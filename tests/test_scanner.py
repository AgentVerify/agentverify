from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator

from agentverify.analysis import component_context
from agentverify.cli import main
from agentverify.policy import evaluate_policy, normalize_policy
from agentverify.report import render_bom, render_json, render_sarif, render_text
from agentverify.scanner import build_python_module_index, scan_repository

ROOT = Path(__file__).resolve().parents[1]


def test_python_module_index_includes_every_nested_source_root(tmp_path: Path) -> None:
    helper = tmp_path / "src/distribution/src/package/security/ssrf_http.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("VALUE = 1\n", encoding="utf-8")

    assert build_python_module_index(tmp_path, [helper])["package.security.ssrf_http"] == (
        "src/distribution/src/package/security/ssrf_http.py"
    )


def test_python_agent_inventory_and_dynamic_shell_finding() -> None:
    ir = scan_repository(ROOT / "cases/python_dangerous")

    assert {(item.kind, item.name) for item in ir.components} >= {
        ("framework", "OpenAI Agents SDK"),
        ("provider", "OpenAI"),
        ("agent", "operator"),
        ("model", "gpt-5"),
        ("tool", "run_task"),
        ("capability", "shell-execution"),
    }
    assert [finding.rule_id for finding in ir.findings] == ["AV-EXEC001"]
    assert ir.findings[0].confidence == "high"
    assert ir.findings[0].ir_path == (
        "agent:operator",
        "tool:run_task",
        "capability:shell-execution",
    )
    assert ir.findings[0].analysis["approval_coverage"] == "unresolved"
    assert {
        (item.source_kind, item.source_name, item.relation, item.target_kind, item.target_name)
        for item in ir.relationships
    } >= {
        ("agent", "operator", "uses", "tool", "run_task"),
        ("tool", "run_task", "uses", "capability", "shell-execution"),
    }


def test_fixed_argv_is_inventory_not_finding() -> None:
    ir = scan_repository(ROOT / "examples/safe_agent")

    assert any(item.name == "shell-execution" for item in ir.components)
    assert not ir.findings


def test_approval_control_governs_privileged_tool() -> None:
    ir = scan_repository(ROOT / "cases/python_approved")

    relationships = {
        (item.source_kind, item.source_name, item.relation, item.target_kind, item.target_name)
        for item in ir.relationships
    }
    assert ("agent", "deployer", "uses", "tool", "deploy") in relationships
    assert ("tool", "deploy", "uses", "capability", "shell-execution") in relationships
    assert ("tool", "deploy", "governed-by", "control", "human-approval") in relationships
    assert ir.findings[0].analysis["approval_coverage"] == "present"
    assert ir.findings[0].analysis["governing_controls"] == ["human-approval"]


def test_typescript_literal_approval_governs_only_its_tool() -> None:
    ir = scan_repository(ROOT / "cases/typescript_approved")

    shell_findings = [finding for finding in ir.findings if finding.rule_id == "AV-EXEC001"]
    coverage = {
        finding.analysis["tool"]: finding.analysis["approval_coverage"]
        for finding in shell_findings
    }
    assert coverage == {
        "approvedCommand": "present",
        "conditionalCommand": "unresolved",
        "disabledApproval": "unresolved",
    }
    assert all(finding.ir_path[0] == "agent:operator" for finding in shell_findings)
    assert {
        (item.source_name, item.relation, item.target_name)
        for item in ir.relationships
        if item.source_kind == "tool" and item.target_kind == "control"
    } == {("approvedCommand", "governed-by", "human-approval")}


def test_python_enabled_auto_approval_is_review_candidate() -> None:
    ir = scan_repository(ROOT / "cases/python_auto_approval")

    assert [finding.rule_id for finding in ir.findings] == ["AV-APPROVAL001"]
    assert ir.findings[0].result_kind == "review"


def test_builtin_tool_constructor_approval_is_instance_scoped() -> None:
    ir = scan_repository(ROOT / "cases/builtin_tool_approval")

    tools = {
        component.name: component.attributes["approval_policy"]
        for component in ir.components
        if component.kind == "tool"
    }
    assert tools == {
        "ShellTool@11": "enabled",
        "ApplyPatchTool@12": "disabled-explicit",
        "CustomTool@13": "unresolved",
        "ShellTool@16": "unresolved-handler",
        "ShellTool@17": "disabled-explicit",
    }
    controls = {
        edge.source_name
        for edge in ir.relationships
        if edge.source_kind == "tool"
        and edge.relation == "governed-by"
        and edge.target_name == "human-approval"
    }
    assert controls == {"ShellTool@11"}
    agent_tools = {
        edge.target_name
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.source_name == "operator"
    }
    assert agent_tools == set(tools)
    shell = next(
        component
        for component in ir.components
        if component.kind == "capability"
        and component.name == "shell-execution"
        and component.evidence.line == 11
    )
    path, analysis = component_context(ir, shell)
    assert path == ("agent:operator", "tool:ShellTool@11", "capability:shell-execution")
    assert analysis["approval_coverage"] == "present"

    handled_shell = next(
        component
        for component in ir.components
        if component.kind == "tool" and component.name == "ShellTool@16"
    )
    assert handled_shell.attributes["approval_handler"] == "configured"
    assert [finding.rule_id for finding in ir.findings] == ["AV-APPROVAL002"]
    assert ir.findings[0].evidence.line == 17
    assert ir.findings[0].result_kind == "review"
    assert ir.findings[0].analysis["approval_coverage"] == "unresolved"


def test_builtin_tool_names_require_openai_agents_import(tmp_path: Path) -> None:
    (tmp_path / "unrelated.py").write_text(
        "ShellTool(executor=object(), needs_approval=True)\n", encoding="utf-8"
    )

    ir = scan_repository(tmp_path)

    assert not any(
        component.kind == "tool" and component.name.startswith("ShellTool@")
        for component in ir.components
    )
    assert not any(
        edge.target_kind == "control" and edge.target_name == "human-approval"
        for edge in ir.relationships
    )


def test_python_computer_tool_has_exact_agent_and_capability_identity() -> None:
    ir = scan_repository(ROOT / "cases/python_computer_tool")
    tools = [
        component
        for component in ir.components
        if component.kind == "tool" and component.name.startswith("ComputerTool@")
    ]
    assert {tool.evidence.line for tool in tools} == {5, 10, 14}
    assert {tool.symbol_id for tool in tools} == {
        "py:agent.py#tool:tool@5",
        "py:agent.py#tool:tool@10",
        "py:agent.py#tool:ComputerTool@14",
    }
    tool_by_line = {tool.evidence.line: tool for tool in tools}
    assert tool_by_line[5].attributes["approval_policy"] == "not-applicable"
    assert tool_by_line[5].attributes["approval_source"] == "sdk-computer-safety-check"
    assert tool_by_line[5].attributes["safety_check_handler"] == "none"
    assert tool_by_line[5].attributes["execution_environment"] == "local"
    assert tool_by_line[10].attributes["safety_check_handler"] == "configured"

    agent_edges = {
        edge.source_name: edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_kind == "tool"
    }
    assert agent_edges["first"].target_id == "py:agent.py#tool:tool@5"
    assert agent_edges["first"].attributes == {
        "target_identity": "lexical-single-definition"
    }
    assert agent_edges["second"].target_id == "py:agent.py#tool:tool@10"
    assert agent_edges["second"].attributes == {
        "target_identity": "lexical-single-definition"
    }
    assert agent_edges["inline"].target_id == "py:agent.py#tool:ComputerTool@14"
    assert agent_edges["inline"].attributes == {}

    capability_edges = [
        edge
        for edge in ir.relationships
        if edge.source_kind == "tool"
        and edge.relation == "uses"
        and edge.target_name == "computer-control"
    ]
    assert {edge.source_id for edge in capability_edges} == {
        tool.symbol_id for tool in tools
    }
    capabilities = [
        component
        for component in ir.components
        if component.kind == "capability" and component.name == "computer-control"
    ]
    assert len(capabilities) == 3
    assert all(
        component.attributes["execution_environment"] == "local"
        for component in capabilities
    )
    assert not any(edge.evidence.path == "unrelated.py" for edge in capability_edges)


def test_assigned_builtin_tool_uses_binding_identity_for_agent_context(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """from agents import Agent, ShellTool

shell = ShellTool(executor=object(), needs_approval=False)
operator = Agent(name="operator", tools=[shell])
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    tool = next(component for component in ir.components if component.kind == "tool")
    edge = next(
        relationship
        for relationship in ir.relationships
        if relationship.source_kind == "agent" and relationship.target_kind == "tool"
    )
    finding = next(finding for finding in ir.findings if finding.rule_id == "AV-APPROVAL002")
    assert tool.symbol_id == edge.target_id == "py:agent.py#tool:shell"
    assert edge.source_id == "py:agent.py#agent:operator"
    assert finding.ir_path[:2] == ("agent:operator", "tool:ShellTool@3")
    assert finding.analysis["direct_agents"] == ["operator"]


def test_repeated_python_bindings_get_occurrence_qualified_symbol_ids(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """from agents import Agent, ShellTool

def first():
    shell = ShellTool(executor=object())
    agent = Agent(name="shared", tools=[shell])
    return agent

def second():
    shell = ShellTool(executor=object())
    agent = Agent(name="shared", tools=[shell])
    return agent
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)
    agents = [component for component in ir.components if component.kind == "agent"]
    edges = [
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_kind == "tool"
    ]
    assert {component.symbol_id for component in agents} == {
        "py:agent.py#agent:agent@5",
        "py:agent.py#agent:agent@10",
    }
    assert {edge.source_id for edge in edges} == {component.symbol_id for component in agents}
    assert {edge.target_id for edge in edges} == {
        "py:agent.py#tool:shell@4",
        "py:agent.py#tool:shell@9",
    }
    assert all(edge.attributes["target_identity"] == "lexical-single-definition" for edge in edges)

    bom = json.loads(render_bom(ir))
    source_endpoints = [
        relationship["source"]
        for relationship in bom["relationships"]
        if relationship["source"]["kind"] == "agent"
    ]
    assert source_endpoints
    assert all(endpoint["resolution"] == "symbol-id" for endpoint in source_endpoints)
    assert len({endpoint["asset_id"] for endpoint in source_endpoints}) == 2
    target_endpoints = [
        relationship["target"]
        for relationship in bom["relationships"]
        if relationship["source"]["kind"] == "agent"
    ]
    assert all(endpoint["resolution"] == "symbol-id" for endpoint in target_endpoints)


def test_python_scoped_resolution_rejects_reassignment_and_forward_reference(
    tmp_path: Path,
) -> None:
    (tmp_path / "agent.py").write_text(
        """from agents import Agent, ShellTool

def reassigned():
    shell = ShellTool(executor=object())
    shell = ShellTool(executor=object())
    return Agent(name="reassigned", tools=[shell])

def forward():
    agent = Agent(name="forward", tools=[later])
    later = ShellTool(executor=object())
    return agent

def module_forward():
    return Agent(name="module-forward", tools=[global_later])

global_later = ShellTool(executor=object())
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)
    edges = [edge for edge in ir.relationships if edge.source_kind == "agent"]
    assert {edge.source_name for edge in edges} == {
        "forward",
        "module-forward",
        "reassigned",
    }
    assert all(edge.target_id is None for edge in edges)
    reassigned = next(edge for edge in edges if edge.source_name == "reassigned")
    assert reassigned.attributes["target_identity"] == "ambiguous-repeated-binding"
    forward = next(edge for edge in edges if edge.source_name == "forward")
    assert "target_identity" not in forward.attributes


def test_repeated_python_tool_definitions_get_occurrence_qualified_ids(tmp_path: Path) -> None:
    (tmp_path / "tools.py").write_text(
        """from agents import function_tool

def first():
    @function_tool(needs_approval=True)
    def approval_tool():
        return "first"
    return approval_tool

def second():
    @function_tool(needs_approval=True)
    def approval_tool():
        return "second"
    return approval_tool
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)
    tools = [component for component in ir.components if component.kind == "tool"]
    approval_edges = [edge for edge in ir.relationships if edge.relation == "governed-by"]
    assert {component.symbol_id for component in tools} == {
        "py:tools.py#tool:approval_tool@5",
        "py:tools.py#tool:approval_tool@11",
    }
    assert {edge.source_id for edge in approval_edges} == {
        component.symbol_id for component in tools
    }
    bom = json.loads(render_bom(ir))
    assert all(
        relationship["source"]["resolution"] == "symbol-id" for relationship in bom["relationships"]
    )


def test_default_disabled_local_shell_is_reviewed_but_hosted_shell_is_not(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """from agents import Agent, ShellTool

local = Agent(name="local", tools=[ShellTool(executor=object())])
hosted = Agent(
    name="hosted",
    tools=[ShellTool(environment={"type": "container_auto"})],
)
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    approval_reviews = [finding for finding in ir.findings if finding.rule_id == "AV-APPROVAL002"]
    assert len(approval_reviews) == 1
    assert approval_reviews[0].evidence.line == 3
    assert approval_reviews[0].result_kind == "review"
    assert "disabled by default" in approval_reviews[0].message
    environments = {
        component.evidence.line: component.attributes["execution_environment"]
        for component in ir.components
        if component.kind == "tool"
    }
    assert environments == {3: "local", 6: "hosted"}


def test_non_approval_skip_and_status_flags_are_not_bypasses(tmp_path: Path) -> None:
    (tmp_path / "flags.py").write_text(
        """_sampling_auto_approved_warning_logged = True
dangerously_skip_version_check = True
auto_approve = True
""",
        encoding="utf-8",
    )
    (tmp_path / "flags.ts").write_text(
        """const warning = { autoApprovedWarningLogged: true };
const client = { dangerouslySkipVersionCheck: true };
const policy = { autoApprove: true };
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    approval_findings = [finding for finding in ir.findings if finding.rule_id == "AV-APPROVAL001"]
    assert [(finding.evidence.path, finding.evidence.line) for finding in approval_findings] == [
        ("flags.py", 3),
        ("flags.ts", 3),
    ]


def test_environment_auto_approval_requires_a_direct_true_return() -> None:
    ir = scan_repository(ROOT / "cases/approval_env_guard")

    approval_findings = [finding for finding in ir.findings if finding.rule_id == "AV-APPROVAL001"]
    assert [(finding.evidence.path, finding.evidence.line) for finding in approval_findings] == [
        ("approval.py", 8),
        ("approval.py", 42),
        ("approval.ts", 4),
        ("approval.ts", 12),
    ]
    controls = {
        (component.evidence.path, component.evidence.line): component.attributes
        for component in ir.components
        if component.kind == "control-setting" and component.name == "auto-approval"
    }
    assert controls[("approval.py", 8)]["environment_names"] == ["SHELL_AUTO_APPROVE"]
    assert controls[("approval.py", 42)] == {
        "enabled": True,
        "source": "environment-approval-short-circuit",
        "environment_names": ["PATCH_AUTO_APPROVE"],
        "scope": "production",
    }
    assert controls[("approval.ts", 4)]["environment_names"] == ["AUTO_APPROVE_HITL"]
    assert controls[("approval.ts", 12)]["environment_names"] == ["SHELL_AUTO_APPROVE"]
    assert all(
        attributes["source"] == "environment-guard"
        for location, attributes in controls.items()
        if location != ("approval.py", 42)
    )


def test_environment_approval_attribute_is_independent_of_method_order(tmp_path: Path) -> None:
    (tmp_path / "gate.py").write_text(
        """import os

class Gate:
    def require_confirmation(self) -> None:
        if self.auto_approve:
            return
        self.prompt()

    def __init__(self) -> None:
        self.auto_approve = os.environ["AUTO_APPROVE_ACTIONS"] == "1"
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line) for finding in ir.findings
    ] == [("AV-APPROVAL001", "gate.py", 5)]


def test_anthropic_and_azure_model_providers() -> None:
    ir = scan_repository(ROOT / "cases/model_providers")

    assert {(item.kind, item.name) for item in ir.components} >= {
        ("provider", "Anthropic"),
        ("provider", "Azure OpenAI"),
        ("model", "gpt-4o-enterprise"),
    }
    assert ("provider", "OpenAI") not in {(item.kind, item.name) for item in ir.components}
    azure_model = next(item for item in ir.components if item.kind == "model")
    assert azure_model.attributes["provider"] == "Azure OpenAI"


def test_dynamic_mcp_forwarding_but_not_fixed_tool_call() -> None:
    ir = scan_repository(ROOT / "cases/mcp_forwarder")

    forwarding = [
        item
        for item in ir.components
        if item.kind == "capability" and item.name == "mcp-tool-forwarding"
    ]
    assert len(forwarding) == 12
    assert [finding.rule_id for finding in ir.findings] == [
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
    ]
    assert ir.findings[0].result_kind == "review"
    guarded = next(item for item in forwarding if item.attributes["allowlist_guard"])
    assert guarded.evidence.line == 18
    assert any(
        item.source_kind == "capability"
        and item.relation == "governed-by"
        and item.target_name == "tool-allowlist"
        for item in ir.relationships
    )
    late = next(item for item in forwarding if item.evidence.line == 22)
    assert late.attributes["allowlist_guard"] is False
    registry_guarded = next(item for item in forwarding if item.evidence.line == 36)
    assert registry_guarded.attributes == {
        "api": "session.call_tool",
        "dynamic_tool_name": True,
        "dynamic_arguments": True,
        "allowlist_guard": False,
        "registry_guard": True,
        "fixed_tool_binding": False,
        "scope": "production",
        "guard_control": "tool-registry",
        "guard_path": "proxy.py",
        "guard_line": 35,
    }
    registry_edge = next(
        item
        for item in ir.relationships
        if item.evidence.line == 36 and item.target_name == "tool-registry"
    )
    assert registry_edge.attributes == {
        "control_path": "proxy.py",
        "control_line": 35,
        "policy_effect": "routing-only",
    }
    registry_finding = next(item for item in ir.findings if item.evidence.line == 36)
    assert registry_finding.analysis["governing_controls"] == ["tool-registry"]
    assert registry_finding.analysis["governing_control_effects"] == {
        "tool-registry": ["routing-only"]
    }
    assert (
        next(item for item in forwarding if item.evidence.line == 41).attributes["allowlist_guard"]
        is False
    )
    assert (
        next(item for item in forwarding if item.evidence.line == 49).attributes["allowlist_guard"]
        is False
    )
    bound = next(item for item in forwarding if item.evidence.line == 64)
    assert bound.attributes["fixed_tool_binding"] is True
    assert bound.attributes["binding_line"] == 57
    binding_edge = next(
        item
        for item in ir.relationships
        if item.evidence.line == 64 and item.target_name == "fixed-tool-binding"
    )
    assert binding_edge.attributes == {
        "control_path": "proxy.py",
        "control_line": 57,
        "binding_scope": "instance",
        "policy_effect": "binds-tool-source-per-instance",
    }
    bound_finding = next(item for item in ir.findings if item.evidence.line == 64)
    assert bound_finding.analysis["governing_controls"] == ["fixed-tool-binding"]
    assert bound_finding.analysis["governing_control_effects"] == {
        "fixed-tool-binding": ["binds-tool-source-per-instance"]
    }
    mutable = next(item for item in forwarding if item.evidence.line == 76)
    assert mutable.attributes["fixed_tool_binding"] is False
    assert not any(
        item.evidence.line == 76 and item.target_name == "fixed-tool-binding"
        for item in ir.relationships
    )
    closure = next(item for item in forwarding if item.evidence.line == 81)
    assert closure.attributes["fixed_tool_binding"] is True
    assert closure.attributes["binding_scope"] == "closure"
    closure_edge = next(
        item
        for item in ir.relationships
        if item.evidence.line == 81 and item.target_name == "fixed-tool-binding"
    )
    assert closure_edge.attributes == {
        "control_path": "proxy.py",
        "control_line": 79,
        "binding_scope": "closure",
        "policy_effect": "binds-tool-source-per-closure",
    }
    rebound = next(item for item in forwarding if item.evidence.line == 90)
    assert rebound.attributes["fixed_tool_binding"] is False
    assert not any(
        item.evidence.line == 90 and item.target_name == "fixed-tool-binding"
        for item in ir.relationships
    )
    routed = next(item for item in forwarding if item.evidence.line == 97)
    assert routed.attributes["registry_guard"] is True
    assert routed.attributes["guard_summary"] == "same-class-method"
    routed_edge = next(
        item
        for item in ir.relationships
        if item.evidence.line == 97 and item.target_name == "tool-registry"
    )
    assert routed_edge.attributes == {
        "control_path": "proxy.py",
        "control_line": 101,
        "policy_effect": "routing-only",
        "summary": "same-class-method",
    }
    routed_finding = next(item for item in ir.findings if item.evidence.line == 97)
    assert routed_finding.analysis["governing_control_effects"] == {
        "tool-registry": ["routing-only"]
    }
    fallback = next(item for item in forwarding if item.evidence.line == 108)
    assert fallback.attributes["registry_guard"] is False
    assert not any(
        item.evidence.line == 108 and item.target_name == "tool-registry"
        for item in ir.relationships
    )


def test_mcp_registry_method_summary_requires_literal_path_selection(tmp_path: Path) -> None:
    source = """from mcp.server import Server

class MiddlewareServer:
    async def select_dynamic(self, name: str, arguments: dict, selected: bool):
        return await self.call_tool(name, arguments, run_middleware=selected)

    async def select_core(self, name: str, arguments: dict):
        return await self.call_tool(name, arguments, run_middleware=False)

    async def call_tool(
        self,
        name: str,
        arguments: dict,
        *,
        run_middleware: bool = True,
    ):
        if run_middleware:
            return await self.call_tool(name, arguments, run_middleware=False)
        tool = await self.get_tool(name)
        if tool is None:
            raise ValueError(name)
        return await tool.run(arguments)

class ReturnFallbackServer:
    async def dispatch(self, name: str, arguments: dict):
        return await self.call_tool(name, arguments)

    async def call_tool(self, name: str, arguments: dict):
        tool = await self.get_tool(name)
        if tool is None:
            return await self.default_tool.run(arguments)
        return await tool.run(arguments)

class ConditionalGuardServer:
    async def dispatch(self, name: str, arguments: dict):
        return await self.call_tool(name, arguments)

    async def call_tool(self, name: str, arguments: dict, enforce: bool = True):
        tool = await self.get_tool(name)
        if enforce:
            if tool is None:
                raise ValueError(name)
        return await tool.run(arguments)

class ReassignedFallbackServer:
    async def dispatch(self, name: str, arguments: dict):
        return await self.call_tool(name, arguments)

    async def call_tool(self, name: str, arguments: dict):
        tool = await self.get_tool(name)
        if tool is None:
            tool = self.default_tool
        if tool is None:
            raise ValueError(name)
        return await tool.run(arguments)
"""
    (tmp_path / "server.py").write_text(source, encoding="utf-8")

    ir = scan_repository(tmp_path)
    registry_edges = [
        item
        for item in ir.relationships
        if item.target_name == "tool-registry" and item.evidence.path == "server.py"
    ]

    def line_of(fragment: str) -> int:
        return source[: source.index(fragment)].count("\n") + 1

    dynamic_line = line_of("self.call_tool(name, arguments, run_middleware=selected)")
    core_line = line_of("self.call_tool(name, arguments, run_middleware=False)")
    fallback_line = line_of(
        "return await self.call_tool(name, arguments)\n\n    async def call_tool"
    )
    conditional_line = line_of(
        "return await self.call_tool(name, arguments)\n\n    async def call_tool(self, name: str, arguments: dict, enforce"
    )
    reassigned_line = line_of(
        "return await self.call_tool(name, arguments)\n\n    async def call_tool(self, name: str, arguments: dict):\n        tool = await self.get_tool(name)\n        if tool is None:\n            tool = self.default_tool"
    )
    assert not any(item.evidence.line == dynamic_line for item in registry_edges)
    assert not any(item.evidence.line == fallback_line for item in registry_edges)
    assert not any(item.evidence.line == conditional_line for item in registry_edges)
    assert not any(item.evidence.line == reassigned_line for item in registry_edges)
    core_edge = next(item for item in registry_edges if item.evidence.line == core_line)
    assert core_edge.attributes["required_arguments"] == {"run_middleware": False}
    assert core_edge.attributes["summary"] == "same-class-method"


def test_imported_mcp_registry_manager_requires_immutable_constructor_binding() -> None:
    fixture = ROOT / "cases/mcp_imported_manager"
    ir = scan_repository(fixture)

    forwarding = {
        item.evidence.line: item
        for item in ir.components
        if item.kind == "capability"
        and item.name == "mcp-tool-forwarding"
        and item.evidence.path == "app/server.py"
    }
    assert set(forwarding) == {11, 22, 30}
    routed = forwarding[11]
    assert routed.attributes["registry_guard"] is True
    assert routed.attributes["guard_summary"] == "imported-class-method"
    assert routed.attributes["guard_class"] == "RegistryManager"
    assert routed.attributes["guard_path"] == "app/managers/registry.py"
    assert routed.attributes["guard_line"] == 4
    routed_edge = next(
        item
        for item in ir.relationships
        if item.evidence.path == "app/server.py"
        and item.evidence.line == 11
        and item.target_name == "tool-registry"
    )
    assert routed_edge.attributes == {
        "control_path": "app/managers/registry.py",
        "control_line": 4,
        "policy_effect": "routing-only",
        "summary": "imported-class-method",
        "summary_class": "RegistryManager",
        "summary_path": "app/managers/registry.py",
    }
    assert forwarding[22].attributes["registry_guard"] is False
    assert forwarding[30].attributes["registry_guard"] is False
    assert not any(
        item.target_name == "tool-registry"
        and item.evidence.path == "app/server.py"
        and item.evidence.line in {22, 30}
        for item in ir.relationships
    )
    rebound = next(
        item
        for item in ir.components
        if item.name == "mcp-tool-forwarding"
        and item.evidence.path == "app/rebound_server.py"
        and item.evidence.line == 13
    )
    assert rebound.attributes["registry_guard"] is False
    assert not any(
        item.target_name == "tool-registry"
        and item.evidence.path == "app/rebound_server.py"
        and item.evidence.line == 13
        for item in ir.relationships
    )

    partial = scan_repository(fixture, selected_paths=["app/server.py"])
    assert not any(item.target_name == "tool-registry" for item in partial.relationships)


def test_browser_and_external_action_capabilities_are_linked() -> None:
    ir = scan_repository(ROOT / "cases/external_actions")

    capabilities = {item.name for item in ir.components if item.kind == "capability"}
    assert capabilities >= {"browser", "network", "external-action"}
    tool_capabilities = {
        item.target_name
        for item in ir.relationships
        if item.source_kind == "tool" and item.source_name == "publish"
    }
    assert tool_capabilities >= {"browser", "network", "external-action"}
    assert not ir.findings


def test_parameter_controlled_http_origin_is_reported_but_fixed_host_is_not() -> None:
    ir = scan_repository(ROOT / "cases/network_dynamic_origin")

    network = {
        item.evidence.line: item.attributes
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.evidence.path == "agent.py"
    }
    assert network[7]["dynamic_origin"] is True
    assert network[12]["dynamic_origin"] is False
    assert network[17]["dynamic_origin"] is False
    assert network[31] == {
        "scope": "production",
        "api": "urlrequest.urlopen",
        "canonical_api": "urllib.request.urlopen",
        "dynamic_origin": True,
    }
    assert network[37] == {
        "scope": "production",
        "api": "open_url",
        "canonical_api": "urllib.request.urlopen",
        "dynamic_origin": True,
    }
    assert network[43] == {
        "scope": "production",
        "api": "request_alias.urlopen",
        "canonical_api": "urllib.request.urlopen",
        "dynamic_origin": False,
    }
    assert sorted(network) == [7, 12, 17, 31, 37, 43]
    assert [
        (finding.rule_id, finding.evidence.line)
        for finding in ir.findings
        if finding.evidence.path == "agent.py"
    ] == [
        ("AV-NET001", 7),
        ("AV-NET001", 31),
        ("AV-NET001", 37),
    ]
    finding = ir.findings[0]
    assert finding.result_kind == "review"
    assert finding.ir_path == (
        "agent:networker",
        "tool:fetch_url",
        "capability:network",
    )
    assert {
        (edge.source_name, edge.evidence.line)
        for edge in ir.relationships
        if edge.target_kind == "capability" and edge.target_name == "network"
    } == {
        ("fetch_url", 7),
        ("search", 12),
        ("status", 17),
        ("urllib_direct", 31),
        ("urllib_request", 37),
        ("urllib_fixed_request", 43),
        ("guarded_fetch", 13),
        ("guarded_alias_fetch", 22),
        ("late_guard", 27),
        ("scheme_only", 39),
        ("continuing_guard", 47),
        ("rebound_parser", 56),
        ("shadowed_parser", 65),
        ("mutable_host_policy", 76),
        ("rejection_branch_request", 83),
    }


def test_python_network_origin_guards_require_fail_closed_scheme_and_host_checks() -> None:
    ir = scan_repository(ROOT / "cases/network_dynamic_origin")

    guarded = {
        item.evidence.line: item.attributes
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.evidence.path == "guards.py"
        and item.attributes.get("network_origin_guard")
    }
    assert sorted(guarded) == [13, 22]
    assert guarded[13]["initial_origin_scope"] == "allowlisted"
    assert guarded[22]["initial_origin_scope"] == "allowlisted"
    controls = [
        item
        for item in ir.components
        if item.kind == "control" and item.name == "network-origin-allowlist"
    ]
    assert [(item.evidence.path, item.evidence.line) for item in controls] == [
        ("guards.py", 11),
        ("guards.py", 20),
    ]
    assert controls[0].attributes == {
        "scope": "production",
        "policy_effect": "restricts-initial-http-origin",
        "frontend": "python",
        "parser": "urlsplit",
        "url": "url",
        "schemes": ["https"],
        "hosts": ["api.example.com", "cdn.example.com"],
        "initial_origin_scope": "allowlisted",
        "redirect_scope": "disabled",
        "dns_scope": "unresolved",
    }
    assert controls[1].attributes["redirect_scope"] == "unresolved"
    governed_lines = {
        edge.evidence.line
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.source_name == "network"
        and edge.relation == "governed-by"
        and edge.target_kind == "control"
        and edge.target_name == "network-origin-allowlist"
    }
    assert governed_lines == {13, 22}
    guarded_finding = next(
        finding
        for finding in ir.findings
        if finding.rule_id == "AV-NET001"
        and finding.evidence.path == "guards.py"
        and finding.evidence.line == 13
    )
    assert guarded_finding.result_kind == "review"
    assert guarded_finding.analysis["governing_controls"] == [
        "network-origin-allowlist"
    ]


def test_dynamic_http_origin_tracks_aliases_and_keyword_url(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """import requests
from agents import function_tool

@function_tool
def fetch(target: str) -> str:
    alias = target
    return requests.request(method="GET", url=alias).text

class ConfiguredClient:
    @function_tool
    def fetch_configured(self) -> str:
        return requests.get(self.endpoint).text
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    findings = [finding for finding in ir.findings if finding.rule_id == "AV-NET001"]
    assert len(findings) == 1
    finding = findings[0]
    assert finding.evidence.line == 7
    assert finding.analysis["tool"] == "fetch"


def test_typescript_dynamic_eval_is_linked_and_reported() -> None:
    ir = scan_repository(ROOT / "cases/typescript_eval")

    assert [finding.rule_id for finding in ir.findings] == ["AV-EXEC002"]
    assert ir.findings[0].ir_path == (
        "agent:evaluator",
        "tool:evaluate",
        "capability:code-execution",
    )


def test_typescript_tool_arrays_are_structure_aware_and_identity_linked() -> None:
    ir = scan_repository(ROOT / "cases/typescript_structured_tools")

    tools = {component.name: component for component in ir.components if component.kind == "tool"}
    assert set(tools) == {
        "applyPatchTool@33",
        "assignedShell",
        "namespaceTools",
        "safeTool",
    }
    assert tools["assignedShell"].attributes["approval_policy"] == "disabled-explicit"
    assert tools["assignedShell"].attributes["execution_environment"] == "local"
    assert tools["applyPatchTool@33"].attributes["approval_policy"] == "enabled"

    operator_edges = [
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.source_name == "operator"
    ]
    assert {(edge.relation, edge.target_kind, edge.target_name) for edge in operator_edges} == {
        ("delegates-to", "agent", "worker"),
        ("uses", "tool", "applyPatchTool@33"),
        ("uses", "tool", "assignedShell"),
        ("uses", "tool", "namespaceTools"),
        ("uses", "tool", "safeTool"),
        ("uses", "tool", "unknownFactory"),
        ("uses", "tool", "unrelatedShellTool"),
    }
    assert not {
        "async",
        "description",
        "do",
        "return",
        "toolName",
        "words",
    } & {edge.target_name for edge in operator_edges}
    assert next(edge for edge in operator_edges if edge.target_name == "worker").target_id == (
        "ts:agent.ts#agent:worker"
    )
    assert (
        next(edge for edge in operator_edges if edge.target_name == "unrelatedShellTool").target_id
        is None
    )
    assert [finding.rule_id for finding in ir.findings] == ["AV-APPROVAL002"]
    assert ir.findings[0].ir_path[:2] == ("agent:operator", "tool:assignedShell")


def test_repeated_typescript_agent_bindings_get_occurrence_qualified_ids(tmp_path: Path) -> None:
    (tmp_path / "agent.ts").write_text(
        """import { Agent, tool } from "@openai/agents";
function first() {
  const repeatedTool = tool({ name: "first" });
  const agent = new Agent({ name: "shared", tools: [repeatedTool] });
  return agent;
}
function second() {
  const repeatedTool = tool({ name: "second" });
  const agent = new Agent({ name: "shared", tools: [repeatedTool] });
  return agent;
}
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)
    agents = [component for component in ir.components if component.kind == "agent"]
    edges = [edge for edge in ir.relationships if edge.source_kind == "agent"]
    assert {component.symbol_id for component in agents} == {
        "ts:agent.ts#agent:agent@4",
        "ts:agent.ts#agent:agent@9",
    }
    assert {edge.source_id for edge in edges} == {component.symbol_id for component in agents}
    assert all(edge.target_id is None for edge in edges)
    assert all(edge.attributes["target_identity"] == "ambiguous-repeated-binding" for edge in edges)
    bom = json.loads(render_bom(ir))
    assert all(
        relationship["source"]["resolution"] == "symbol-id" for relationship in bom["relationships"]
    )


def test_typescript_builtin_options_variable_stays_unresolved(tmp_path: Path) -> None:
    (tmp_path / "agent.ts").write_text(
        """import { Agent, shellTool } from "@openai/agents";
const options = loadPolicyAtRuntime();
const agent = new Agent({ name: "operator", tools: [shellTool(options)] });
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    tool = next(component for component in ir.components if component.kind == "tool")
    assert tool.attributes["approval_policy"] == "unresolved"
    assert tool.attributes["execution_environment"] == "unresolved"
    assert not ir.findings


def test_cline_inline_tool_links_only_dynamic_bun_shell_execution() -> None:
    ir = scan_repository(ROOT / "cases/typescript_bun_shell")

    shell = [
        component
        for component in ir.components
        if component.kind == "capability" and component.name == "shell-execution"
    ]
    assert [
        (component.evidence.line, component.attributes["dynamic_command"]) for component in shell
    ] == [
        (8, True),
        (12, False),
    ]
    assert [finding.rule_id for finding in ir.findings] == ["AV-EXEC001"]
    assert ir.findings[0].evidence.line == 8
    assert ir.findings[0].ir_path == (
        "agent:operator",
        "tool:createTool@6",
        "capability:shell-execution",
    )


def test_typescript_mastra_properties_and_mcp_registrations_have_exact_tool_spans() -> None:
    ir = scan_repository(ROOT / "cases/typescript_tool_registrations")

    tools = {
        item.name: item
        for item in ir.components
        if item.kind == "tool" and item.evidence.path == "tools.ts"
    }
    assert set(tools) == {"lookup", "requester", "download", "status"}
    assert tools["lookup"].symbol_id == "ts:tools.ts#tool:lookup"
    assert tools["requester"].attributes == {
        "constructor": "createTool",
        "needs_approval": False,
        "binding": "object-property",
    }
    assert tools["download"].attributes == {
        "constructor": "registerTool",
        "needs_approval": False,
        "protocol": "MCP",
        "registry": "server",
    }
    assert tools["download"].symbol_id == "ts:tools.ts#tool:download"

    network_edges = [
        (edge.source_name, edge.evidence.line, edge.source_id)
        for edge in ir.relationships
        if edge.source_kind == "tool"
        and edge.target_kind == "capability"
        and edge.target_name == "network"
    ]
    assert network_edges == [
        ("lookup", 7, "ts:tools.ts#tool:lookup"),
        ("requester", 14, "ts:tools.ts#tool:requester"),
        ("download", 22, "ts:tools.ts#tool:download"),
        ("status", 26, "ts:tools.ts#tool:status"),
    ]
    dynamic_origins = {
        item.evidence.line: item.attributes["dynamic_origin"]
        for item in ir.components
        if item.kind == "capability" and item.name == "network" and item.evidence.path == "tools.ts"
    }
    assert dynamic_origins == {7: False, 14: True, 22: True, 26: False}
    assert [
        (finding.rule_id, finding.evidence.line, finding.analysis["tool"])
        for finding in ir.findings
    ] == [
        ("AV-NET001", 14, "requester"),
        ("AV-NET001", 22, "download"),
    ]
    assert not any(
        item.kind == "tool" and item.evidence.path == "fake.ts" for item in ir.components
    )
    assert not any(
        item.kind == "capability" and item.name == "network" and item.evidence.path == "fake.ts"
        for item in ir.components
    )


def test_typescript_network_origin_tracks_aliases_but_resolves_fixed_module_host(
    tmp_path: Path,
) -> None:
    (tmp_path / "tools.ts").write_text(
        """import { tool } from "ai";
const API = "https://search.example";

const requester = tool({
  execute: async ({ url }) => {
    const target = url;
    return fetch(target);
  },
});

const search = tool({
  execute: async ({ query }) => {
    const target = `${API}/search?q=${query}`;
    return fetch(target);
  },
});
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    network = {
        item.evidence.line: item.attributes["dynamic_origin"]
        for item in ir.components
        if item.kind == "capability" and item.name == "network"
    }
    assert network == {7: True, 14: False}
    assert [
        (finding.rule_id, finding.evidence.line, finding.analysis["tool"])
        for finding in ir.findings
    ] == [("AV-NET001", 7, "requester")]


def test_typescript_same_file_network_helpers_propagate_only_controlled_origins() -> None:
    ir = scan_repository(ROOT / "cases/typescript_helper_summary")

    summarized = {
        item.evidence.line: item.attributes
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "same-file-helper"
    }
    assert {
        item.evidence.line
        for item in ir.components
        if item.kind == "capability" and item.name == "network"
    } == {8, 13, 18, 24}
    assert summarized == {
        18: {
            "scope": "production",
            "api": "fetchRemote",
            "dynamic_origin": True,
            "summary": "same-file-helper",
            "helper_line": 7,
            "helper_network_calls": 1,
        },
        24: {
            "scope": "production",
            "api": "searchRemote",
            "dynamic_origin": False,
            "summary": "same-file-helper",
            "helper_line": 11,
            "helper_network_calls": 1,
        },
    }
    assert [
        (edge.source_name, edge.evidence.line, edge.source_id)
        for edge in ir.relationships
        if edge.target_kind == "capability" and edge.target_name == "network"
    ] == [
        ("proxy", 18, "ts:tools.ts#tool:proxy"),
        ("search", 24, "ts:tools.ts#tool:search"),
    ]
    assert [(finding.rule_id, finding.evidence.line) for finding in ir.findings] == [
        ("AV-NET001", 18)
    ]


def test_typescript_network_origin_policy_preserves_optional_open_hostname_scope() -> None:
    ir = scan_repository(ROOT / "cases/typescript_network_origin_policy")

    network = {
        item.evidence.line: item.attributes
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "same-file-helper"
    }
    assert sorted(network) == [35, 41, 51, 57, 72, 82]
    assert network[35]["network_origin_policy"] is True
    assert network[35]["scheme_scope"] == "allowlisted"
    assert network[35]["hostname_scope"] == "configured-optional"
    assert all(
        "network_origin_policy" not in network[line]
        for line in (41, 51, 57, 72, 82)
    )
    controls = [
        item
        for item in ir.components
        if item.kind == "control" and item.name == "network-origin-policy"
    ]
    assert len(controls) == 1
    assert controls[0].evidence.path == "policy.ts"
    assert controls[0].evidence.line == 8
    assert controls[0].attributes == {
        "scope": "production",
        "policy_effect": "validates-initial-http-origin",
        "frontend": "typescript",
        "helper": "validateTarget",
        "schemes": ["http", "https"],
        "scheme_scope": "allowlisted",
        "hostname_scope": "configured-optional",
        "hostname_default": "open",
        "hostname_match": "exact-or-subdomain",
        "environment_name": "ALLOWED_DOMAINS",
        "redirect_scope": "unresolved",
        "dns_scope": "unresolved",
    }
    edges = [
        edge
        for edge in ir.relationships
        if edge.target_kind == "control" and edge.target_name == "network-origin-policy"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("policy.ts", 35)
    ]
    guarded_finding = next(
        finding
        for finding in ir.findings
        if finding.rule_id == "AV-NET001" and finding.evidence.line == 35
    )
    assert guarded_finding.result_kind == "review"
    assert guarded_finding.analysis["governing_control_effects"] == {
        "network-origin-policy": ["validates-initial-http-origin"]
    }


def test_python_secure_network_helper_requires_complete_transport_proof() -> None:
    ir = scan_repository(ROOT / "cases/python_secure_network_helper")

    network = [
        item
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "secure-imported-function"
    ]
    assert [(item.evidence.path, item.evidence.line) for item in network] == [
        ("app.py", 6),
        ("app.py", 10),
    ]
    assert all(
        item.attributes
        == {
            "scope": "production",
            "api": "safe_get",
            "dynamic_origin": True,
            "summary": "secure-imported-function",
            "helper_path": "secure_transport/safe_requests.py",
            "helper_line": 30,
            "helper_network_lines": [21],
            "network_origin_policy": True,
            "initial_origin_scope": "public-addresses",
            "redirect_scope": "each-hop-validated",
            "dns_scope": "connection-pinned",
            "proxy_scope": "disabled",
            "enforcement_default": "enabled",
        }
        for item in network
    )
    controls = [
        item
        for item in ir.components
        if item.kind == "control" and item.name == "network-ssrf-policy"
    ]
    assert len(controls) == 1
    assert controls[0].evidence.path == "secure_transport/safe_requests.py"
    assert controls[0].evidence.line == 30
    assert controls[0].attributes == {
        "scope": "production",
        "policy_effect": "restricts-http-origin-and-peer",
        "frontend": "python",
        "helper": "safe_get",
        "helper_path": "secure_transport/safe_requests.py",
        "schemes": ["http", "https"],
        "initial_origin_scope": "public-addresses",
        "redirect_scope": "each-hop-validated",
        "dns_scope": "connection-pinned",
        "proxy_scope": "disabled",
        "enforcement_default": "enabled",
        "escape_hatch": "configured-opt-out",
        "bypass_environment": "ALLOW_UNSAFE_NETWORK",
        "force_safe_environment": "FORCE_SAFE_NETWORK",
    }
    edges = [
        edge
        for edge in ir.relationships
        if edge.target_kind == "control" and edge.target_name == "network-ssrf-policy"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("app.py", 6),
        ("app.py", 10),
    ]

    selected_ir = scan_repository(
        ROOT / "cases/python_secure_network_helper",
        selected_paths={"app.py", "secure_transport/safe_requests.py"},
    )
    assert not any(
        edge.target_kind == "control" and edge.target_name == "network-ssrf-policy"
        for edge in selected_ir.relationships
    )


def test_python_proxy_conditional_network_helper_preserves_proxy_residual(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/python_proxy_conditional_network_helper"
    ir = scan_repository(root)

    network = [
        item
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "secure-imported-function"
    ]
    assert [(item.evidence.path, item.evidence.line) for item in network] == [
        ("app.py", 6),
        ("app.py", 10),
    ]
    assert [item.attributes["redirect_scope"] for item in network] == [
        "disabled",
        "each-hop-validated",
    ]
    assert all(
        item.attributes["dns_scope"] == "connection-pinned-unless-proxied"
        and item.attributes["proxy_scope"] == "environment-or-caller-dependent"
        and item.attributes["enforcement_default"] == "enabled"
        and item.attributes["helper_network_lines"] == [65]
        for item in network
    )
    controls = {
        item.attributes["helper"]: item
        for item in ir.components
        if item.kind == "control" and item.name == "network-ssrf-policy"
    }
    assert set(controls) == {"safe_get", "safe_request"}
    assert controls["safe_get"].evidence.line == 69
    assert controls["safe_request"].evidence.line == 73
    assert all(
        item.attributes["policy_effect"]
        == "restricts-http-origin-and-conditionally-pins-peer"
        and item.attributes["escape_hatch"] == "none"
        and "bypass_environment" not in item.attributes
        and "force_safe_environment" not in item.attributes
        for item in controls.values()
    )

    blocking_mutations = [
        (
            "_assert_pinned_peer(sock, address, hostname)",
            "verify_peer(sock, address, hostname)",
        ),
        ("parsed = urlparse(url)", 'parsed = urlparse("https://fixed.example")'),
        (
            "addresses = [result[4][0] for result in socket.getaddrinfo(parsed.hostname, None)]",
            'socket.getaddrinfo(parsed.hostname, None)\n    addresses = ["8.8.8.8"]',
        ),
        (
            '_proxy_applies(url, kwargs.get("proxies"))',
            "_proxy_applies(url, None)",
        ),
    ]
    for index, (before, after) in enumerate(blocking_mutations):
        incomplete = tmp_path / f"incomplete-{index}"
        shutil.copytree(root, incomplete)
        transport = incomplete / "transport/url_safety.py"
        source = transport.read_text(encoding="utf-8")
        assert before in source
        transport.write_text(source.replace(before, after, 1), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.target_kind == "control" and edge.target_name == "network-ssrf-policy"
            for edge in incomplete_ir.relationships
        )

    unbounded = tmp_path / "unbounded"
    shutil.copytree(root, unbounded)
    transport = unbounded / "transport/url_safety.py"
    source = transport.read_text(encoding="utf-8")
    transport.write_text(
        source.replace("range(max_redirects + 1)", "range(5)", 1),
        encoding="utf-8",
    )
    unbounded_ir = scan_repository(unbounded)
    assert [
        edge.evidence.line
        for edge in unbounded_ir.relationships
        if edge.target_kind == "control" and edge.target_name == "network-ssrf-policy"
    ] == [6]


def test_python_configurable_pinned_network_helper_preserves_noop_state(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/python_configurable_network_helper"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.target_kind == "control" and edge.target_name == "network-ssrf-policy"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("app.py", 6),
        ("app.py", 10),
    ]
    assert [edge.attributes["redirect_scope"] for edge in edges] == [
        "disabled-default-each-hop-validated-when-enabled",
        "disabled",
    ]
    assert all(
        edge.attributes["initial_origin_scope"]
        == "public-addresses-with-configured-allowlist-and-loopback-exemption"
        and edge.attributes["dns_scope"] == "connection-pinned-when-enforced"
        and edge.attributes["proxy_scope"] == "disabled-when-enforced"
        and edge.attributes["enforcement_default"] == "enabled"
        and edge.attributes["bypass_environments"]
        == [
            "LANGFLOW_SSRF_PROTECTION_ENABLED",
            "LANGFLOW_CONNECTOR_SSRF_VALIDATION_ENABLED",
        ]
        for edge in edges
    )

    for name, relative, before, after in (
        (
            "disabled-default",
            "lfx/services/settings/groups/security.py",
            "ssrf_protection_enabled: bool = True",
            "ssrf_protection_enabled: bool = False",
        ),
        (
            "unpinned-backend",
            "lfx/utils/ssrf_transport.py",
            "connect_tcp(host=pinned_ip)",
            "connect_tcp(host='re-resolved.example')",
        ),
        (
            "unproven-allowlist",
            "lfx/utils/ssrf_protection.py",
            "return hostname in get_allowed_hosts()",
            "return False",
        ),
        (
            "unproven-loopback-policy",
            "lfx/utils/ssrf_protection.py",
            'os.getenv("LANGFLOW_CONNECTOR_SSRF_ALLOW_LOOPBACK")',
            'os.getenv("UNRELATED_LOOPBACK_FLAG")',
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.target_kind == "control" and edge.target_name == "network-ssrf-policy"
            for edge in incomplete_ir.relationships
        )


def test_typescript_configurable_ssrf_composition_preserves_disabled_default(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_configurable_ssrf_composition"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis")
        == "typescript-configurable-ssrf-composition"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("web-fetch.tool.ts", 18)
    ]
    assert edges[0].attributes == {
        "control_path": "composition.ts",
        "control_line": 14,
        "scope": "production",
        "policy_effect": "validates-url-and-resolved-host-when-enforced",
        "frontend": "typescript",
        "analysis": "typescript-configurable-ssrf-composition",
        "initial_origin_scope": "configured-address-policy-when-enforced",
        "redirect_scope": "bounded-each-hop-hooks-when-enforced",
        "dns_scope": "secure-lookup-configured-when-enforced",
        "proxy_scope": "unresolved",
        "enforcement_default": "disabled",
        "escape_hatch": "default-disabled",
        "enforcement_mode": "configured-opt-in",
        "enable_environment": "N8N_SSRF_PROTECTION_ENABLED",
        "config_path": "config.ts",
        "config_line": 4,
        "service_path": "service.ts",
        "passthrough_path": "ssrf-guard.ts",
        "discovery_path": "discovery.ts",
        "helper_path": "web-fetch.utils.ts",
        "helper_line": 14,
        "approval_scope": "domain-hitl-independent",
    }
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
        if finding.rule_id == "AV-NET001"
    ] == [("AV-NET001", "web-fetch.tool.ts", 18)]
    assert not any(
        finding.rule_id == "AV-NET001"
        and finding.evidence.path == "raw.ts"
        for finding in ir.findings
    )

    enabled = tmp_path / "enabled-default"
    shutil.copytree(root, enabled)
    config_path = enabled / "config.ts"
    config_source = config_path.read_text(encoding="utf-8")
    config_path.write_text(
        config_source.replace("enabled: boolean = false", "enabled: boolean = true"),
        encoding="utf-8",
    )
    enabled_ir = scan_repository(enabled)
    enabled_edges = [
        edge
        for edge in enabled_ir.relationships
        if edge.attributes.get("analysis")
        == "typescript-configurable-ssrf-composition"
    ]
    assert len(enabled_edges) == 1
    assert enabled_edges[0].attributes["enforcement_default"] == "enabled"
    assert enabled_edges[0].attributes["escape_hatch"] == "configured-opt-out"
    assert enabled_edges[0].attributes["enforcement_mode"] == "configured-opt-out"

    for name, relative, before, after in (
        (
            "passthrough-composition",
            "composition.ts",
            "? this.ssrfProtectionService",
            "? createPassthroughSsrfGuard()",
        ),
        (
            "ordinary-lookup",
            "web-fetch.utils.ts",
            "lookup: ssrf.createSecureLookup()",
            "lookup: ordinaryLookup",
        ),
        (
            "unchecked-redirect",
            "web-fetch.utils.ts",
            "ssrf.validateRedirectSync(opts.href)",
            "observeRedirect(opts.href)",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis")
            == "typescript-configurable-ssrf-composition"
            for edge in incomplete_ir.relationships
        )


def test_typescript_flowise_secure_request_composition_preserves_proxy_residual(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_flowise_secure_request"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis")
        == "typescript-flowise-secure-request-composition"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("HTTP.ts", 31)
    ]
    assert edges[0].attributes == {
        "scope": "production",
        "policy_effect": "validates-and-pins-addresses-unless-proxied",
        "frontend": "typescript",
        "analysis": "typescript-flowise-secure-request-composition",
        "initial_origin_scope": "default-address-denylist-when-enforced",
        "redirect_scope": "each-hop-validated",
        "dns_scope": "connection-pinned-unless-proxied",
        "proxy_scope": "environment-dependent",
        "transport_scope": "fixed-caller-config",
        "enforcement_default": "enabled",
        "escape_hatch": "configured-opt-out",
        "enforcement_mode": "configured-opt-out",
        "disable_environment": "HTTP_SECURITY_CHECK",
        "denylist_environment": "HTTP_DENY_LIST",
        "ipv4_mapped_ipv6": "normalized",
        "helper_path": "httpSecurity.ts",
        "helper_line": 33,
    }
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
        if finding.rule_id == "AV-NET001"
        and finding.evidence.path == "HTTP.ts"
    ] == [("AV-NET001", "HTTP.ts", 31)]
    assert not any(
        finding.rule_id == "AV-NET001" and finding.evidence.path == "raw.ts"
        for finding in ir.findings
    )

    for name, relative, before, after in (
        (
            "default-off",
            "httpSecurity.ts",
            "process.env.HTTP_SECURITY_CHECK !== 'false'",
            "process.env.HTTP_SECURITY_CHECK === 'true'",
        ),
        (
            "automatic-redirects",
            "httpSecurity.ts",
            "maxRedirects: 0",
            "maxRedirects: 5",
        ),
        (
            "unpinned-agent",
            "httpSecurity.ts",
            "cb(null, target.ip, target.family)",
            "cb(null, _host, target.family)",
        ),
        (
            "caller-proxy",
            "HTTP.ts",
            "return await secureAxiosRequest(requestConfig)",
            "requestConfig.proxy = {}\n    return await secureAxiosRequest(requestConfig)",
        ),
        (
            "unnormalized-mapped-ipv6",
            "httpSecurity.ts",
            "parsedIp = ipv6Addr.toIPv4Address()",
            "parsedIp = ipv6Addr",
        ),
        (
            "no-deny-match",
            "httpSecurity.ts",
            "parsedIp.match(parsedRange, adjustedMask)",
            "publicMatch(parsedIp, parsedRange, adjustedMask)",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis")
            == "typescript-flowise-secure-request-composition"
            for edge in incomplete_ir.relationships
        )


def test_typescript_flowise_secure_fetch_composition_overrides_caller_agent(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_flowise_secure_request"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis")
        == "typescript-flowise-secure-fetch-composition"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("WebScraperTool.ts", 9)
    ]
    assert edges[0].attributes == {
        "scope": "production",
        "policy_effect": "validates-and-pins-addresses",
        "frontend": "typescript",
        "analysis": "typescript-flowise-secure-fetch-composition",
        "initial_origin_scope": "default-address-denylist-when-enforced",
        "redirect_scope": "each-hop-validated",
        "dns_scope": "connection-pinned",
        "proxy_scope": "pinned-agent",
        "transport_scope": "caller-agent-overridden",
        "enforcement_default": "enabled",
        "escape_hatch": "configured-opt-out",
        "enforcement_mode": "configured-opt-out",
        "disable_environment": "HTTP_SECURITY_CHECK",
        "denylist_environment": "HTTP_DENY_LIST",
        "ipv4_mapped_ipv6": "normalized",
        "helper_path": "httpSecurity.ts",
        "helper_line": 83,
    }
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
        if finding.rule_id == "AV-NET001"
        and finding.evidence.path == "WebScraperTool.ts"
    ] == [("AV-NET001", "WebScraperTool.ts", 9)]
    assert not any(
        finding.rule_id == "AV-NET001" and finding.evidence.path == "raw-fetch.ts"
        for finding in ir.findings
    )
    without_barrel = scan_repository(
        root,
        selected_paths=["WebScraperTool.ts", "httpSecurity.ts"],
    )
    assert not any(
        edge.attributes.get("analysis")
        == "typescript-flowise-secure-fetch-composition"
        for edge in without_barrel.relationships
    )

    for name, relative, before, after in (
        (
            "fetch-default-off",
            "httpSecurity.ts",
            "process.env.HTTP_SECURITY_CHECK !== 'false'",
            "process.env.HTTP_SECURITY_CHECK === 'true'",
        ),
        (
            "fetch-automatic-redirects",
            "httpSecurity.ts",
            "redirect: 'manual' as const",
            "redirect: 'follow' as const",
        ),
        (
            "fetch-unpinned-agent",
            "httpSecurity.ts",
            "agent: () => agent",
            "agent: init.agent",
        ),
        (
            "fetch-fixed-entrypoint",
            "WebScraperTool.ts",
            "this.scrapeRecursive(initialInput, 1)",
            "this.scrapeRecursive('https://example.test', 1)",
        ),
        (
            "fetch-broken-class-hop",
            "WebScraperTool.ts",
            "this.scrapeSingleUrl(url)",
            "this.scrapeSingleUrl('https://example.test')",
        ),
        (
            "fetch-wrong-import",
            "WebScraperTool.ts",
            "from './index'",
            "from './raw-fetch'",
        ),
        (
            "fetch-broken-barrel",
            "index.ts",
            "export * from './httpSecurity'",
            "export * from './raw-fetch'",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis")
            == "typescript-flowise-secure-fetch-composition"
            for edge in incomplete_ir.relationships
        )


def test_typescript_google_adk_fetch_preserves_preflight_dns_residual(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_google_adk_secure_fetch"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis")
        == "typescript-google-adk-load-web-page-composition"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("load_web_page.ts", 69)
    ]
    assert edges[0].attributes == {
        "scope": "production",
        "policy_effect": "validates-public-addresses-preflight",
        "frontend": "typescript",
        "analysis": "typescript-google-adk-load-web-page-composition",
        "initial_origin_scope": "public-addresses-preflight",
        "redirect_scope": "disabled",
        "dns_scope": "preflight-only-rebinding-residual",
        "proxy_scope": "unresolved",
        "transport_scope": "global-fetch-unpinned",
        "enforcement_default": "enabled",
        "escape_hatch": "none",
        "enforcement_mode": "always-on",
        "ipv4_mapped_ipv6": "normalized",
        "helper_path": "load_web_page.ts",
        "helper_line": 58,
    }
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
        if finding.rule_id == "AV-NET001"
    ] == [("AV-NET001", "load_web_page.ts", 69)]
    assert not any(
        finding.rule_id == "AV-NET001" and finding.evidence.path == "raw.ts"
        for finding in ir.findings
    )
    without_tool_class = scan_repository(
        root,
        selected_paths=["load_web_page.ts"],
    )
    assert not any(
        edge.attributes.get("analysis")
        == "typescript-google-adk-load-web-page-composition"
        for edge in without_tool_class.relationships
    )

    for name, relative, before, after in (
        (
            "adk-auto-redirect",
            "load_web_page.ts",
            "redirect: 'manual'",
            "redirect: 'follow'",
        ),
        (
            "adk-no-preflight",
            "load_web_page.ts",
            "await validateResolvedAddresses(normalizeHost(parsed.hostname))",
            "await Promise.resolve()",
        ),
        (
            "adk-incomplete-address-check",
            "load_web_page.ts",
            "addresses.some(isBlockedAddress)",
            "addresses.every(isBlockedAddress)",
        ),
        (
            "adk-mapped-ip-bypass",
            "load_web_page.ts",
            "value >> 32n === 0xffffn",
            "value >> 32n !== 0xffffn",
        ),
        (
            "adk-fixed-tool-input",
            "load_web_page.ts",
            "execute: ({url}) => loadWebPage(url)",
            "execute: ({url}) => loadWebPage('https://example.test')",
        ),
        (
            "adk-wrong-tool-import",
            "load_web_page.ts",
            "from './function_tool.js'",
            "from './raw.js'",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis")
            == "typescript-google-adk-load-web-page-composition"
            for edge in incomplete_ir.relationships
        )


def test_typescript_axios_instances_preserve_absolute_url_override_semantics(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_axios_instance"
    ir = scan_repository(root)
    capabilities = [
        item
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.evidence.path == "direct.ts"
    ]
    assert [
        (
            item.evidence.line,
            item.attributes["api"],
            item.attributes["dynamic_origin"],
            item.attributes.get("base_url_scope"),
            item.attributes.get("absolute_url_override"),
        )
        for item in capabilities
    ] == [
        (12, "axios.instance.get", True, "fixed-origin", "allowed"),
        (16, "axios.instance.request", True, "fixed-origin", "allowed"),
        (20, "axios.get", True, None, None),
        (25, "axios.instance.get", False, "fixed-origin", "allowed"),
        (29, "axios.instance.get", False, "fixed-origin", "disabled"),
        (33, "axios.instance.get", True, "absent", "disabled"),
    ]
    assert [
        finding.evidence.line
        for finding in ir.findings
        if finding.rule_id == "AV-NET001" and finding.evidence.path == "direct.ts"
    ] == [12, 16, 20, 33]
    assert not any(
        item.kind == "capability" and item.evidence.path == "shadowed.ts"
        for item in ir.components
    )

    locked = tmp_path / "locked-override-enabled"
    shutil.copytree(root, locked)
    locked_path = locked / "direct.ts"
    source = locked_path.read_text(encoding="utf-8")
    locked_path.write_text(
        source.replace("allowAbsoluteUrls: false,", "allowAbsoluteUrls: true,", 1),
        encoding="utf-8",
    )
    locked_ir = scan_repository(locked)
    assert any(
        finding.rule_id == "AV-NET001"
        and finding.evidence.path == "direct.ts"
        and finding.evidence.line == 29
        for finding in locked_ir.findings
    )

    wrong_import = tmp_path / "wrong-import"
    shutil.copytree(root, wrong_import)
    wrong_import_path = wrong_import / "direct.ts"
    source = wrong_import_path.read_text(encoding="utf-8")
    wrong_import_path.write_text(
        source.replace('from "axios"', 'from "./local-http"'),
        encoding="utf-8",
    )
    wrong_import_ir = scan_repository(wrong_import)
    assert not any(
        item.attributes.get("summary") == "same-file-axios-instance"
        for item in wrong_import_ir.components
    )


def test_typescript_activepieces_imported_axios_control_preserves_proxy_residual(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_activepieces_safe_http"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis")
        == "typescript-imported-filtering-axios-instance"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("mcp-transport.ts", 8)
    ]
    assert edges[0].attributes == {
        "scope": "production",
        "policy_effect": "filters-connected-addresses-unless-proxied",
        "frontend": "typescript",
        "analysis": "typescript-imported-filtering-axios-instance",
        "initial_origin_scope": "http-https-with-connected-address-filter",
        "redirect_scope": "each-direct-connection-filtered",
        "dns_scope": "connection-time-filtered-unless-proxied",
        "proxy_scope": "environment-dependent",
        "transport_scope": "imported-axios-client-instance",
        "enforcement_default": "enabled",
        "escape_hatch": "configured-address-allowlist",
        "enforcement_mode": "always-on-with-configured-exceptions",
        "allowlist_environment": "AP_SSRF_ALLOW_LIST",
        "allowlist_scope": "ip-or-cidr",
        "filter_library": "request-filtering-agent",
        "filter_library_version": "3.2.0",
        "manifest_path": "package.json",
        "helper_path": "safe-http.ts",
        "helper_line": 31,
        "transport_path": "mcp-transport.ts",
        "transport_line": 19,
        "entry_path": "mcp-tool-validator.ts",
        "entry_line": 4,
    }
    capability = next(
        item
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "imported-axios-client-instance"
    )
    assert capability.attributes["origin_authority"] == "configured-mcp-server"
    assert capability.attributes["dynamic_origin"] is False
    assert not any(
        finding.rule_id == "AV-NET001"
        and finding.evidence.path == "mcp-transport.ts"
        for finding in ir.findings
    )
    protocol_edges = [
        edge
        for edge in ir.relationships
        if edge.source_kind == "protocol"
        and edge.source_name == "MCP"
        and edge.relation == "uses"
        and edge.target_name == "network"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in protocol_edges] == [
        ("mcp-transport.ts", 8)
    ]

    without_manifest = scan_repository(
        root,
        selected_paths=["safe-http.ts", "mcp-transport.ts", "mcp-tool-validator.ts"],
    )
    assert not any(
        edge.attributes.get("analysis")
        == "typescript-imported-filtering-axios-instance"
        for edge in without_manifest.relationships
    )

    for name, relative, before, after in (
        (
            "private-addresses-enabled",
            "safe-http.ts",
            "allowPrivateIPAddress: false",
            "allowPrivateIPAddress: true",
        ),
        (
            "caller-overrides-agent",
            "safe-http.ts",
            "...config,\n    httpAgent,\n    httpsAgent,",
            "httpAgent,\n    httpsAgent,\n    ...config,",
        ),
        (
            "wrong-safe-import",
            "mcp-transport.ts",
            'from "./safe-http"',
            'from "./raw-http"',
        ),
        (
            "caller-proxy",
            "mcp-transport.ts",
            "method, url, headers, data: init?.body,",
            "method, url, headers, proxy: {}, data: init?.body,",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis")
            == "typescript-imported-filtering-axios-instance"
            for edge in incomplete_ir.relationships
        )


def test_typescript_composio_safe_fetch_preserves_runtime_and_route_residuals(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_composio_ssrf_safe_fetch"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis")
        == "typescript-imported-undici-ssrf-safe-fetch"
    ]
    assert [
        (
            edge.evidence.path,
            edge.evidence.line,
            edge.attributes["call_helper"],
            edge.attributes["enforcement_mode"],
            edge.attributes["edge_runtime_scope"],
        )
        for edge in edges
    ] == [
        (
            "RemoteFile.ts",
            7,
            "ssrfSafeFetchWhereSupported",
            "node-filtered-edge-unenforced",
            "unguarded-fetch",
        ),
        (
            "RemoteFile.ts",
            11,
            "ssrfSafeFetchWhereSupported",
            "node-filtered-edge-unenforced",
            "unguarded-fetch",
        ),
        (
            "ToolRouterSessionFileMount.ts",
            5,
            "ssrfSafeFetch",
            "node-filtered-edge-fail-closed",
            "fail-closed",
        ),
        (
            "ToolRouterSessionFileMount.ts",
            10,
            "ssrfSafeFetchWhereSupported",
            "node-filtered-edge-unenforced",
            "unguarded-fetch",
        ),
    ]
    assert {edge.attributes["dns_scope"] for edge in edges} == {
        "connection-pinned-unless-configured-route"
    }
    assert {edge.attributes["proxy_scope"] for edge in edges} == {
        "caller-global-or-environment-dependent"
    }
    assert {edge.attributes["filter_library_version"] for edge in edges} == {
        "^7.29.0"
    }
    capabilities = [
        item
        for item in ir.components
        if item.kind == "capability"
        and item.attributes.get("summary") == "imported-undici-ssrf-safe-fetch"
    ]
    assert [
        (item.evidence.path, item.evidence.line, item.attributes["dynamic_origin"])
        for item in capabilities
    ] == [
        ("RemoteFile.ts", 7, False),
        ("RemoteFile.ts", 11, False),
        ("ToolRouterSessionFileMount.ts", 5, True),
        ("ToolRouterSessionFileMount.ts", 10, False),
    ]

    without_manifest = scan_repository(
        root,
        selected_paths=[
            "RemoteFile.ts",
            "ToolRouterSessionFileMount.ts",
            "pinnedDispatcher.node.ts",
            "ssrfGuard.node.ts",
            "ssrfGuard.workerd.ts",
        ],
    )
    assert not any(
        edge.attributes.get("analysis")
        == "typescript-imported-undici-ssrf-safe-fetch"
        for edge in without_manifest.relationships
    )

    for name, relative, before, after in (
        (
            "automatic-redirect",
            "ssrfGuard.node.ts",
            "{ ...init, redirect: 'manual', dispatcher }",
            "{ ...init, dispatcher }",
        ),
        (
            "metadata-range-removed",
            "ssrfGuard.node.ts",
            "['169.254.0.0', 16]",
            "['11.0.0.0', 8]",
        ),
        (
            "unpinned-dispatcher",
            "pinnedDispatcher.node.ts",
            "addresses.map(address => ({ address, family: isIP(address) }))",
            "[{ address: _hostname, family: 0 }]",
        ),
        (
            "edge-does-not-fail-closed",
            "ssrfGuard.workerd.ts",
            "throw new ComposioBlockedInternalUrlError('unsupported', { cause: rawUrl });",
            "return fetch(rawUrl);",
        ),
        (
            "wrong-guard-import",
            "ToolRouterSessionFileMount.ts",
            "from '#ssrf_guard'",
            "from './raw'",
        ),
        (
            "wrong-runtime-map",
            "package.json",
            '"workerd": "./dist/utils/ssrfGuard.workerd.mjs"',
            '"workerd": "./dist/utils/ssrfGuard.node.mjs"',
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis")
            == "typescript-imported-undici-ssrf-safe-fetch"
            for edge in incomplete_ir.relationships
        )


def test_typescript_composio_cli_upload_resolves_tool_arguments_to_raw_fetch(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_composio_cli_upload"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis") == "typescript-composio-cli-file-upload-flow"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("tool-file-uploads.ts", 2)
    ]
    capability = next(
        item
        for item in ir.components
        if item.kind == "capability"
        and item.attributes.get("analysis") == "typescript-composio-cli-file-upload-flow"
    )
    assert capability.attributes["dynamic_origin"] is True
    assert capability.attributes["origin_authority"] == "tool-execution-arguments"
    assert capability.attributes["destination_policy"] == "absent-on-proven-path"
    assert any(
        finding.rule_id == "AV-NET001"
        and finding.evidence.path == "tool-file-uploads.ts"
        and finding.evidence.line == 2
        for finding in ir.findings
    )

    for name, relative, before, after in (
        (
            "guarded-fetch",
            "tool-file-uploads.ts",
            "fetch(url)",
            "ssrfSafeFetch(url)",
        ),
        (
            "fixed-arguments",
            "tools-executor.ts",
            "arguments_: params.arguments",
            "arguments_: {}",
        ),
        (
            "broken-schema-gate",
            "tool-file-uploads.ts",
            "schema?.file_uploadable === true",
            "schema?.file_uploadable === false",
        ),
        (
            "wrong-import",
            "tools-executor.ts",
            "from 'src/services/tool-file-uploads'",
            "from './raw'",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis") == "typescript-composio-cli-file-upload-flow"
            for edge in incomplete_ir.relationships
        )


def test_typescript_google_adk_openapi_tool_keeps_model_input_off_origin(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_google_adk_openapi_rest_tool"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis") == "typescript-google-adk-openapi-rest-tool"
    ]
    assert {
        (edge.source_kind, edge.relation, edge.target_kind, edge.target_name)
        for edge in edges
    } == {
        ("tool", "uses", "capability", "network"),
        ("capability", "governed-by", "control", "network-origin-policy"),
    }
    assert {edge.evidence.line for edge in edges} == {15}
    capability = next(
        item
        for item in ir.components
        if item.kind == "capability"
        and item.attributes.get("analysis") == "typescript-google-adk-openapi-rest-tool"
    )
    assert capability.attributes["dynamic_origin"] is False
    assert capability.attributes["configured_origin"] is True
    assert capability.attributes["origin_authority"] == "openapi-server-configuration"
    control = next(
        item
        for item in ir.components
        if item.kind == "control"
        and item.attributes.get("analysis") == "typescript-google-adk-openapi-rest-tool"
    )
    assert control.attributes["model_path_scope"] == "segment-encoded"
    assert control.attributes["dot_segment_policy"] == "rejected"
    assert control.attributes["credential_url_scope"] == "query-only"
    assert not any(finding.rule_id == "AV-NET001" for finding in ir.findings)

    for name, relative, before, after in (
        (
            "model-controlled-base",
            "rest_api_tool.ts",
            "`${endpoint.baseUrl}${resolvedPath}`",
            "`${args.url}${resolvedPath}`",
        ),
        (
            "unencoded-path",
            "rest_api_tool.ts",
            "return encodeURIComponent(value)",
            "return value",
        ),
        (
            "raw-path-binding",
            "rest_api_tool.ts",
            "pathParams[originalName] = encodePathParamValue(originalName, String(argValue))",
            "pathParams[originalName] = String(argValue)",
        ),
        (
            "dynamic-server-variable",
            "openapi_spec_parser.ts",
            "variable?.default || variable?.enum?.[0]",
            "process.env[name]",
        ),
        (
            "credential-rewrites-url",
            "auth_helpers.ts",
            "url += `${separator}key=${encodeURIComponent(credential.apiKey)}`",
            "url = credential.apiKey",
        ),
        (
            "wrong-tool-factory-import",
            "openapi_toolset.ts",
            "from './rest_api_tool.js'",
            "from './raw.js'",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis") == "typescript-google-adk-openapi-rest-tool"
            for edge in incomplete_ir.relationships
        )


def test_openai_agents_python_mcp_tools_inherit_disabled_approval_default(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/python_openai_mcp_approval_default"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis")
        == "python-openai-agents-mcp-approval-default"
    ]
    assert {
        (edge.source_kind, edge.relation, edge.target_kind, edge.target_name)
        for edge in edges
    } == {
        ("agent", "uses", "mcp-server", "Reference Policy Server"),
        ("mcp-server", "configured-by", "control-setting", "mcp-tool-approval"),
    }
    setting = next(
        item
        for item in ir.components
        if item.kind == "control-setting"
        and item.name == "mcp-tool-approval"
        and item.attributes.get("analysis")
        == "python-openai-agents-mcp-approval-default"
    )
    assert setting.attributes["enabled"] is False
    assert setting.attributes["approval_policy"] == "disabled-default"
    assert setting.attributes["policy_scope"] == "all-discovered-mcp-tools"
    assert setting.attributes["missing_tool_mapping_default"] == "disabled"
    assert not any(finding.rule_id == "AV-APPROVAL001" for finding in ir.findings)

    for name, relative, before, after in (
        (
            "explicit-approval",
            "app.py",
            'name="Reference Policy Server",',
            'name="Reference Policy Server", require_approval="always",',
        ),
        (
            "wrong-import",
            "app.py",
            "from agents.mcp import MCPServerStdio",
            "from local_mcp import MCPServerStdio",
        ),
        (
            "enabled-sdk-default",
            "server.py",
            "require_approval=None",
            "require_approval=True",
        ),
        (
            "fail-closed-normalization",
            "server.py",
            "if require_approval is None:\n            return False",
            "if require_approval is None:\n            return True",
        ),
        (
            "hardcoded-wrapper-approval",
            "util.py",
            "needs_approval=needs_approval",
            "needs_approval=True",
        ),
        (
            "different-server-binding",
            "app.py",
            "mcp_servers=[server]",
            "mcp_servers=[other_server]",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis")
            == "python-openai-agents-mcp-approval-default"
            for edge in incomplete_ir.relationships
        )


def test_typescript_a2a_remote_cards_preserve_endpoint_authority_and_transport(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_a2a_card_endpoint"
    ir = scan_repository(root)
    capabilities = [
        item
        for item in ir.components
        if item.kind == "capability" and item.name == "a2a-rpc"
    ]
    assert [
        (item.evidence.path, item.evidence.line, item.attributes["analysis"])
        for item in capabilities
    ] == [
        (
            "a2a_remote_agent.ts",
            26,
            "typescript-adk-a2a-card-endpoint-composition",
        ),
        (
            "gemini_manager.ts",
            60,
            "typescript-gemini-a2a-card-endpoint-composition",
        ),
    ]
    assert capabilities[0].attributes == {
        "scope": "production",
        "frontend": "typescript",
        "protocol": "a2a",
        "dynamic_origin": False,
        "origin_authority": "remote-agent-card",
        "remote_card_endpoint_scope": "unconstrained",
        "analysis": "typescript-adk-a2a-card-endpoint-composition",
        "card_source_scope": "configuration-object-url-or-local-file",
        "card_fetch_scope": "sdk-default-resolver",
        "rpc_origin_scope": "remote-card-controlled",
        "rpc_scheme_scope": "remote-card-controlled",
        "advertised_interface_scope": "sdk-selected",
        "redirect_scope": "sdk-default-unresolved",
        "dns_scope": "sdk-default-unresolved",
        "proxy_scope": "sdk-default-unresolved",
        "transport_scope": "sdk-client-factory",
        "endpoint_policy": "absent-on-proven-path",
        "resolver_path": "agent_card.ts",
        "resolver_line": 5,
    }
    assert capabilities[1].attributes == {
        "scope": "production",
        "frontend": "typescript",
        "protocol": "a2a",
        "dynamic_origin": False,
        "origin_authority": "remote-agent-card",
        "remote_card_endpoint_scope": "unconstrained",
        "analysis": "typescript-gemini-a2a-card-endpoint-composition",
        "card_source_scope": "configured-url-or-inline-json",
        "card_fetch_scope": "unauthenticated-first-auth-retry",
        "rpc_origin_scope": "remote-card-controlled",
        "rpc_scheme_scope": "remote-card-controlled-grpc-allows-insecure",
        "advertised_interface_scope": "sdk-selected",
        "redirect_scope": "sdk-default-unresolved",
        "dns_scope": "dispatcher-default-unpinned",
        "proxy_scope": "configuration-dependent",
        "transport_scope": "undici-agent-or-proxy",
        "endpoint_policy": "absent-on-proven-path",
    }
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
        if finding.rule_id == "AV-A2A001"
    ] == [
        ("AV-A2A001", "a2a_remote_agent.ts", 26),
        ("AV-A2A001", "gemini_manager.ts", 60),
    ]
    assert all(
        finding.ir_path == ("protocol:A2A", "capability:a2a-rpc")
        and finding.analysis["protocol"] == "A2A"
        for finding in ir.findings
        if finding.rule_id == "AV-A2A001"
    )
    assert not any(
        finding.rule_id == "AV-A2A001" and finding.evidence.path == "raw.ts"
        for finding in ir.findings
    )

    without_resolver = scan_repository(
        root,
        selected_paths=["a2a_remote_agent.ts"],
    )
    assert not any(
        item.attributes.get("analysis")
        == "typescript-adk-a2a-card-endpoint-composition"
        for item in without_resolver.components
    )

    for name, relative, before, after, analysis in (
        (
            "a2a-fixed-resolver",
            "agent_card.ts",
            "resolver.resolve(source)",
            "resolver.resolve('https://fixed.example/card')",
            "typescript-adk-a2a-card-endpoint-composition",
        ),
        (
            "a2a-fixed-card",
            "a2a_remote_agent.ts",
            "factory.createFromAgentCard(this.card)",
            "factory.createFromAgentCard({url: 'https://fixed.example/rpc'})",
            "typescript-adk-a2a-card-endpoint-composition",
        ),
        (
            "a2a-intervening-validator",
            "a2a_remote_agent.ts",
            "this.card = await resolveAgentCard(this.a2aConfig.agentCard);",
            "this.card = await resolveAgentCard(this.a2aConfig.agentCard);\n      await validateCardOrigin(this.card);",
            "typescript-adk-a2a-card-endpoint-composition",
        ),
        (
            "a2a-wrong-resolver-import",
            "a2a_remote_agent.ts",
            "from './agent_card.js'",
            "from './raw.js'",
            "typescript-adk-a2a-card-endpoint-composition",
        ),
        (
            "gemini-fixed-card",
            "gemini_manager.ts",
            "factory.createFromAgentCard(agentCard)",
            "factory.createFromAgentCard({url: 'https://fixed.example/rpc'})",
            "typescript-gemini-a2a-card-endpoint-composition",
        ),
        (
            "gemini-unproven-dispatcher",
            "gemini_manager.ts",
            "dispatcher: this.a2aDispatcher",
            "dispatcher: undefined",
            "typescript-gemini-a2a-card-endpoint-composition",
        ),
        (
            "gemini-intervening-validator",
            "gemini_manager.ts",
            "const agentCard = normalizeAgentCard(rawCard);",
            "const agentCard = normalizeAgentCard(rawCard);\n    validateCardOrigin(agentCard, options);",
            "typescript-gemini-a2a-card-endpoint-composition",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            item.attributes.get("analysis") == analysis
            for item in incomplete_ir.components
        )


def test_python_a2a_card_policy_requires_all_interfaces_and_dominating_validation(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/python_a2a_card_endpoint"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.target_kind == "control"
        and edge.target_name == "a2a-card-rpc-origin-policy"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("remote_a2a_agent.py", 41),
        ("remote_a2a_agent.py", 48),
    ]
    assert all(
        edge.attributes["analysis"]
        == "python-google-adk-a2a-card-endpoint-policy"
        and edge.attributes["rpc_origin_scope"] == "same-origin-with-card-source"
        and edge.attributes["rpc_scheme_scope"] == "https-or-loopback-http"
        and edge.attributes["advertised_interface_scope"] == "all-rpc-urls"
        and edge.attributes["enforcement_mode"] == "always-on-for-network-cards"
        and edge.attributes["control_line"] == 21
        for edge in edges
    )
    assert not any(finding.rule_id == "AV-A2A001" for finding in ir.findings)

    for name, before, after in (
        (
            "a2a-primary-only",
            "_compat.agent_card_rpc_urls(agent_card)",
            "[_compat.agent_card_url(agent_card)]",
        ),
        (
            "a2a-cross-origin-allowed",
            "card_origin != source_origin",
            "card_origin == source_origin",
        ),
        (
            "a2a-http-allowed",
            'parsed_card.scheme.lower() != "https"',
            'parsed_card.scheme.lower() == "https"',
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / "remote_a2a_agent.py"
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.target_kind == "control"
            and edge.target_name == "a2a-card-rpc-origin-policy"
            for edge in incomplete_ir.relationships
        )


def test_typescript_network_helper_summaries_map_object_parameters_and_multiline_aliases(
    tmp_path: Path,
) -> None:
    (tmp_path / "tools.ts").write_text(
        """import { createTool } from "@mastra/core/tools";

class Helpers {
  static async request({ baseUrl, route }: { baseUrl: string; route: string }) {
    const fullUrl = `${baseUrl}${route}`;
    return fetch(fullUrl);
  }
}

const request = createTool({
  id: "request",
  execute: async (inputData) => {
    const {
      baseUrl,
      route,
    } = inputData;
    return Helpers.request({
      baseUrl,
      route,
    });
  },
});
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    summarized = [
        item
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "same-file-helper"
    ]
    assert len(summarized) == 1
    assert summarized[0].attributes == {
        "scope": "production",
        "api": "request",
        "dynamic_origin": True,
        "summary": "same-file-helper",
        "helper_line": 4,
        "helper_network_calls": 1,
    }
    assert [
        (edge.source_name, edge.source_id)
        for edge in ir.relationships
        if edge.target_kind == "capability" and edge.target_name == "network"
    ] == [("request", "ts:tools.ts#tool:request")]
    assert [finding.rule_id for finding in ir.findings] == ["AV-NET001"]


def test_typescript_imported_path_boundary_suppresses_only_proven_guard() -> None:
    ir = scan_repository(ROOT / "cases/typescript_path_boundary")

    filesystem = {
        item.evidence.line: item.attributes
        for item in ir.components
        if item.kind == "capability"
        and item.name == "filesystem"
        and item.evidence.path == "tools.ts"
    }
    assert filesystem == {
        10: {
            "scope": "production",
            "write_access": True,
            "dynamic_path": True,
            "path_boundary_guard": True,
            "path_boundary_scope": "constrained",
        },
        16: {
            "scope": "production",
            "write_access": True,
            "dynamic_path": True,
            "path_boundary_guard": False,
            "path_boundary_scope": "unresolved",
        },
        23: {
            "scope": "production",
            "write_access": True,
            "dynamic_path": True,
            "path_boundary_guard": False,
            "path_boundary_scope": "unresolved",
        },
    }
    controls = [
        item for item in ir.components if item.kind == "control" and item.name == "path-boundary"
    ]
    assert len(controls) == 1
    assert controls[0].evidence.path == "guard.ts"
    assert controls[0].evidence.line == 6
    assert controls[0].attributes["policy_effect"] == "restricts-filesystem-path"
    assert controls[0].attributes["predicate_path"] == "path-check.ts"
    assert controls[0].attributes["boundary_scope"] == "constrained"
    assert [
        (
            edge.evidence.line,
            edge.target_name,
            edge.attributes.get("control_path"),
            edge.attributes.get("policy_effect"),
            edge.attributes.get("predicate_path"),
            edge.attributes.get("boundary_scope"),
        )
        for edge in ir.relationships
        if edge.source_kind == "capability" and edge.relation == "governed-by"
    ] == [
        (
            10,
            "path-boundary",
            "guard.ts",
            "restricts-filesystem-path",
            "path-check.ts",
            "constrained",
        )
    ]
    assert [
        (finding.rule_id, finding.evidence.line, finding.analysis["tool"])
        for finding in ir.findings
    ] == [
        ("AV-FS001", 16, "unsafe-directory"),
        ("AV-FS001", 23, "reassigned-directory"),
    ]


def test_python_path_boundary_is_ordered_branch_local_and_scope_aware() -> None:
    ir = scan_repository(ROOT / "cases/python_path_boundary")

    filesystem = {
        item.evidence.line: (
            item.attributes["path_boundary_guard"],
            item.attributes["path_boundary_scope"],
        )
        for item in ir.components
        if item.kind == "capability" and item.name == "filesystem"
    }
    assert filesystem == {
        12: (True, "constrained"),
        13: (True, "constrained"),
        22: (True, "constrained"),
        23: (False, "unresolved"),
        32: (False, "unresolved"),
        42: (False, "unresolved"),
        51: (True, "unresolved"),
        59: (False, "unresolved"),
        69: (False, "unresolved"),
        80: (False, "unresolved"),
        89: (False, "unresolved"),
        100: (True, "constrained"),
        111: (False, "unresolved"),
        123: (False, "unresolved"),
        134: (False, "unresolved"),
        145: (False, "unresolved"),
        152: (False, "unresolved"),
        163: (False, "unresolved"),
        176: (False, "unresolved"),
        189: (False, "unresolved"),
    }
    assert [
        (
            edge.evidence.line,
            edge.attributes["control_line"],
            edge.attributes["policy_effect"],
            edge.attributes["boundary_scope"],
            edge.attributes["frontend"],
            edge.attributes["helper"],
        )
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.target_name == "path-boundary"
    ] == [
        (12, 10, "restricts-filesystem-path", "constrained", "python", "Path.is_relative_to"),
        (13, 10, "restricts-filesystem-path", "constrained", "python", "Path.is_relative_to"),
        (22, 21, "restricts-filesystem-path", "constrained", "python", "Path.is_relative_to"),
        (51, 49, "validates-filesystem-path", "unresolved", "python", "Path.is_relative_to"),
        (100, 97, "restricts-filesystem-path", "constrained", "python", "Path.relative_to"),
    ]
    assert [
        (
            edge.evidence.line,
            edge.attributes["control_line"],
            edge.attributes["policy_effect"],
            edge.attributes["strength"],
        )
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.target_name == "path-prefix-check"
    ] == [
        (32, 30, "weak-string-prefix-validation", "weak-prefix"),
        (176, 172, "weak-string-prefix-validation", "weak-prefix"),
    ]
    assert [
        (finding.rule_id, finding.evidence.line, finding.analysis["tool"])
        for finding in ir.findings
    ] == [
        ("AV-FS001", 23, "positive_branch"),
        ("AV-FS002", 32, "prefix_check"),
        ("AV-FS001", 42, "reassigned_candidate"),
        ("AV-FS001", 51, "configured_root"),
        ("AV-FS001", 59, "unresolved_candidate"),
        ("AV-FS001", 69, "reassigned_root"),
        ("AV-FS001", 80, "conditionally_reassigned_candidate"),
        ("AV-FS001", 89, "parent_without_strict_descendant"),
        ("AV-FS001", 111, "relative_to_continuing_handler"),
        ("AV-FS001", 123, "relative_to_nonexclusive_try"),
        ("AV-FS001", 134, "relative_to_parent_without_strict_descendant"),
        ("AV-FS001", 145, "relative_to_rebinds_candidate"),
        ("AV-FS001", 152, "prefix_after_write"),
        ("AV-FS001", 163, "separator_aware_prefix"),
        ("AV-FS002", 176, "prefix_inside_terminating_try"),
        ("AV-FS001", 189, "prefix_inside_continuing_try"),
    ]


def test_python_path_helper_summary_is_return_exact_and_class_local() -> None:
    ir = scan_repository(ROOT / "cases/python_path_helper")

    filesystem = {
        item.evidence.line: (
            item.attributes["path_boundary_guard"],
            item.attributes["path_boundary_scope"],
        )
        for item in ir.components
        if item.kind == "capability" and item.name == "filesystem"
    }
    assert filesystem == {
        23: (True, "unresolved"),
        24: (False, "unresolved"),
        30: (False, "unresolved"),
        48: (False, "unresolved"),
        67: (False, "unresolved"),
        86: (False, "unresolved"),
        104: (False, "unresolved"),
        125: (False, "unresolved"),
        145: (False, "unresolved"),
        165: (False, "unresolved"),
    }
    assert [
        (
            edge.evidence.line,
            edge.attributes["control_line"],
            edge.attributes["helper"],
            edge.attributes["summary"],
            edge.attributes["boundary_scope"],
        )
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.target_name == "path-boundary"
    ] == [(23, 15, "Path.relative_to", "same-class-return", "unresolved")]
    assert [
        (finding.rule_id, finding.evidence.line)
        for finding in ir.findings
    ] == [
        ("AV-FS001", 23),
        ("AV-FS001", 24),
        ("AV-FS001", 30),
        ("AV-FS001", 48),
        ("AV-FS001", 67),
        ("AV-FS001", 86),
        ("AV-FS001", 104),
        ("AV-FS001", 125),
        ("AV-FS001", 145),
        ("AV-FS001", 165),
    ]


def test_python_post_definition_tool_registration_is_exact_and_cross_file() -> None:
    ir = scan_repository(ROOT / "cases/python_post_registration")

    tools = {item.name: item for item in ir.components if item.kind == "tool"}
    assert set(tools) == {
        "direct_wrapped_write",
        "factory_wrapped_write",
        "imported_write",
        "local_write",
        "nested_wrapped_write",
    }
    assert tools["imported_write"].attributes == {
        "decorators": [],
        "needs_approval": True,
        "registration": "post-definition",
        "registration_path": "app/server.py",
        "registration_line": 31,
        "registrar": "mcp.tool",
        "resolution": "relative-import-single-definition",
    }
    assert tools["imported_write"].symbol_id == "py:app/tools.py#tool:imported_write"
    assert tools["local_write"].attributes["resolution"] == (
        "same-module-single-definition"
    )
    assert tools["direct_wrapped_write"].attributes["wrappers"] == ["transparent"]
    assert tools["factory_wrapped_write"].attributes["wrappers"] == ["configured"]
    assert tools["nested_wrapped_write"].attributes["wrappers"] == [
        "transparent",
        "transparent",
    ]
    assert all(
        tools[name].attributes["wrapper_summary"]
        == "metadata-preserving-forwarder"
        for name in (
            "direct_wrapped_write",
            "factory_wrapped_write",
            "nested_wrapped_write",
        )
    )
    assert {
        (edge.source_name, edge.relation, edge.target_name, edge.evidence.path, edge.evidence.line)
        for edge in ir.relationships
    } == {
        ("imported_write", "governed-by", "human-approval", "app/server.py", 31),
        ("imported_write", "uses", "filesystem", "app/tools.py", 5),
        ("local_write", "uses", "filesystem", "app/server.py", 23),
        ("direct_wrapped_write", "uses", "filesystem", "app/tools.py", 21),
        ("factory_wrapped_write", "uses", "filesystem", "app/tools.py", 25),
        ("nested_wrapped_write", "uses", "filesystem", "app/tools.py", 29),
    }
    assert [
        (
            finding.rule_id,
            finding.evidence.path,
            finding.evidence.line,
            finding.analysis["tool"],
            finding.analysis["approval_coverage"],
        )
        for finding in ir.findings
    ] == [
        ("AV-FS001", "app/server.py", 23, "local_write", "unresolved"),
        ("AV-FS001", "app/tools.py", 5, "imported_write", "present"),
        ("AV-FS001", "app/tools.py", 21, "direct_wrapped_write", "unresolved"),
        ("AV-FS001", "app/tools.py", 25, "factory_wrapped_write", "unresolved"),
        ("AV-FS001", "app/tools.py", 29, "nested_wrapped_write", "unresolved"),
    ]


def test_python_browser_evaluate_requires_browser_import_and_tracks_dynamic_input() -> None:
    ir = scan_repository(ROOT / "cases/python_browser_evaluate")

    executions = [
        (
            item.evidence.path,
            item.evidence.line,
            item.attributes["api"],
            item.attributes["execution_context"],
            item.attributes["dynamic_input"],
            item.attributes["receiver_proof"],
        )
        for item in ir.components
        if item.kind == "capability" and item.name == "code-execution"
    ]
    assert executions == [
        ("agent.py", 9, "page.evaluate", "browser-page", True, "parameter-annotation"),
        ("agent.py", 14, "page.evaluate", "browser-page", False, "parameter-annotation"),
        ("agent.py", 20, "page.evaluate", "browser-page", True, "parameter-annotation"),
        (
            "agent.py",
            26,
            "browser_page.evaluate",
            "browser-page",
            True,
            "typed-parameter-alias",
        ),
    ]
    assert [
        (edge.source_name, edge.evidence.line)
        for edge in ir.relationships
        if edge.target_name == "code-execution"
    ] == [
        ("dynamic_evaluate", 9),
        ("literal_evaluate", 14),
        ("aliased_evaluate", 20),
        ("aliased_page", 26),
    ]
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
    ] == [
        ("AV-EXEC002", "agent.py", 9),
        ("AV-EXEC002", "agent.py", 20),
        ("AV-EXEC002", "agent.py", 26),
    ]


def test_python_registry_decorators_are_import_proven_and_entrypoint_scoped() -> None:
    ir = scan_repository(ROOT / "cases/python_registry_tools")

    assert [
        (
            item.name,
            item.evidence.path,
            item.evidence.line,
            item.attributes.get("framework"),
            item.attributes.get("entrypoints"),
        )
        for item in ir.components
        if item.kind == "tool"
    ] == [
        ("direct_tool", "meta.py", 7, "MetaGPT", None),
        ("Runner", "meta.py", 12, "MetaGPT", ["run"]),
        ("OpaqueRunner", "meta.py", 24, "MetaGPT", []),
        ("memory_write", "meta.py", 30, "MetaGPT", None),
        ("fixed_write", "meta.py", 37, "MetaGPT", None),
        ("code_runner", "qwen.py", 7, "Qwen-Agent", ["call"]),
        ("fixed_search", "qwen.py", 25, "Qwen-Agent", ["call"]),
    ]
    assert [
        (edge.source_name, edge.evidence.path, edge.evidence.line)
        for edge in ir.relationships
        if edge.target_name == "code-execution"
    ] == [
        ("direct_tool", "meta.py", 8),
        ("Runner", "meta.py", 14),
        ("code_runner", "qwen.py", 9),
    ]
    assert [
        (item.evidence.path, item.evidence.line, item.attributes["tool_input_path"])
        for item in ir.components
        if item.name == "filesystem"
    ] == [("meta.py", 38, False)]
    assert [
        (item.evidence.line, item.attributes["dynamic_origin"])
        for item in ir.components
        if item.name == "network"
    ] == [(32, False), (33, False)]
    assert [
        (edge.source_name, edge.evidence.line)
        for edge in ir.relationships
        if edge.target_name == "network"
    ] == [("fixed_search", 32), ("fixed_search", 33)]
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
    ] == [
        ("AV-EXEC002", "meta.py", 8),
        ("AV-EXEC002", "meta.py", 14),
        ("AV-EXEC002", "qwen.py", 9),
    ]


def test_python_imported_network_helpers_require_exact_unrebound_imports() -> None:
    ir = scan_repository(ROOT / "cases/python_imported_network_helper")

    assert [
        (
            item.evidence.line,
            item.attributes["dynamic_origin"],
            item.attributes["summary"],
            item.attributes["helper_path"],
            item.attributes["helper_network_lines"],
        )
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "imported-function"
        and item.evidence.path == "pkg/tools.py"
    ] == [
        (15, True, "imported-function", "pkg/helpers.py", [7]),
        (16, False, "imported-function", "pkg/helpers.py", [11]),
        (26, False, "imported-function", "pkg/helpers.py", [7]),
    ]
    assert [
        (edge.source_name, edge.evidence.line)
        for edge in ir.relationships
        if edge.target_name == "network" and edge.evidence.path == "pkg/tools.py"
    ] == [
        ("remote_loader", 15),
        ("remote_loader", 16),
        ("fixed_loader", 26),
    ]
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
        if finding.evidence.path == "pkg/tools.py"
    ] == [("AV-NET001", "pkg/tools.py", 15)]


def test_python_imported_class_network_helpers_are_iterative_and_binding_scoped() -> None:
    ir = scan_repository(ROOT / "cases/python_imported_network_helper")

    assert [
        (
            item.evidence.path,
            item.evidence.line,
            item.attributes["dynamic_origin"],
            item.attributes["api"],
            item.attributes["callee_network_lines"],
        )
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "imported-class-method"
    ] == [
        ("pkg/chain.py", 12, True, "UrlParser.call", [10]),
        ("pkg/class_tools.py", 14, True, "UrlParser.call", [10]),
        ("pkg/class_tools.py", 23, True, "UrlParser.call", [10]),
        ("pkg/class_tools.py", 29, False, "UrlParser.call", [10]),
        ("pkg/class_tools.py", 35, True, "ChainParser.call", [12]),
        ("pkg/class_tools.py", 87, False, "UrlParser.call", [10]),
    ]
    assert [
        (edge.source_name, edge.evidence.path, edge.evidence.line)
        for edge in ir.relationships
        if edge.target_name == "network"
        and edge.evidence.path in {"pkg/chain.py", "pkg/class_tools.py"}
    ] == [
        ("chain_parser", "pkg/chain.py", 12),
        ("direct_class_loader", "pkg/class_tools.py", 14),
        ("bound_class_loader", "pkg/class_tools.py", 23),
        ("fixed_class_loader", "pkg/class_tools.py", 29),
        ("multi_hop_loader", "pkg/class_tools.py", 35),
        ("mixed_field_loader", "pkg/class_tools.py", 87),
    ]
    assert [
        (finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
        if finding.evidence.path in {"pkg/chain.py", "pkg/class_tools.py"}
    ] == [
        ("pkg/chain.py", 12),
        ("pkg/class_tools.py", 14),
        ("pkg/class_tools.py", 23),
        ("pkg/class_tools.py", 35),
    ]


def test_python_filesystem_mutations_resolve_destinations_aliases_and_guards() -> None:
    ir = scan_repository(ROOT / "cases/filesystem_mutations")

    filesystem = {
        item.evidence.line: (
            item.attributes["canonical_api"],
            item.attributes["operation"],
            item.attributes["path_role"],
            item.attributes["dynamic_path"],
            item.attributes["path_boundary_scope"],
        )
        for item in ir.components
        if item.kind == "capability" and item.name == "filesystem"
    }
    assert filesystem == {
        13: ("shutil.copytree", "copy", "destination", True, "unresolved"),
        18: ("shutil.move", "move", "destination", True, "unresolved"),
        23: ("os.replace", "move", "destination", True, "unresolved"),
        28: ("shutil.copy2", "copy", "destination", True, "unresolved"),
        33: ("os.remove", "delete", "target", True, "unresolved"),
        38: ("shutil.copy2", "copy", "destination", False, "unresolved"),
        47: ("shutil.copy2", "copy", "destination", True, "constrained"),
        56: ("shutil.copy2", "copy", "destination", True, "unresolved"),
        74: (
            "shutil.copy|shutil.copy2",
            "copy",
            "destination",
            True,
            "unresolved",
        ),
        85: (
            "shutil.copy|shutil.copy2",
            "copy",
            "destination",
            True,
            "unresolved",
        ),
        97: (
            "shutil.copy|shutil.copy2",
            "copy",
            "destination",
            True,
            "constrained",
        ),
        132: (
            "pathlib.Path.replace",
            "move",
            "destination",
            True,
            "unresolved",
        ),
        138: (
            "pathlib.Path.rename",
            "move",
            "destination",
            True,
            "unresolved",
        ),
        147: (
            "pathlib.Path.rename",
            "move",
            "destination",
            True,
            "constrained",
        ),
    }
    callable_aliases = {
        item.evidence.line: item.attributes["possible_apis"]
        for item in ir.components
        if item.kind == "capability"
        and item.name == "filesystem"
        and item.attributes["callable_alias"]
    }
    assert callable_aliases == {
        74: ["shutil.copy", "shutil.copy2"],
        85: ["shutil.copy", "shutil.copy2"],
        97: ["shutil.copy", "shutil.copy2"],
    }
    path_receivers = {
        item.evidence.line: item.attributes["receiver_proof"]
        for item in ir.components
        if item.kind == "capability"
        and item.name == "filesystem"
        and item.attributes.get("receiver_proof") is not None
    }
    assert path_receivers == {
        132: "explicit-constructor",
        138: "immutable-local",
        147: "explicit-constructor",
    }
    assert [
        (edge.evidence.line, edge.attributes["control_line"])
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.target_name == "path-boundary"
    ] == [(47, 45), (97, 94), (147, 145)]
    assert [
        (edge.evidence.line, edge.attributes["control_line"])
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.target_name == "path-prefix-check"
    ] == [(56, 54)]
    assert [
        (finding.rule_id, finding.evidence.line, finding.analysis["tool"])
        for finding in ir.findings
    ] == [
        ("AV-FS001", 13, "copy_tree"),
        ("AV-FS001", 18, "move_path"),
        ("AV-FS001", 23, "replace_path"),
        ("AV-FS001", 28, "copy_file"),
        ("AV-FS001", 33, "delete_file"),
        ("AV-FS002", 56, "weak_prefix_copy"),
        ("AV-FS001", 74, "local_copy_choice"),
        ("AV-FS001", 85, "branch_copy_choice"),
        ("AV-FS001", 132, "direct_path_replace"),
        ("AV-FS001", 138, "immutable_path_rename"),
    ]


def test_python_filesystem_callable_rebinding_invalidates_state(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """
import shutil
from langchain.tools import tool

def wrapper(source: str, destination: str) -> None:
    pass

@tool
def walrus_rebind(source: str, destination: str) -> None:
    copy_fn = shutil.copy2
    (copy_fn := wrapper)
    copy_fn(source, destination)

@tool
def import_rebind(source: str, destination: str) -> None:
    copy_fn = shutil.copy2
    import json as copy_fn
    copy_fn(source, destination)
""".lstrip(),
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    assert not any(
        item.kind == "capability" and item.name == "filesystem"
        for item in ir.components
    )
    assert not ir.findings


def test_dynamic_writable_tool_path_but_not_fixed_path_is_reviewed() -> None:
    ir = scan_repository(ROOT / "cases/filesystem_scope")

    filesystem_findings = [finding for finding in ir.findings if finding.rule_id == "AV-FS001"]
    assert len(filesystem_findings) == 1
    assert filesystem_findings[0].ir_path == (
        "agent:writer",
        "tool:write_file",
        "capability:filesystem",
    )
    assert filesystem_findings[0].result_kind == "review"


def test_container_host_boundaries_but_not_safe_compose_are_reviewed() -> None:
    ir = scan_repository(ROOT / "cases/sandbox_boundary")

    findings = [finding for finding in ir.findings if finding.rule_id == "AV-SANDBOX001"]
    assert {finding.message for finding in findings} == {
        "A container mounts the host Docker socket",
        "A container runs in privileged mode",
        "A container shares the host network namespace",
        "A container shares the host process namespace",
        "A container shares the host IPC namespace",
        "A workload automatically mounts a Kubernetes service-account token",
        "A container explicitly allows privilege escalation",
        "A container mounts the host filesystem root",
        "A Kubernetes workload mounts a host path",
    }
    assert len(findings) == 12
    assert ir.config_files_scanned == 4
    assert all(finding.result_kind == "review" for finding in findings)
    host_path = next(
        component
        for component in ir.components
        if component.kind == "sandbox-boundary" and component.name == "host-path-mount"
    )
    assert host_path.attributes["host_path"] == "/srv/agent-workspace"
    assert any(
        component.kind == "sandbox-boundary"
        and component.name == "privileged-container"
        and component.attributes.get("api") == "client.containers.run"
        for component in ir.components
    )


def test_action_trace_only_governs_capabilities_inside_the_span() -> None:
    ir = scan_repository(ROOT / "cases/audit_trace")

    trace = next(
        component
        for component in ir.components
        if component.kind == "control" and component.name == "action-trace"
    )
    assert trace.attributes == {
        "instrumentation": "opentelemetry",
        "durability": "unresolved",
        "scope": "production",
        "tool": "send_email",
    }
    governed_lines = {
        edge.evidence.line
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.target_name == "action-trace"
    }
    assert governed_lines == {11}
    assert any(
        edge.source_kind == "tool"
        and edge.source_name == "send_email"
        and edge.relation == "contains-control"
        for edge in ir.relationships
    )
    assert not any(
        edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.evidence.line == 16
        for edge in ir.relationships
    )
    traced_action = next(
        component
        for component in ir.components
        if component.kind == "capability"
        and component.name == "external-action"
        and component.evidence.line == 11
    )
    _, analysis = component_context(ir, traced_action)
    assert analysis["governing_controls"] == ["action-trace"]
    assert analysis["audit_coverage"] == "instrumented; exporter durability unresolved"


def test_google_adk_bigquery_plugin_proves_durable_attributable_action_audit() -> None:
    ir = scan_repository(ROOT / "cases/python_google_adk_bigquery_audit")

    storage = next(
        component
        for component in ir.components
        if component.kind == "capability" and component.name == "audit-storage"
    )
    assert storage.attributes == {
        "analysis": "python-google-adk-bigquery-action-audit",
        "api": "BigQueryWriteAsyncClient.append_rows",
        "sink": "bigquery-storage-write-api",
        "durability": "durable-remote-database",
        "scope": "production",
    }
    deployed = next(
        component
        for component in ir.components
        if component.kind == "control"
        and component.name == "durable-action-audit"
        and component.evidence.path == "app.py"
    )
    assert deployed.attributes["deployment_state"] == "enabled"
    assert deployed.attributes["event_types"] == [
        "TOOL_STARTING",
        "TOOL_COMPLETED",
        "TOOL_ERROR",
    ]
    assert deployed.attributes["attribution_fields"] == [
        "event_id",
        "agent",
        "user_id",
        "session_id",
        "invocation_id",
        "tool",
    ]
    actions = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "capability"
        and component.name == "external-action"
        and component.evidence.path == "app.py"
    }
    _, audited = component_context(ir, actions[13])
    _, disabled = component_context(ir, actions[18])
    assert audited["governing_controls"] == ["durable-action-audit"]
    assert audited["audit_coverage"] == "durable and attributable; delivery best-effort"
    assert disabled["governing_controls"] == []
    assert disabled["audit_coverage"] == "unresolved"
    setting = next(
        component
        for component in ir.components
        if component.kind == "control-setting" and component.name == "action-audit"
    )
    assert setting.attributes["enabled"] is False
    assert setting.attributes["state"] == "disabled-explicit"
    assert any(
        edge.source_name == "disabled_agent"
        and edge.relation == "configured-by"
        and edge.target_name == "action-audit"
        for edge in ir.relationships
    )
    assert not any(finding.rule_id == "AV-AUDIT001" for finding in ir.findings)


def test_google_adk_audit_control_requires_the_full_framework_path(tmp_path: Path) -> None:
    source = ROOT / "cases/python_google_adk_bigquery_audit"
    mutations = (
        (
            "google/adk/plugins/bigquery_agent_analytics_plugin.py",
            "enabled: bool = True",
            "enabled: bool = False",
        ),
        (
            "google/adk/plugins/bigquery_agent_analytics_plugin.py",
            "await self.write_client.append_rows(row)",
            "print(row)",
        ),
        (
            "google/adk/runners.py",
            "plugins=app.plugins",
            "plugins=[]",
        ),
        (
            "google/adk/flows/llm_flows/functions.py",
            "await invocation_context.plugin_manager.run_after_tool_callback(",
            "await invocation_context.plugin_manager.after_tool_callback(",
        ),
    )
    for index, (relative, before, after) in enumerate(mutations):
        incomplete = tmp_path / str(index)
        shutil.copytree(source, incomplete)
        target = incomplete / relative
        text = target.read_text(encoding="utf-8")
        assert before in text
        target.write_text(text.replace(before, after, 1), encoding="utf-8")

        ir = scan_repository(incomplete)

        assert not any(
            component.name in {"durable-action-audit", "audit-storage", "action-audit"}
            for component in ir.components
        )


def test_google_adk_audit_control_withholds_mutable_or_filtered_compositions(
    tmp_path: Path,
) -> None:
    source = ROOT / "cases/python_google_adk_bigquery_audit"
    mutations = (
        (
            "audit_plugin = BigQueryAgentAnalyticsPlugin(",
            "audit_plugin = BigQueryAgentAnalyticsPlugin(",
            "audit_plugin = object()\n",
        ),
        (
            'project_id="project", dataset_id="audit")',
            (
                'project_id="project", dataset_id="audit", '
                + 'event_allowlist=["TOOL_STARTING"])'
            ),
            "",
        ),
    )
    for index, (before, after, suffix) in enumerate(mutations):
        incomplete = tmp_path / str(index)
        shutil.copytree(source, incomplete)
        target = incomplete / "app.py"
        text = target.read_text(encoding="utf-8")
        assert before in text
        target.write_text(text.replace(before, after, 1) + suffix, encoding="utf-8")

        ir = scan_repository(incomplete)

        assert not any(
            edge.source_kind == "capability"
            and edge.evidence.path == "app.py"
            and edge.evidence.line == 13
            and edge.relation == "governed-by"
            and edge.target_name == "durable-action-audit"
            for edge in ir.relationships
        )


def test_skyvern_taskv3_proves_durable_execution_record_with_actor_gap() -> None:
    ir = scan_repository(ROOT / "cases/python_skyvern_action_history")

    action = next(
        component
        for component in ir.components
        if component.kind == "capability"
        and component.name == "external-action"
        and component.attributes.get("analysis")
        == "python-skyvern-taskv3-action-history"
    )
    path, analysis = component_context(ir, action)
    assert path == (
        "agent:Skyvern Task v3 agent loop",
        "tool:Task v3 recordable action dispatch",
        "capability:external-action",
    )
    assert analysis["governing_controls"] == ["durable-action-record"]
    assert analysis["audit_coverage"] == (
        "durable execution record; actor attribution unresolved; delivery best-effort"
    )
    control = next(
        component
        for component in ir.components
        if component.kind == "control" and component.name == "durable-action-record"
    )
    assert control.attributes["deployment_state"] == "enabled"
    assert control.attributes["scope"] == "production"
    assert control.attributes["actor_attribution"] == (
        "unresolved-created-by-nullable-and-unset"
    )
    assert control.attributes["failure_behavior"] == "persistence-errors-contained"
    storage = next(
        component
        for component in ir.components
        if component.kind == "capability" and component.name == "audit-storage"
    )
    assert storage.attributes == {
        "analysis": "python-skyvern-taskv3-action-history",
        "scope": "production",
        "api": "SQLAlchemy AsyncSession.commit",
        "sink": "sqlalchemy-actions-table",
        "table": "actions",
        "durability": "durable-relational-database",
    }
    audit_findings = [
        finding for finding in ir.findings if finding.rule_id == "AV-AUDIT001"
    ]
    assert len(audit_findings) == 1
    finding = audit_findings[0]
    assert finding.evidence.path == "skyvern/forge/taskv3/loop.py"
    assert finding.evidence.line == 9
    assert finding.severity == "medium"
    assert finding.confidence == "high"
    assert finding.result_kind == "review"
    assert finding.analysis["audit_coverage"] == (
        "durable execution record; actor attribution unresolved; delivery best-effort"
    )
    assert not any(
        candidate.rule_id == "AV-AUDIT001"
        and candidate.evidence.path == "untracked.py"
        for candidate in ir.findings
    )


def test_skyvern_action_record_requires_dispatch_callback_and_commit_path(
    tmp_path: Path,
) -> None:
    source = ROOT / "cases/python_skyvern_action_history"
    mutations = (
        (
            "skyvern/forge/taskv3/loop.py",
            "result = await spec.handler(args)",
            'result = ToolResult(status="unknown")',
        ),
        (
            "skyvern/forge/taskv3/loop.py",
            "await on_action_round(round_actions)",
            "await observe_round(round_actions)",
        ),
        (
            "skyvern/forge/agent.py",
            "on_action_round=_on_action_round",
            "on_action_round=None",
        ),
        (
            "skyvern/forge/agent.py",
            "await app.DATABASE.workflow_params.create_action(action=action)",
            "await app.DATABASE.workflow_params.preview_action(action=action)",
        ),
        (
            "skyvern/forge/sdk/db/repositories/workflow_parameters.py",
            "await session.commit()",
            "await session.flush()",
        ),
        (
            "skyvern/forge/sdk/db/models.py",
            "created_by = Column(String, nullable=True)",
            "created_by = Column(String, nullable=False)",
        ),
    )
    for index, (relative, before, after) in enumerate(mutations):
        incomplete = tmp_path / str(index)
        shutil.copytree(source, incomplete)
        target = incomplete / relative
        text = target.read_text(encoding="utf-8")
        assert before in text
        target.write_text(text.replace(before, after, 1), encoding="utf-8")

        ir = scan_repository(incomplete)

        assert not any(
            component.attributes.get("analysis")
            == "python-skyvern-taskv3-action-history"
            for component in ir.components
        )


def test_delegation_expands_transitive_capability_path() -> None:
    ir = scan_repository(ROOT / "cases/delegation")

    assert ir.findings[0].ir_path == (
        "agent:coordinator",
        "agent:worker",
        "tool:run_command",
        "capability:shell-execution",
    )
    assert ir.findings[0].analysis["direct_agents"] == ["worker"]
    assert ir.findings[0].analysis["reachable_agents"] == ["coordinator", "worker"]


def test_same_named_cross_file_edges_do_not_leak_into_context() -> None:
    ir = scan_repository(ROOT / "cases/symbol_collision")

    finding = next(finding for finding in ir.findings if finding.rule_id == "AV-EXEC001")
    assert finding.ir_path == (
        "agent:operator",
        "tool:run_command",
        "capability:shell-execution",
    )
    assert finding.analysis["direct_agents"] == ["operator"]
    assert finding.analysis["approval_coverage"] == "unresolved"
    assert finding.analysis["governing_controls"] == []
    tool_symbols = {
        component.evidence.path: component.symbol_id
        for component in ir.components
        if component.kind == "tool" and component.name == "run_command"
    }
    assert tool_symbols == {
        "approved.py": "py:approved.py#tool:run_command",
        "dangerous.py": "py:dangerous.py#tool:run_command",
    }
    operator_edge = next(
        edge
        for edge in ir.relationships
        if edge.source_name == "operator" and edge.relation == "uses"
    )
    approval_edge = next(edge for edge in ir.relationships if edge.relation == "governed-by")
    assert operator_edge.target_id == tool_symbols["dangerous.py"]
    assert approval_edge.source_id == tool_symbols["approved.py"]


def test_relative_python_tool_import_resolves_only_existing_sibling_module() -> None:
    ir = scan_repository(ROOT / "cases/imported_relative_tool")

    operator_edge = next(
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.source_name == "operator"
        and edge.target_name == "run_command"
    )
    assert operator_edge.attributes == {"target_path": "pkg/tools.py"}
    assert operator_edge.target_id == "py:pkg/tools.py#tool:run_command"
    unresolved_edge = next(
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.source_name == "unresolved"
    )
    assert unresolved_edge.attributes == {}
    assert unresolved_edge.target_id is None


def test_contextual_absolute_class_tool_import_requires_one_path_and_exact_export() -> None:
    ir = scan_repository(ROOT / "cases/python_contextual_class_tool")

    positive = next(
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.evidence.path == "project_a/agent.py"
    )
    assert positive.target_name == "WebTools.browse"
    assert positive.attributes == {
        "target_path": "project_a/tools/browser.py",
        "target_identity": "contextual-absolute-import-single-export",
    }
    assert positive.target_id == (
        "py:project_a/tools/browser.py#tool:BrowserTools.browse"
    )
    assert any(
        finding.rule_id == "AV-NET001"
        and finding.ir_path
        == (
            "agent:Agent",
            "tool:browse",
            "capability:network",
        )
        for finding in ir.findings
    )

    unresolved = {
        edge.evidence.path: edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.evidence.path != "project_a/agent.py"
    }
    assert set(unresolved) == {
        "ambiguous/nested/agent.py",
        "project_a/missing.py",
        "project_a/reimported.py",
        "project_a/shadowed.py",
    }
    assert all(edge.attributes == {} for edge in unresolved.values())
    assert all(edge.target_id is None for edge in unresolved.values())


def test_local_import_resolves_cross_file_agent_tool_path() -> None:
    ir = scan_repository(ROOT / "cases/imported_tool")

    finding = next(finding for finding in ir.findings if finding.rule_id == "AV-EXEC001")
    assert finding.ir_path == (
        "agent:operator",
        "tool:run_command",
        "capability:shell-execution",
    )
    assert finding.analysis["direct_agents"] == ["operator"]
    assert finding.analysis["approval_coverage"] == "present"
    agent_edge = next(
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_name == "run_command"
    )
    assert agent_edge.attributes["target_path"] == "tools.py"
    tool = next(
        component
        for component in ir.components
        if component.kind == "tool" and component.evidence.path == "tools.py"
    )
    assert agent_edge.target_id == tool.symbol_id == "py:tools.py#tool:run_command"


def test_python_local_bindings_do_not_inherit_module_import_identity() -> None:
    ir = scan_repository(ROOT / "cases/python_import_shadowing")
    edges = {
        edge.evidence.line: edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_name == "tool"
    }

    assert edges[4].attributes == {"target_path": "pkg/__init__.py"}
    assert edges[4].target_id == "py:pkg/__init__.py#tool:tool"
    assert edges[8].attributes == {}
    assert edges[8].target_id is None
    assert edges[13].attributes == {}
    assert edges[13].target_id is None


def test_python_repeated_bindings_require_same_block_dominance() -> None:
    ir = scan_repository(ROOT / "cases/python_block_dominance")
    edges = {
        edge.evidence.line: edge
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.source_name == "Crew"
        and edge.target_name == "agent"
    }

    assert edges[10].attributes == {"target_identity": "block-dominating-definition"}
    assert edges[10].target_id == "py:app.py#agent:agent@9"
    assert edges[16].attributes == {"target_identity": "block-dominating-definition"}
    assert edges[16].target_id == "py:app.py#agent:agent@15"
    assert edges[22].attributes == {"target_identity": "ambiguous-repeated-binding"}
    assert edges[22].target_id is None
    assert edges[29].attributes == {"target_identity": "ambiguous-repeated-binding"}
    assert edges[29].target_id is None
    assert edges[35].attributes == {"target_identity": "block-dominating-definition"}
    assert edges[35].target_id == "py:app.py#agent:agent@34"
    assert edges[42].attributes == {"target_identity": "block-dominating-definition"}
    assert edges[42].target_id == "py:app.py#agent:agent@41"


def test_python_direct_callable_tools_require_same_block_definition() -> None:
    ir = scan_repository(ROOT / "cases/python_direct_callable_tool")
    tools = {component.name: component for component in ir.components if component.kind == "tool"}
    assert set(tools) == {"branch_tool", "run_command", "unique_tool"}
    assert tools["run_command"].symbol_id == "py:app.py#tool:run_command"
    assert tools["run_command"].attributes == {
        "decorators": [],
        "needs_approval": False,
        "registration": "agent-tool-reference",
        "registration_path": "app.py",
        "registration_line": 9,
        "resolution": "same-block-single-definition",
    }
    assert tools["branch_tool"].symbol_id == "py:app.py#tool:branch_tool"
    assert tools["branch_tool"].attributes["registration_line"] == 16
    assert tools["unique_tool"].symbol_id == "py:app.py#tool:unique_tool"
    assert tools["unique_tool"].attributes["registration_line"] == 49

    edges = {
        edge.evidence.line: edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_kind == "tool"
    }
    assert edges[9].target_id == "py:app.py#tool:run_command"
    assert edges[9].attributes == {}
    assert edges[16].target_id == "py:app.py#tool:branch_tool"
    assert edges[16].attributes == {}
    assert edges[24].target_id is None
    assert edges[31].target_id is None
    assert edges[35].target_id is None
    assert edges[39].target_id is None
    assert edges[49].target_id == "py:app.py#tool:unique_tool"
    assert edges[53].target_id is None

    shell = next(
        component
        for component in ir.components
        if component.kind == "capability" and component.name == "shell-execution"
    )
    assert shell.evidence.line == 8
    shell_edge = next(
        edge
        for edge in ir.relationships
        if edge.source_id == "py:app.py#tool:run_command"
        and edge.target_name == "shell-execution"
    )
    assert shell_edge.evidence.line == 8
    finding = next(
        finding
        for finding in ir.findings
        if finding.rule_id == "AV-EXEC001" and finding.evidence.line == 8
    )
    assert finding.ir_path[:2] == ("agent:Agent", "tool:run_command")


def test_python_function_tool_wrappers_require_import_and_same_block_proof() -> None:
    ir = scan_repository(ROOT / "cases/python_function_tool_wrapper")
    tools = {
        component.symbol_id: component
        for component in ir.components
        if component.kind == "tool"
        and component.attributes.get("registration") == "function-tool-wrapper"
    }
    assert set(tools) == {
        "py:app.py#tool:wrapped@12",
        "py:app.py#tool:wrapped@20",
    }
    approved = tools["py:app.py#tool:wrapped@12"]
    assert approved.name == "wrapped"
    assert approved.evidence.line == 12
    assert approved.attributes == {
        "decorators": [],
        "needs_approval": True,
        "registration": "function-tool-wrapper",
        "registration_path": "app.py",
        "registration_line": 13,
        "wrapper_factory": "agents.function_tool",
        "wrapper_line": 12,
        "wrapped_function": "run_command",
        "resolution": "same-block-single-definition",
    }

    edges = {
        edge.evidence.line: edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_kind == "tool"
    }
    assert edges[13].target_id == "py:app.py#tool:wrapped@12"
    assert edges[21].target_id == "py:app.py#tool:wrapped@20"
    for line in (29, 37, 46, 55, 64, 69):
        assert edges[line].target_id is None
    multiple_edges = [
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.target_kind == "tool"
        and edge.evidence.line == 78
    ]
    assert len(multiple_edges) == 2
    assert all(edge.target_id is None for edge in multiple_edges)

    capability = next(
        edge
        for edge in ir.relationships
        if edge.source_id == "py:app.py#tool:wrapped@12"
        and edge.target_name == "shell-execution"
    )
    assert capability.evidence.line == 10
    approval = next(
        edge
        for edge in ir.relationships
        if edge.source_id == "py:app.py#tool:wrapped@12"
        and edge.target_name == "human-approval"
    )
    assert approval.evidence.line == 12
    finding = next(
        finding
        for finding in ir.findings
        if finding.rule_id == "AV-EXEC001" and finding.evidence.line == 10
    )
    assert finding.ir_path[:2] == ("agent:Agent", "tool:wrapped")
    assert finding.analysis["approval_coverage"] == "present"


def test_literal_tool_bindings_require_role_and_exact_local_identity() -> None:
    ir = scan_repository(ROOT / "cases/python_literal_tool_bindings")
    edges = {
        (edge.source_name, edge.target_name): edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_kind == "tool"
    }

    assert edges[("module-bindings", "module_tools")].target_id == (
        "py:positive.py#tool:module_tools"
    )
    assert edges[("module-bindings", "module_callable")].target_id == (
        "py:positive.py#tool:module_callable"
    )
    assert edges[("local-binding", "local_tools")].target_id == (
        "py:positive.py#tool:local_tools"
    )
    assert edges[("inline-binding", "InlineTools@31")].target_id == (
        "py:positive.py#tool:InlineTools@31"
    )
    assert edges[("inline-binding", "InlineTools@31")].attributes == {
        "target_identity": "literal-tools-list-inline-constructor"
    }
    assert edges[("inline-binding", "LocalToolkit@31")].target_id == (
        "py:positive.py#tool:LocalToolkit@31"
    )
    assert edges[("context-binding", "context_tools")].target_id == (
        "py:positive.py#tool:context_tools"
    )
    assert edges[("context-binding", "context_tools")].attributes == {
        "target_identity": "literal-tools-list-context-manager"
    }

    unresolved_agents = {
        "reassigned-binding",
        "cross-branch-binding",
        "parameter-binding",
        "unproven-factory",
        "unproven-builtin",
        "ambiguous-constructor",
        "shadowed-constructor",
        "reassigned-context",
        "nested-context",
        "callable-rebound",
    }
    assert all(
        edges[(agent_name, "rebound_callable" if agent_name == "callable-rebound" else "tools")]
        .target_id
        is None
        for agent_name in unresolved_agents
    )

    components = {
        component.symbol_id: component
        for component in ir.components
        if component.kind == "tool"
    }
    assert components["py:positive.py#tool:module_tools"].attributes == {
        "binding": "literal-tools-list-constructor",
        "constructor": "ImportedTools",
        "registration": "agent-tool-reference",
        "registration_line": 17,
        "resolution": "module-single-definition",
        "scope": "production",
    }
    assert components["py:positive.py#tool:module_callable"].attributes[
        "resolution"
    ] == "module-single-definition"


def test_python_agent_helper_returns_require_exact_same_class_flow() -> None:
    ir = scan_repository(ROOT / "cases/python_agent_helper_return")
    edges = {
        edge.evidence.line: edge
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.source_name == "Crew"
        and edge.target_kind == "agent"
    }

    assert edges[11].target_id == "py:app.py#agent:Agent@7"
    assert edges[11].attributes == {
        "target_identity": "same-class-helper-return"
    }
    assert edges[20].target_id == "py:app.py#agent:agent@14"
    assert edges[20].attributes == {
        "target_identity": "same-class-helper-return"
    }
    for line in (29, 38, 46, 51, 56, 67, 82):
        assert edges[line].target_id is None
        assert edges[line].attributes == {
            "target_identity": "ambiguous-repeated-binding"
        }


def test_imported_agent_factory_requires_exact_class_and_same_block_flow() -> None:
    ir = scan_repository(ROOT / "cases/python_imported_agent_factory")
    edges = {
        (edge.evidence.path, edge.evidence.line): edge
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.source_name == "Crew"
        and edge.target_kind == "agent"
    }

    positive = edges[("project_a/main.py", 8)]
    assert positive.target_id == (
        "py:project_a/factory.py#agent:imported-worker@6"
    )
    assert positive.attributes == {
        "target_identity": "contextual-imported-class-factory-return",
        "target_path": "project_a/factory.py",
    }

    unresolved = {
        ("ambiguous/nested/main.py", 8),
        ("project_a/main.py", 12),
        ("project_a/main.py", 19),
        ("project_a/main.py", 25),
        ("project_a/main.py", 32),
        ("project_a/missing.py", 8),
        ("project_a/reimported.py", 9),
        ("project_a/unsupported.py", 14),
        ("project_a/unsupported.py", 18),
        ("project_a/unsupported.py", 22),
        ("project_a/unsupported.py", 26),
        ("project_a/unsupported.py", 30),
    }
    assert unresolved <= edges.keys()
    assert all(edges[key].target_id is None for key in unresolved)
    assert all(edges[key].attributes == {} for key in unresolved)


def test_python_typed_tool_parameters_require_callsite_constructor_consensus() -> None:
    ir = scan_repository(ROOT / "cases/python_typed_tool_parameter")
    edges = {
        edge.evidence.line: edge
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.relation == "uses"
        and edge.target_kind == "tool"
        and edge.target_name == "tool"
    }

    assert edges[5].target_id == "py:app.py#tool:tool@4"
    assert edges[5].attributes == {
        "target_identity": "typed-parameter-callsite-consensus"
    }
    for line in (23, 33, 42, 50, 62, 72, 81, 90, 99, 112, 121, 131, 145):
        assert edges[line].target_id is None
        assert edges[line].attributes == {
            "target_identity": "ambiguous-repeated-binding"
        }

    parameter = next(
        component
        for component in ir.components
        if component.symbol_id == "py:app.py#tool:tool@4"
    )
    assert parameter.name == "ApplyPatchTool parameter tool@4"
    assert parameter.evidence.line == 4
    assert parameter.attributes == {
        "binding": "typed-parameter",
        "constructor": "ApplyPatchTool",
        "callsite_proof": "same-module-constructor-consensus",
        "verified_call_sites": 3,
        "callsite_target_ids": [
            "py:app.py#tool:ApplyPatchTool@19",
            "py:app.py#tool:patch",
            "py:app.py#tool:tool@9",
        ],
        "scope": "production",
    }
    inline_edge = next(
        edge
        for edge in ir.relationships
        if edge.evidence.path == "inline_only.py"
        and edge.evidence.line == 5
        and edge.source_kind == "agent"
        and edge.target_name == "patch"
    )
    assert inline_edge.target_id == "py:inline_only.py#tool:patch@4"
    assert inline_edge.attributes == {
        "target_identity": "typed-parameter-callsite-consensus"
    }


def test_relative_typescript_import_resolves_cross_file_tool_path() -> None:
    ir = scan_repository(ROOT / "cases/imported_ts_tool")

    finding = next(finding for finding in ir.findings if finding.rule_id == "AV-EXEC001")
    assert finding.ir_path == (
        "agent:operator",
        "tool:runCommand",
        "capability:shell-execution",
    )
    assert finding.analysis["direct_agents"] == ["operator"]
    assert finding.analysis["approval_coverage"] == "present"
    agent_edge = next(
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_name == "importedCommand"
    )
    assert agent_edge.attributes["target_path"] == "tools.ts"
    assert agent_edge.attributes["target_name"] == "runCommand"
    tool = next(
        component
        for component in ir.components
        if component.kind == "tool" and component.evidence.path == "tools.ts"
    )
    assert agent_edge.target_id == tool.symbol_id == "ts:tools.ts#tool:runCommand"


def test_typescript_import_outside_root_or_ambiguous_stays_unresolved(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (tmp_path / "external.ts").write_text("export const externalTool = {};\n", encoding="utf-8")
    (project / "tools.ts").write_text("export const localTool = {};\n", encoding="utf-8")
    (project / "tools.js").write_text("export const localTool = {};\n", encoding="utf-8")
    (project / "agent.ts").write_text(
        """import { Agent } from "@openai/agents";
import { externalTool } from "../external";
import { localTool } from "./tools";
const agent = new Agent({ name: "operator", tools: [externalTool, localTool] });
""",
        encoding="utf-8",
    )

    ir = scan_repository(project)

    agent_edges = [edge for edge in ir.relationships if edge.source_kind == "agent"]
    assert len(agent_edges) == 2
    assert all("target_path" not in edge.attributes for edge in agent_edges)


def test_test_scope_findings_are_opt_in() -> None:
    default_ir = scan_repository(ROOT / "cases/test_scope")
    complete_ir = scan_repository(ROOT / "cases/test_scope", include_tests=True)

    assert not default_ir.findings
    assert {finding.rule_id for finding in complete_ir.findings} == {
        "AV-APPROVAL001",
        "AV-EXEC001",
    }


def test_regex_exec_is_not_code_or_shell_execution(tmp_path: Path) -> None:
    (tmp_path / "parser.ts").write_text(
        "const match = pattern.exec(line);\nconst score = engine.eval(line);\n",
        encoding="utf-8",
    )
    (tmp_path / "parser.py").write_text("match = pattern.exec(line)\n", encoding="utf-8")

    ir = scan_repository(tmp_path)

    assert not [item for item in ir.components if item.kind == "capability"]
    assert not ir.findings


def test_typescript_literal_shell_commands_are_inventory_only(tmp_path: Path) -> None:
    (tmp_path / "commands.ts").write_text(
        """import { execSync } from \"node:child_process\";
execSync("npm install");
execSync(`npm run build`);
execSync(`npm run ${target}`);
execSync("npm " + command);
execSync(command);
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    shell = [item for item in ir.components if item.name == "shell-execution"]
    assert [item.attributes["dynamic_command"] for item in shell] == [
        False,
        False,
        True,
        True,
        True,
    ]
    assert [finding.evidence.line for finding in ir.findings] == [4, 5, 6]


def test_inline_suppression_is_rule_scoped_and_requires_reason(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """import subprocess

# agentverify: ignore AV-EXEC001 -- reviewed wrapper; input is allowlisted upstream
subprocess.run(command, shell=True)
# agentverify: ignore AV-EXEC002 -- wrong rule
subprocess.run(other_command, shell=True)
# agentverify: ignore AV-EXEC001
subprocess.run(third_command, shell=True)
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    assert ir.suppressed_findings == 1
    assert [finding.evidence.line for finding in ir.findings] == [6, 8]
    assert len(ir.suppressions) == 1
    assert ir.suppressions[0].rule_id == "AV-EXEC001"
    assert ir.suppressions[0].directive.line == 3
    assert ir.suppressions[0].reason == "reviewed wrapper; input is allowlisted upstream"
    report = json.loads(render_json(ir))
    assert report["suppressions"][0]["finding"]["line"] == 4
    assert ir.suppressions[0].expires_on is None
    assert ir.suppressions[0].status == "active"
    assert "Inline suppression directives:" in render_text(ir)


def test_suppression_expiry_restores_expired_or_noncompliant_findings(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """import subprocess
# agentverify: ignore AV-EXEC001 until 2025-01-01 -- expired exception
subprocess.run(expired, shell=True)
# agentverify: ignore AV-EXEC001 until 2027-01-01 -- active exception
subprocess.run(active, shell=True)
# agentverify: ignore AV-EXEC001 -- missing expiry
subprocess.run(no_expiry, shell=True)
# agentverify: ignore AV-EXEC001 until tomorrow -- malformed expiry
subprocess.run(invalid, shell=True)
""",
        encoding="utf-8",
    )

    ir = scan_repository(
        tmp_path,
        require_suppression_expiry=True,
        current_date=date(2026, 8, 21),
    )

    assert [finding.evidence.line for finding in ir.findings] == [3, 7, 9]
    assert ir.suppressed_findings == 1
    assert [suppression.status for suppression in ir.suppressions] == [
        "expired",
        "active",
        "missing-expiry",
        "invalid-expiry",
    ]


def test_typescript_and_compose_inline_suppressions(tmp_path: Path) -> None:
    (tmp_path / "agent.ts").write_text(
        """import { exec } from "node:child_process";
// agentverify: ignore AV-EXEC001 -- command policy is enforced by the caller
exec(command);
""",
        encoding="utf-8",
    )
    (tmp_path / "docker-compose.yml").write_text(
        """services:
  agent:
    # agentverify: ignore AV-SANDBOX001 -- dedicated isolated build host
    privileged: true
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    assert not ir.findings
    assert ir.suppressed_findings == 2
    assert {suppression.rule_id for suppression in ir.suppressions} == {
        "AV-EXEC001",
        "AV-SANDBOX001",
    }


def test_oversized_source_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "large.py").write_text("#" * 2_000_001, encoding="utf-8")

    ir = scan_repository(tmp_path)

    assert ir.files_scanned == 0
    assert ir.errors == ["large.py: skipped file larger than 2000000 bytes"]


def test_utf8_bom_is_accepted(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_bytes(b"\xef\xbb\xbffrom agents import Agent\n")

    ir = scan_repository(tmp_path)

    assert not ir.errors
    assert ("framework", "OpenAI Agents SDK") in {(item.kind, item.name) for item in ir.components}


def test_typescript_and_mcp_config() -> None:
    ir = scan_repository(ROOT / "cases/typescript_mcp")

    assert {(item.kind, item.name) for item in ir.components} >= {
        ("framework", "OpenAI Agents SDK"),
        ("protocol", "MCP"),
        ("mcp-server", "local-shell"),
        ("agent", "operator"),
        ("tool", "runCommand"),
        ("capability", "shell-execution"),
    }
    assert {
        (item.source_kind, item.source_name, item.relation, item.target_kind, item.target_name)
        for item in ir.relationships
    } >= {
        ("agent", "operator", "uses", "tool", "runCommand"),
        ("tool", "runCommand", "uses", "capability", "shell-execution"),
    }
    assert any(finding.rule_id == "AV-APPROVAL001" for finding in ir.findings)
    report = json.loads(render_json(ir))
    assert report["files_scanned"] == 1
    assert {finding["rule_id"] for finding in report["findings"]} == {
        "AV-APPROVAL001",
        "AV-EXEC001",
        "AV-MCP002",
    }
    serialized = json.dumps(report)
    assert "fixture-secret-value" not in serialized
    servers = {item["name"]: item for item in report["components"] if item["kind"] == "mcp-server"}
    assert servers["local-shell"]["attributes"]["environment_names"] == ["SERVICE_API_KEY"]
    assert servers["remote"]["attributes"]["url"] == "https://[REDACTED]@example.invalid/mcp"


def test_cli_fail_on_high(capsys) -> None:
    exit_code = main(["scan", str(ROOT / "cases/python_dangerous"), "--fail-on", "high"])
    assert exit_code == 1
    assert "AV-EXEC001" in capsys.readouterr().out


def test_sarif_contains_location_fingerprint_and_ir_context() -> None:
    ir = scan_repository(ROOT / "cases/python_dangerous")

    sarif = json.loads(render_sarif(ir))
    result = sarif["runs"][0]["results"][0]
    assert sarif["version"] == "2.1.0"
    assert "informationUri" not in sarif["runs"][0]["tool"]["driver"]
    assert sarif["runs"][0]["properties"] == {
        "scanScope": "repository",
        "pathFilters": [],
        "baselineSummary": {},
        "policySummary": {},
    }
    assert result["ruleId"] == "AV-EXEC001"
    assert result["locations"][0]["physicalLocation"]["region"]["startLine"] == 13
    assert result["partialFingerprints"]["agentverify/v1"]
    assert result["properties"]["irPath"][0] == "agent:operator"


def test_native_ai_bom_is_deterministic_evidence_first_and_schema_shaped() -> None:
    ir = scan_repository(ROOT / "cases/python_dangerous")

    rendered = render_bom(ir)
    assert rendered == render_bom(ir)
    bom = json.loads(rendered)
    schema = json.loads(
        (ROOT / "src/agentverify/schemas/agentverify-ai-bom-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(bom)
    assert set(bom) == set(schema["required"])
    assert bom["bom_format"] == "AgentVerify AI BOM"
    assert bom["spec_version"] == "1.2"
    assert bom["metadata"]["root"] == "."
    assert bom["metadata"]["scan_scope"] == "repository"
    assert len({asset["id"] for asset in bom["assets"]}) == len(bom["assets"])
    shell = next(
        asset
        for asset in bom["assets"]
        if asset["kind"] == "capability" and asset["name"] == "shell-execution"
    )
    assert shell["evidence"] == {
        "path": "agent.py",
        "line": 13,
        "excerpt": "return subprocess.run(command, shell=True, capture_output=True, text=True).stdout",
    }
    assert bom["governance"]["risk_summary"] == {
        "by_result_kind": {"finding": 1},
        "by_rule": {"AV-EXEC001": 1},
        "by_severity": {"high": 1},
    }
    assert bom["risks"][0]["ir_path"][-1] == "capability:shell-execution"


def test_native_ai_bom_does_not_hide_ambiguous_display_names() -> None:
    bom = json.loads(render_bom(scan_repository(ROOT / "cases/symbol_collision")))

    assert len({asset["id"] for asset in bom["assets"]}) == len(bom["assets"])
    assert len({edge["id"] for edge in bom["relationships"]}) == len(bom["relationships"])
    run_command_endpoints = [
        endpoint
        for relationship in bom["relationships"]
        for endpoint in (relationship["source"], relationship["target"])
        if endpoint["kind"] == "tool" and endpoint["name"] == "run_command"
    ]
    assert run_command_endpoints
    resolutions = [endpoint["resolution"] for endpoint in run_command_endpoints]
    assert resolutions.count("symbol-id") == 3
    assert resolutions.count("ambiguous") == 1
    ambiguous = next(
        endpoint for endpoint in run_command_endpoints if endpoint["resolution"] == "ambiguous"
    )
    assert len(ambiguous["candidate_asset_ids"]) == 2


def test_native_ai_bom_resolves_relationship_endpoints_by_exact_evidence() -> None:
    bom = json.loads(render_bom(scan_repository(ROOT / "cases/mcp_forwarder")))

    registry_edge = next(
        relationship
        for relationship in bom["relationships"]
        if relationship["evidence"]["line"] == 36
        and relationship["target"]["name"] == "tool-registry"
    )
    assert registry_edge["source"]["resolution"] == "evidence-location"
    assert registry_edge["target"]["resolution"] == "evidence-location"
    assert (
        registry_edge["source"]["resolution_path"],
        registry_edge["source"]["resolution_line"],
    ) == ("proxy.py", 36)
    assert (
        registry_edge["target"]["resolution_path"],
        registry_edge["target"]["resolution_line"],
    ) == ("proxy.py", 35)
    assert registry_edge["source"]["asset_id"] != registry_edge["target"]["asset_id"]


def test_native_ai_bom_does_not_embed_checkout_path(tmp_path: Path) -> None:
    source = (ROOT / "examples/safe_agent/agent.py").read_text(encoding="utf-8")
    outputs = []
    for directory_name in ("checkout-one", "checkout-two"):
        checkout = tmp_path / directory_name
        checkout.mkdir()
        (checkout / "agent.py").write_text(source, encoding="utf-8")
        outputs.append(render_bom(scan_repository(checkout)))

    assert outputs[0] == outputs[1]
    assert str(tmp_path) not in outputs[0]


def test_policy_decision_evidence_is_retained_by_all_reporters() -> None:
    ir = scan_repository(ROOT / "cases/python_dangerous")
    policy = normalize_policy(
        {
            "schema_version": 1,
            "name": "release",
            "gates": [{"id": "high", "max_count": 0}],
        }
    )
    assert evaluate_policy(ir, policy, source="policy.json", digest="a" * 64) is False

    json_report = json.loads(render_json(ir))
    bom = json.loads(render_bom(ir))
    sarif = json.loads(render_sarif(ir))
    text_report = render_text(ir)
    assert json_report["policy_summary"]["gates"][0]["matched_count"] == 1
    bom_schema = json.loads(
        (ROOT / "src/agentverify/schemas/agentverify-ai-bom-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(bom_schema).validate(bom)
    assert bom["metadata"]["policy_summary"] == json_report["policy_summary"]
    assert sarif["runs"][0]["properties"]["policySummary"] == json_report["policy_summary"]
    assert "Policy: release [failed; 1 gates]" in text_report

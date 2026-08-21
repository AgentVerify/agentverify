from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator

from agentverify.analysis import component_context
from agentverify.cli import main
from agentverify.policy import evaluate_policy, normalize_policy
from agentverify.report import render_bom, render_json, render_sarif, render_text
from agentverify.scanner import scan_repository

ROOT = Path(__file__).resolve().parents[1]


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
    assert all(
        edge.attributes["target_identity"] == "lexical-single-definition"
        for edge in edges
    )

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
    approval_edges = [
        edge for edge in ir.relationships if edge.relation == "governed-by"
    ]
    assert {component.symbol_id for component in tools} == {
        "py:tools.py#tool:approval_tool@5",
        "py:tools.py#tool:approval_tool@11",
    }
    assert {edge.source_id for edge in approval_edges} == {
        component.symbol_id for component in tools
    }
    bom = json.loads(render_bom(ir))
    assert all(
        relationship["source"]["resolution"] == "symbol-id"
        for relationship in bom["relationships"]
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
    assert len(forwarding) == 6
    assert [finding.rule_id for finding in ir.findings] == [
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
        if item.kind == "capability" and item.name == "network"
    }
    assert network[7]["dynamic_origin"] is True
    assert network[12]["dynamic_origin"] is False
    assert network[17]["dynamic_origin"] is False
    assert [(finding.rule_id, finding.evidence.line) for finding in ir.findings] == [
        ("AV-NET001", 7)
    ]
    finding = ir.findings[0]
    assert finding.result_kind == "review"
    assert finding.ir_path == (
        "agent:networker",
        "tool:fetch_url",
        "capability:network",
    )


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
    assert all(
        edge.attributes["target_identity"] == "ambiguous-repeated-binding"
        for edge in edges
    )
    bom = json.loads(render_bom(ir))
    assert all(
        relationship["source"]["resolution"] == "symbol-id"
        for relationship in bom["relationships"]
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
    assert bom["spec_version"] == "1.1"
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

from __future__ import annotations

import json
from pathlib import Path

from agentverify.analysis import component_context
from agentverify.cli import main
from agentverify.report import render_json, render_sarif, render_text
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
    assert len(forwarding) == 2
    assert [finding.rule_id for finding in ir.findings] == ["AV-MCP002"]
    assert ir.findings[0].result_kind == "review"
    guarded = next(item for item in forwarding if item.attributes["allowlist_guard"])
    assert guarded.evidence.line == 18
    assert any(
        item.source_kind == "capability"
        and item.relation == "governed-by"
        and item.target_name == "tool-allowlist"
        for item in ir.relationships
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


def test_typescript_dynamic_eval_is_linked_and_reported() -> None:
    ir = scan_repository(ROOT / "cases/typescript_eval")

    assert [finding.rule_id for finding in ir.findings] == ["AV-EXEC002"]
    assert ir.findings[0].ir_path == (
        "agent:evaluator",
        "tool:evaluate",
        "capability:code-execution",
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
    unresolved_edge = next(
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.source_name == "unresolved"
    )
    assert unresolved_edge.attributes == {}


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
    assert "Inline suppressions:" in render_text(ir)


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
    assert sarif["runs"][0]["properties"] == {
        "scanScope": "repository",
        "pathFilters": [],
        "baselineSummary": {},
    }
    assert result["ruleId"] == "AV-EXEC001"
    assert result["locations"][0]["physicalLocation"]["region"]["startLine"] == 13
    assert result["partialFingerprints"]["agentverify/v1"]
    assert result["properties"]["irPath"][0] == "agent:operator"

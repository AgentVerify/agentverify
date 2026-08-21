from __future__ import annotations

import json
from pathlib import Path

from agentverify.cli import main
from agentverify.report import render_json, render_sarif
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
        "A container mounts the host filesystem root",
    }
    assert ir.config_files_scanned == 2
    assert all(finding.result_kind == "review" for finding in findings)


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
    assert result["ruleId"] == "AV-EXEC001"
    assert result["locations"][0]["physicalLocation"]["region"]["startLine"] == 13
    assert result["partialFingerprints"]["agentverify/v1"]
    assert result["properties"]["irPath"][0] == "agent:operator"

from __future__ import annotations

from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agentverify import cli
from agentverify.report import render_bom, render_json, render_sarif
from agentverify.rules import RULE_CATALOG
from agentverify.scanner import scan_repository

ROOT = Path(__file__).resolve().parents[1]


def test_cli_handles_closed_output_pipe(monkeypatch: pytest.MonkeyPatch) -> None:
    def closed_pipe(*args: object, **kwargs: object) -> None:
        raise BrokenPipeError

    monkeypatch.setattr("builtins.print", closed_pipe)
    assert cli.main(["scan", str(ROOT / "examples/safe_agent")]) == 0


def test_cli_writes_report_to_output_file(tmp_path: Path, capsys) -> None:
    output = tmp_path / "agentverify.json"

    assert (
        cli.main(
            [
                "scan",
                str(ROOT / "examples/safe_agent"),
                "--format",
                "json",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    payload = __import__("json").loads(output.read_text(encoding="utf-8"))
    assert payload["report_format"] == "AgentVerify JSON Report"
    assert payload["schema_version"] == 1
    assert payload["files_scanned"] == 1


def test_cli_output_preserves_threshold_exit_and_short_alias(tmp_path: Path, capsys) -> None:
    output = tmp_path / "agentverify.sarif"

    assert (
        cli.main(
            [
                "scan",
                str(ROOT / "cases/python_dangerous"),
                "--format",
                "sarif",
                "-o",
                str(output),
                "--fail-on",
                "high",
            ]
        )
        == 1
    )
    assert capsys.readouterr().out == ""
    payload = __import__("json").loads(output.read_text(encoding="utf-8"))
    assert [result["ruleId"] for result in payload["runs"][0]["results"]] == ["AV-EXEC001"]


def test_cli_summary_format_is_compact_and_preserves_threshold_exit(capsys) -> None:
    assert (
        cli.main(
            [
                "scan",
                str(ROOT / "cases/python_dangerous"),
                "--format",
                "summary",
                "--fail-on",
                "high",
            ]
        )
        == 1
    )

    output = capsys.readouterr().out
    assert output.startswith("AgentVerify Summary\n")
    assert "Findings: 1\n" in output
    assert "Components:" in output
    assert "Relationships:" in output
    assert "severity high: 1" in output
    assert "kind finding: 1" in output
    assert "AV-EXEC001: 1 [finding; high; confidence high]" in output
    assert "Top findings:\n  AV-EXEC001 high/finding at agent.py:13" in output
    assert "AI Components:" not in output
    assert "Risk Findings:" not in output


def test_cli_summary_includes_baseline_and_policy_status(tmp_path: Path, capsys) -> None:
    target = ROOT / "cases/python_dangerous"
    baseline = tmp_path / "baseline.json"
    baseline.write_text(render_json(scan_repository(target)), encoding="utf-8")
    policy = tmp_path / "strict.json"
    policy.write_text(
        '{"schema_version":1,"gates":[{"id":"new-high","max_count":0}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "scan",
                str(target),
                "--baseline",
                str(baseline),
                "--policy",
                str(policy),
                "--format",
                "summary",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert "Baseline: 0 new, 1 unchanged, 0 no longer reported" in output
    assert "Policy: unnamed [passed; 1 gates]" in output
    assert "  new-high: 0 matched / 0 allowed [passed]" in output
    assert "No findings" in output


def test_cli_output_preserves_policy_exit(tmp_path: Path, capsys) -> None:
    policy = tmp_path / "strict.json"
    policy.write_text(
        '{"schema_version":1,"gates":[{"id":"no-high","max_count":0}]}',
        encoding="utf-8",
    )
    output = tmp_path / "agentverify.json"

    assert (
        cli.main(
            [
                "scan",
                str(ROOT / "cases/python_dangerous"),
                "--format",
                "json",
                "--output",
                str(output),
                "--policy",
                str(policy),
            ]
        )
        == 1
    )
    assert capsys.readouterr().out == ""
    payload = __import__("json").loads(output.read_text(encoding="utf-8"))
    assert payload["policy_summary"]["passed"] is False
    assert payload["policy_summary"]["gates"][0]["matched_count"] == 1


def test_cli_reports_output_write_errors(tmp_path: Path, capsys) -> None:
    assert (
        cli.main(
            [
                "scan",
                str(ROOT / "examples/safe_agent"),
                "--output",
                str(tmp_path),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "agentverify: cannot write output:" in captured.err


def test_review_does_not_fail_by_default_but_can_be_opted_in(capsys) -> None:
    path = str(ROOT / "cases/python_auto_approval")

    assert cli.main(["scan", path, "--fail-on", "high"]) == 0
    assert cli.main(["scan", path, "--fail-on", "high", "--fail-on-kind", "any"]) == 1
    capsys.readouterr()


def test_json_baseline_suppresses_known_fingerprint(tmp_path: Path, capsys) -> None:
    target = ROOT / "cases/python_dangerous"
    baseline = tmp_path / "baseline.json"
    baseline.write_text(render_json(scan_repository(target)), encoding="utf-8")

    assert cli.main(["scan", str(target), "--baseline", str(baseline)]) == 0
    output = capsys.readouterr().out
    assert "Suppressed findings: 1" in output
    assert "Baseline: 0 new, 1 unchanged, 0 no longer reported" in output
    assert "No findings" in output


def test_native_ai_bom_can_be_reused_as_baseline(tmp_path: Path, capsys) -> None:
    target = ROOT / "cases/python_dangerous"
    baseline = tmp_path / "baseline.bom.json"
    baseline.write_text(render_bom(scan_repository(target)), encoding="utf-8")

    assert cli.main(["scan", str(target), "--baseline", str(baseline), "--format", "bom"]) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["risks"] == []
    assert payload["metadata"]["baseline_summary"]["unchanged"] == 1


def test_sarif_can_be_reused_as_baseline(tmp_path: Path, capsys) -> None:
    target = ROOT / "cases/python_dangerous"
    baseline = tmp_path / "baseline.sarif"
    baseline.write_text(render_sarif(scan_repository(target)), encoding="utf-8")

    assert cli.main(["scan", str(target), "--baseline", str(baseline), "--format", "json"]) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["findings"] == []
    assert payload["baseline_summary"]["unchanged"] == 1


def test_unknown_json_baseline_object_is_rejected(tmp_path: Path, capsys) -> None:
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"notes":"not an AgentVerify, BOM, or SARIF baseline"}', encoding="utf-8")

    assert (
        cli.main(["scan", str(ROOT / "cases/python_dangerous"), "--baseline", str(baseline)]) == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "agentverify: invalid baseline:" in captured.err
    assert "AgentVerify JSON report, AI BOM, SARIF report, or fingerprint list" in captured.err


def test_partial_baseline_does_not_claim_resolved_findings(tmp_path: Path, capsys) -> None:
    baseline = tmp_path / "baseline.json"
    baseline.write_text('["old-fingerprint"]', encoding="utf-8")
    paths = tmp_path / "changed.txt"
    paths.write_text("agent.py\n", encoding="utf-8")

    target = ROOT / "examples/safe_agent"
    assert (
        cli.main(
            [
                "scan",
                str(target),
                "--baseline",
                str(baseline),
                "--paths-from",
                str(paths),
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = __import__("json").loads(capsys.readouterr().out)
    schema = __import__("json").loads(
        (ROOT / "src/agentverify/schemas/agentverify-report-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(payload)
    assert payload["baseline_summary"] == {
        "baseline_fingerprints": 1,
        "current_fingerprints": 0,
        "new": 0,
        "unchanged": 0,
        "no_longer_reported": None,
    }


def test_version(capsys) -> None:
    with pytest.raises(SystemExit, match="0"):
        cli.main(["--version"])
    assert capsys.readouterr().out.strip() == "agentverify 0.1.0"


def test_cli_lists_enabled_reporting_rules_as_json(capsys) -> None:
    assert cli.main(["rules", "--format", "json"]) == 0

    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["schema_version"] == 1
    assert [rule["rule_id"] for rule in payload["rules"]] == sorted(
        rule["rule_id"] for rule in payload["rules"]
    )
    assert len(payload["rules"]) == 24
    assert next(rule for rule in payload["rules"] if rule["rule_id"] == "AV-EXEC001") == {
        "confidence": "high",
        "remediation": (
            "Pass a fixed argv list with shell disabled, or strictly validate and "
            "allowlist the command."
        ),
        "result_kind": "finding",
        "rule_id": "AV-EXEC001",
        "severity": "high",
        "summary": "A dynamic command is executed through a system shell",
    }


def test_cli_describes_one_rule_and_can_write_it(tmp_path: Path, capsys) -> None:
    output = tmp_path / "rule.txt"

    assert cli.main(["rules", "AV-FS001", "--output", str(output)]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    content = output.read_text(encoding="utf-8")
    assert content.startswith("AV-FS001 [review; high; confidence medium]\n")
    assert "AV-FS002" not in content
    assert "Remediation:" in content


def test_cli_emits_native_ai_bom(capsys) -> None:
    assert cli.main(["scan", str(ROOT / "examples/safe_agent"), "--format", "bom"]) == 0

    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["bom_format"] == "AgentVerify AI BOM"
    assert payload["metadata"]["generator"] == {"name": "AgentVerify", "version": "0.1.0"}
    assert any(asset["kind"] == "agent" for asset in payload["assets"])


def test_cli_prints_bundled_bom_schema(capsys) -> None:
    assert cli.main(["schema", "bom"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    Draft202012Validator.check_schema(schema)
    assert schema["title"] == "AgentVerify AI BOM 1.2"


def test_cli_prints_bundled_policy_schema(capsys) -> None:
    assert cli.main(["schema", "policy"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    policy = __import__("json").loads(
        (ROOT / "examples/ci-policy.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)
    Draft202012Validator(schema).validate(
        __import__("json").loads(
            (ROOT / "examples/repository-policy.json").read_text(encoding="utf-8")
        )
    )
    assert schema["title"] == "AgentVerify Policy 1"
    assert schema["$defs"]["gate"]["properties"]["rules"]["items"]["enum"] == list(RULE_CATALOG)


def test_cli_prints_bundled_report_schema(capsys) -> None:
    assert cli.main(["schema", "report"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    report = __import__("json").loads(render_json(scan_repository(ROOT / "cases/python_dangerous")))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report)
    assert report["report_format"] == "AgentVerify JSON Report"
    assert report["schema_version"] == 1
    assert schema["title"] == "AgentVerify JSON Report 1"
    assert schema["$defs"]["riskSummary"]["required"] == [
        "by_rule",
        "by_result_kind",
        "by_severity",
    ]


def test_cli_writes_bundled_schema_to_output_file(tmp_path: Path, capsys) -> None:
    output = tmp_path / "agentverify-policy.schema.json"

    assert cli.main(["schema", "policy", "--output", str(output)]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    schema = __import__("json").loads(output.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["title"] == "AgentVerify Policy 1"


def test_policy_gate_fails_without_hiding_matching_findings(tmp_path: Path, capsys) -> None:
    policy = tmp_path / "strict-policy.json"
    policy.write_text(
        '{"schema_version":1,"name":"strict","gates":['
        '{"id":"high-findings","result_kinds":["finding"],'
        '"min_severity":"high","max_count":0}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "scan",
                str(ROOT / "cases/python_dangerous"),
                "--policy",
                str(policy),
                "--format",
                "json",
            ]
        )
        == 1
    )
    payload = __import__("json").loads(capsys.readouterr().out)
    assert [finding["rule_id"] for finding in payload["findings"]] == ["AV-EXEC001"]
    summary = payload["policy_summary"]
    assert summary["passed"] is False
    assert summary["source"] == "strict-policy.json"
    assert len(summary["sha256"]) == 64
    assert summary["gates"][0]["matched_count"] == 1
    assert summary["gates"][0]["matched_fingerprints"] == [payload["findings"][0]["fingerprint"]]


def test_policy_gate_can_allow_a_review_budget(tmp_path: Path, capsys) -> None:
    policy = tmp_path / "review-budget.json"
    policy.write_text(
        '{"schema_version":1,"gates":['
        '{"id":"approval-review-budget","rules":["AV-APPROVAL001"],'
        '"result_kinds":["review"],"min_severity":"high","max_count":1}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(["scan", str(ROOT / "cases/python_auto_approval"), "--policy", str(policy)]) == 0
    )
    output = capsys.readouterr().out
    assert "Policy: unnamed [passed; 1 gates]" in output
    assert "approval-review-budget: 1 matched / 1 allowed [passed]" in output


def test_policy_is_evaluated_after_baseline(tmp_path: Path, capsys) -> None:
    target = ROOT / "cases/python_dangerous"
    baseline = tmp_path / "baseline.json"
    baseline.write_text(render_json(scan_repository(target)), encoding="utf-8")
    policy = tmp_path / "strict.json"
    policy.write_text(
        '{"schema_version":1,"gates":[{"id":"new-high","max_count":0}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "scan",
                str(target),
                "--baseline",
                str(baseline),
                "--policy",
                str(policy),
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["findings"] == []
    assert payload["policy_summary"]["evaluated_after_baseline"] is True
    assert payload["policy_summary"]["gates"][0]["matched_count"] == 0


def test_composed_policy_retains_each_gate_source_and_digest(tmp_path: Path, capsys) -> None:
    org = tmp_path / "org.json"
    org.write_text(
        '{"schema_version":1,"name":"org","gates":['
        '{"id":"org-high","result_kinds":["finding"],"max_count":0}]}',
        encoding="utf-8",
    )
    repository = tmp_path / "repository.json"
    repository.write_text(
        '{"schema_version":1,"name":"repository","extends":["org.json"],"gates":['
        '{"id":"repository-reviews","result_kinds":["review"],"max_count":5}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "scan",
                str(ROOT / "cases/python_dangerous"),
                "--policy",
                str(repository),
                "--format",
                "json",
            ]
        )
        == 1
    )
    summary = __import__("json").loads(capsys.readouterr().out)["policy_summary"]
    assert summary["name"] == "repository"
    assert [source["source"] for source in summary["sources"]] == [
        "org.json",
        "repository.json",
    ]
    assert [gate["policy_source"] for gate in summary["gates"]] == [
        "org.json",
        "repository.json",
    ]
    assert all(len(source["sha256"]) == 64 for source in summary["sources"])
    assert summary["gates"][0]["matched_count"] == 1
    assert summary["gates"][0]["passed"] is False

    assert cli.main(["scan", str(ROOT / "examples/safe_agent"), "--policy", str(repository)]) == 0
    text = capsys.readouterr().out
    assert "Policy sources: 2" in text
    assert "org-high (org.json): 0 matched / 0 allowed [passed]" in text


def test_invalid_policy_is_rejected_before_scanning(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / "invalid.json"
    policy.write_text(
        '{"schema_version":1,"gates":[],"disable_rules":["AV-EXEC001"]}',
        encoding="utf-8",
    )

    def unexpected_scan(*args: object, **kwargs: object) -> None:
        raise AssertionError("scan must not run")

    monkeypatch.setattr(cli, "scan_repository", unexpected_scan)

    assert cli.main(["scan", str(ROOT / "cases/python_dangerous"), "--policy", str(policy)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown policy fields: disable_rules" in captured.err


def test_unknown_policy_rule_is_rejected_before_scanning(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / "invalid-rule.json"
    policy.write_text(
        '{"schema_version":1,"gates":[{"id":"typo","rules":["AV-EXECC001"],"max_count":0}]}',
        encoding="utf-8",
    )

    def unexpected_scan(*args: object, **kwargs: object) -> None:
        raise AssertionError("scan must not run")

    monkeypatch.setattr(cli, "scan_repository", unexpected_scan)

    assert cli.main(["scan", str(ROOT / "cases/python_dangerous"), "--policy", str(policy)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "rules contains unsupported values: AV-EXECC001" in captured.err


def test_impossible_policy_rule_filter_is_rejected_before_scanning(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / "dead-filter.json"
    policy.write_text(
        '{"schema_version":1,"gates":['
        '{"id":"wrong-kind","rules":["AV-APPROVAL001"],"max_count":0}]}',
        encoding="utf-8",
    )

    def unexpected_scan(*args: object, **kwargs: object) -> None:
        raise AssertionError("scan must not run")

    monkeypatch.setattr(cli, "scan_repository", unexpected_scan)

    assert (
        cli.main(["scan", str(ROOT / "cases/python_auto_approval"), "--policy", str(policy)]) == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "AV-APPROVAL001 emits review" in captured.err


def test_paths_from_scans_only_selected_repository_paths(tmp_path: Path, capsys) -> None:
    paths = tmp_path / "changed.txt"
    paths.write_text("cases/python_dangerous/agent.py\n", encoding="utf-8")

    assert cli.main(["scan", str(ROOT), "--paths-from", str(paths), "--format", "json"]) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["scan_scope"] == "selected-paths"
    assert payload["path_filters"] == ["cases/python_dangerous/agent.py"]
    assert payload["files_scanned"] == 1
    assert [finding["rule_id"] for finding in payload["findings"]] == ["AV-EXEC001"]


def test_paths_from_rejects_escape(tmp_path: Path, capsys) -> None:
    paths = tmp_path / "changed.txt"
    paths.write_text("../outside.py\n", encoding="utf-8")

    assert cli.main(["scan", str(ROOT), "--paths-from", str(paths)]) == 2
    assert "must stay inside the scan root" in capsys.readouterr().err


def test_empty_paths_from_scans_nothing_but_dot_selects_root(tmp_path: Path, capsys) -> None:
    paths = tmp_path / "changed.txt"
    paths.write_text("", encoding="utf-8")
    target = ROOT / "cases/python_dangerous"

    assert cli.main(["scan", str(target), "--paths-from", str(paths), "--format", "json"]) == 0
    empty = __import__("json").loads(capsys.readouterr().out)
    assert empty["files_scanned"] == 0
    assert empty["path_filters"] == []

    paths.write_text(".\n", encoding="utf-8")
    assert cli.main(["scan", str(target), "--paths-from", str(paths), "--format", "json"]) == 0
    selected = __import__("json").loads(capsys.readouterr().out)
    assert selected["files_scanned"] == 1
    assert selected["path_filters"] == ["."]


def test_cli_can_require_suppression_expiry(tmp_path: Path, capsys) -> None:
    (tmp_path / "agent.py").write_text(
        """import subprocess
# agentverify: ignore AV-EXEC001 -- temporary exception
subprocess.run(command, shell=True)
""",
        encoding="utf-8",
    )

    assert (
        cli.main(["scan", str(tmp_path), "--require-suppression-expiry", "--fail-on", "high"]) == 1
    )
    output = capsys.readouterr().out
    assert "AV-EXEC001" in output
    assert "missing-expiry" in output

from __future__ import annotations

from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agentverify import cli
from agentverify.report import render_bom, render_json
from agentverify.scanner import scan_repository

ROOT = Path(__file__).resolve().parents[1]


def test_cli_handles_closed_output_pipe(monkeypatch: pytest.MonkeyPatch) -> None:
    def closed_pipe(*args: object, **kwargs: object) -> None:
        raise BrokenPipeError

    monkeypatch.setattr("builtins.print", closed_pipe)
    assert cli.main(["scan", str(ROOT / "examples/safe_agent")]) == 0


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
    assert schema["title"] == "AgentVerify AI BOM 1.0"


def test_cli_prints_bundled_policy_schema(capsys) -> None:
    assert cli.main(["schema", "policy"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    policy = __import__("json").loads(
        (ROOT / "examples/ci-policy.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)
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

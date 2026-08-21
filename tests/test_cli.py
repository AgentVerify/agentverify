from __future__ import annotations

from pathlib import Path

import pytest

from agentverify import cli
from agentverify.report import render_json
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
    assert "No findings" in output


def test_version(capsys) -> None:
    with pytest.raises(SystemExit, match="0"):
        cli.main(["--version"])
    assert capsys.readouterr().out.strip() == "agentverify 0.1.0"


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

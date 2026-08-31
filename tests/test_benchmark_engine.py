from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_engine.py"
ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("agentverify_benchmark_engine", SCRIPT)
assert SPEC is not None
benchmark_engine = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(benchmark_engine)


def test_filter_repositories_preserves_corpus_order() -> None:
    repositories = [
        {"repository": "one/repo"},
        {"repository": "two/repo"},
        {"repository": "three/repo"},
    ]

    filtered = benchmark_engine.filter_repositories(
        repositories,
        ["three/repo", "one/repo"],
    )

    assert [row["repository"] for row in filtered] == ["one/repo", "three/repo"]


def test_filter_repositories_fails_on_unknown_name() -> None:
    repositories = [{"repository": "one/repo"}]

    try:
        benchmark_engine.filter_repositories(repositories, ["missing/repo"])
    except SystemExit as exc:
        assert str(exc) == "unknown --repository value(s): missing/repo"
    else:
        raise AssertionError("expected SystemExit for unknown repository")


def test_validate_engine_results_accepts_checked_snapshot() -> None:
    payload = json.loads((ROOT / "benchmarks/engine-results.json").read_text(encoding="utf-8"))

    benchmark_engine.validate_engine_results(payload)


def test_checked_snapshot_tracks_openai_streaming_runs() -> None:
    payload = json.loads((ROOT / "benchmarks/engine-results.json").read_text(encoding="utf-8"))

    summary = payload["summary"]["typescript_openai_run_streaming"]
    assert summary == {
        "total": 17,
        "direct_run": 11,
        "runner_run": 6,
        "configured_by_edges": 17,
        "repositories": 1,
    }


def test_checked_snapshot_tracks_openai_codex_tools() -> None:
    payload = json.loads((ROOT / "benchmarks/engine-results.json").read_text(encoding="utf-8"))

    summary = payload["summary"]["typescript_openai_codex_tool"]
    assert summary == {
        "components": 8,
        "tools": 4,
        "controls": 4,
        "approval_policy_controls": 3,
        "thread_option_controls": 1,
        "approval_policy_never": 6,
        "workspace_write_sandbox": 8,
        "network_access_enabled": 6,
        "web_search_disabled": 6,
        "stream_callbacks": 4,
        "run_context_thread_reuse": 4,
        "working_directory_literal": 4,
        "working_directory_binding": 4,
        "agent_tool_edges": 4,
        "configured_by_edges": 4,
        "repositories": 1,
    }


def test_validate_engine_results_rejects_malformed_snapshot() -> None:
    payload = json.loads((ROOT / "benchmarks/engine-results.json").read_text(encoding="utf-8"))
    payload.pop("repositories")

    with pytest.raises(ValidationError, match="'repositories' is a required property"):
        benchmark_engine.validate_engine_results(payload)

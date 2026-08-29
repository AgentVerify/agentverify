from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_engine.py"
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

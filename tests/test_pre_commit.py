from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pre_commit_hook_manifest_matches_documented_release_hook() -> None:
    manifest = (ROOT / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")

    assert "- id: agentverify" in manifest
    assert "name: AgentVerify agent security scan" in manifest
    assert "entry: agentverify scan . --fail-on high --fail-on-kind finding" in manifest
    assert "language: python" in manifest
    assert "pass_filenames: false" in manifest
    assert "always_run: true" in manifest
    assert "stages: [pre-commit]" in manifest


def test_local_pre_commit_example_uses_installed_cli_and_repository_context() -> None:
    example = (ROOT / "examples/pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "repo: local" in example
    assert "id: agentverify" in example
    assert "entry: agentverify scan . --fail-on high --fail-on-kind finding" in example
    assert "language: system" in example
    assert "pass_filenames: false" in example
    assert "always_run: true" in example


def test_pre_commit_docs_link_manifest_and_local_example() -> None:
    docs = (ROOT / "docs/pre-commit.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "[`examples/pre-commit-config.yaml`](../examples/pre-commit-config.yaml)" in docs
    assert "`.pre-commit-hooks.yaml` manifest" in docs
    assert "`language: system` deliberately uses the reviewed version" in docs
    assert "Keep `pass_filenames: false`" in docs
    assert "[copyable local config](examples/pre-commit-config.yaml)" in readme

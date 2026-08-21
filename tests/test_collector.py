from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collect_repositories.py"
SPEC = importlib.util.spec_from_file_location("agentverify_collect_repositories", SCRIPT)
assert SPEC and SPEC.loader
COLLECTOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = COLLECTOR
SPEC.loader.exec_module(COLLECTOR)
ensure_clone = COLLECTOR.ensure_clone
locked_commits = COLLECTOR.locked_commits


def git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_existing_clone_is_reset_to_locked_commit_without_network(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    repository = cache / "owner--repo"
    repository.mkdir(parents=True)
    git(repository, "init", "-q")
    git(repository, "config", "user.email", "test@example.invalid")
    git(repository, "config", "user.name", "AgentVerify test")
    tracked = repository / "tracked.txt"
    tracked.write_text("first\n", encoding="utf-8")
    git(repository, "add", "tracked.txt")
    git(repository, "commit", "-qm", "first")
    first = git(repository, "rev-parse", "HEAD")
    tracked.write_text("second\n", encoding="utf-8")
    git(repository, "commit", "-qam", "second")

    ensure_clone("owner/repo", cache, first)

    assert git(repository, "rev-parse", "HEAD") == first


def test_locked_commits_reads_only_successful_pinned_results(tmp_path: Path) -> None:
    lock = tmp_path / "repository-data.json"
    lock.write_text(
        json.dumps(
            {
                "repositories": [
                    {"repository": "owner/good", "commit": "abc123", "status": "ok"},
                    {"repository": "owner/failed", "commit": "def456", "status": "error"},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert locked_commits(lock) == {"owner/good": "abc123"}
    assert locked_commits(tmp_path / "missing.json") == {}

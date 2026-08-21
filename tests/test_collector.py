from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collect_repositories.py"
SPEC = importlib.util.spec_from_file_location("agentverify_collect_repositories", SCRIPT)
assert SPEC and SPEC.loader
COLLECTOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = COLLECTOR
SPEC.loader.exec_module(COLLECTOR)
ensure_clone = COLLECTOR.ensure_clone
analysis_selection_hints = COLLECTOR.analysis_selection_hints
expand_python_mcp_dependencies = COLLECTOR.expand_python_mcp_dependencies
expand_python_analysis_dependencies = COLLECTOR.expand_python_analysis_dependencies
locked_commits = COLLECTOR.locked_commits
python_module_indexes = COLLECTOR.python_module_indexes
select_files = COLLECTOR.select_files


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


def test_analysis_selection_hints_are_versioned_and_exact(tmp_path: Path) -> None:
    hints = tmp_path / "hints.json"
    hints.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "repositories": {"owner/repo": ["src/caller.py", "src/settings.py"]},
            }
        ),
        encoding="utf-8",
    )

    assert analysis_selection_hints(hints) == {
        "owner/repo": ("src/caller.py", "src/settings.py")
    }
    assert analysis_selection_hints(tmp_path / "missing.json") == {}

    hints.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "repositories": {"owner/repo": ["src/caller.py", "src/caller.py"]},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate paths"):
        analysis_selection_hints(hints)


def test_python_module_indexes_include_every_nested_source_root() -> None:
    modules, path_modules = python_module_indexes(
        ["src/distribution/src/package/security/ssrf_http.py"]
    )

    assert modules["package.security.ssrf_http"] == (
        "src/distribution/src/package/security/ssrf_http.py"
    )
    assert "package.security.ssrf_http" in path_modules[
        "src/distribution/src/package/security/ssrf_http.py"
    ]


def test_manifest_selection_includes_kubernetes_but_not_ci_workflows() -> None:
    selected = select_files(
        [
            ".github/workflows/deploy.yaml",
            "helm/agent/templates/statefulset.yaml",
            "k8s/pod.yml",
            "src/agent.py",
        ],
        max_files=10,
    )

    assert "helm/agent/templates/statefulset.yaml" in selected
    assert "k8s/pod.yml" in selected
    assert ".github/workflows/deploy.yaml" not in selected


def test_selection_prioritizes_explicit_ssrf_sources_under_tight_budget() -> None:
    selected = select_files(
        [
            "src/agent.py",
            "tests/url_safety.py",
            "deep/pkg/security/ssrf_guard.ts",
        ],
        max_files=1,
    )

    assert selected == ["deep/pkg/security/ssrf_guard.ts"]


def test_mcp_dependency_expansion_follows_local_reexports(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    (repository / "src/pkg/tools").mkdir(parents=True)
    (repository / "src/pkg/server.py").write_text(
        "from pkg.tools import ToolManager\n\n"
        "async def dispatch(manager, name, arguments):\n"
        "    return await manager.call_tool(name, arguments)\n",
        encoding="utf-8",
    )
    (repository / "src/pkg/tools/__init__.py").write_text(
        "from .tool_manager import ToolManager\n",
        encoding="utf-8",
    )
    (repository / "src/pkg/tools/tool_manager.py").write_text(
        "class ToolManager:\n    pass\n",
        encoding="utf-8",
    )
    (repository / "src/pkg/unrelated.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(repository, "init", "-q")
    git(repository, "config", "user.email", "test@example.invalid")
    git(repository, "config", "user.name", "AgentVerify test")
    git(repository, "add", ".")
    git(repository, "commit", "-qm", "fixture")
    tree_paths = git(repository, "ls-tree", "-r", "--name-only", "HEAD").splitlines()

    dependencies = expand_python_mcp_dependencies(
        repository,
        tree_paths,
        ["src/pkg/server.py"],
        max_dependency_files=4,
    )

    assert dependencies == [
        "src/pkg/tools/__init__.py",
        "src/pkg/tools/tool_manager.py",
    ]
    assert expand_python_mcp_dependencies(
        repository,
        tree_paths,
        ["src/pkg/server.py"],
        max_dependency_files=1,
    ) == ["src/pkg/tools/__init__.py"]


def test_dependency_expansion_ignores_non_forwarding_roots(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    (repository / "src/pkg").mkdir(parents=True)
    (repository / "src/pkg/main.py").write_text(
        "from pkg import helper\nprint(helper.VALUE)\n",
        encoding="utf-8",
    )
    (repository / "src/pkg/helper.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(repository, "init", "-q")
    git(repository, "config", "user.email", "test@example.invalid")
    git(repository, "config", "user.name", "AgentVerify test")
    git(repository, "add", ".")
    git(repository, "commit", "-qm", "fixture")
    tree_paths = git(repository, "ls-tree", "-r", "--name-only", "HEAD").splitlines()

    assert (
        expand_python_mcp_dependencies(
            repository,
            tree_paths,
            ["src/pkg/main.py"],
            max_dependency_files=4,
        )
        == []
    )


def test_dependency_expansion_follows_called_url_security_helpers(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    (repository / "src/pkg/security").mkdir(parents=True)
    (repository / "src/pkg/client.py").write_text(
        "from pkg.security.url_safety import safe_get as protected_get\n\n"
        "def fetch(url):\n"
        "    return protected_get(url)\n",
        encoding="utf-8",
    )
    (repository / "src/pkg/security/url_safety.py").write_text(
        "from .ssrf_peer import assert_safe_peer\n\n"
        "def safe_get(url):\n"
        "    return assert_safe_peer(url)\n",
        encoding="utf-8",
    )
    (repository / "src/pkg/security/ssrf_peer.py").write_text(
        "def assert_safe_peer(url):\n    return url\n",
        encoding="utf-8",
    )
    (repository / "src/pkg/unrelated.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(repository, "init", "-q")
    git(repository, "config", "user.email", "test@example.invalid")
    git(repository, "config", "user.name", "AgentVerify test")
    git(repository, "add", ".")
    git(repository, "commit", "-qm", "fixture")
    tree_paths = git(repository, "ls-tree", "-r", "--name-only", "HEAD").splitlines()

    assert expand_python_analysis_dependencies(
        repository,
        tree_paths,
        ["src/pkg/client.py"],
        max_dependency_files=4,
    ) == [
        "src/pkg/security/url_safety.py",
        "src/pkg/security/ssrf_peer.py",
    ]


def test_analysis_hints_materialize_callers_within_dependency_budget(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    (repository / "src/pkg/security").mkdir(parents=True)
    (repository / "src/pkg/client.py").write_text(
        "from pkg.security.ssrf_http import safe_get\n\n"
        "def fetch(url):\n"
        "    return safe_get(url)\n",
        encoding="utf-8",
    )
    (repository / "src/pkg/settings.py").write_text(
        "SSRF_ENABLED = True\n",
        encoding="utf-8",
    )
    (repository / "src/pkg/security/ssrf_http.py").write_text(
        "def safe_get(url):\n    return url\n",
        encoding="utf-8",
    )
    git(repository, "init", "-q")
    git(repository, "config", "user.email", "test@example.invalid")
    git(repository, "config", "user.name", "AgentVerify test")
    git(repository, "add", ".")
    git(repository, "commit", "-qm", "fixture")
    tree_paths = git(repository, "ls-tree", "-r", "--name-only", "HEAD").splitlines()

    assert expand_python_analysis_dependencies(
        repository,
        tree_paths,
        ["src/pkg/security/ssrf_http.py"],
        max_dependency_files=2,
        analysis_hints=("src/pkg/client.py", "src/pkg/settings.py"),
    ) == ["src/pkg/client.py", "src/pkg/settings.py"]
    with pytest.raises(ValueError, match="exceed"):
        expand_python_analysis_dependencies(
            repository,
            tree_paths,
            ["src/pkg/security/ssrf_http.py"],
            max_dependency_files=1,
            analysis_hints=("src/pkg/client.py", "src/pkg/settings.py"),
        )
    with pytest.raises(ValueError, match="absent"):
        expand_python_analysis_dependencies(
            repository,
            tree_paths,
            ["src/pkg/security/ssrf_http.py"],
            max_dependency_files=2,
            analysis_hints=("src/pkg/missing.py",),
        )


def test_security_dependency_expansion_requires_a_real_imported_call(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    (repository / "src/pkg/security").mkdir(parents=True)
    (repository / "src/pkg/client.py").write_text(
        "from pkg.security.url_safety import safe_get\n"
        "MESSAGE = 'safe_get(url)'\n",
        encoding="utf-8",
    )
    (repository / "src/pkg/security/url_safety.py").write_text(
        "def safe_get(url):\n    return url\n",
        encoding="utf-8",
    )
    git(repository, "init", "-q")
    git(repository, "config", "user.email", "test@example.invalid")
    git(repository, "config", "user.name", "AgentVerify test")
    git(repository, "add", ".")
    git(repository, "commit", "-qm", "fixture")
    tree_paths = git(repository, "ls-tree", "-r", "--name-only", "HEAD").splitlines()

    assert (
        expand_python_analysis_dependencies(
            repository,
            tree_paths,
            ["src/pkg/client.py"],
            max_dependency_files=4,
        )
        == []
    )

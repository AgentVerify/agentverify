"""Render the pinned repository dataset as a reviewable Markdown table."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def signals(repository: dict, group: str) -> str:
    values = sorted(repository.get("signals", {}).get(group, {}))
    return ", ".join(values) if values else "—"


def main() -> None:
    data = json.loads((ROOT / "research/repository-data.json").read_text(encoding="utf-8"))
    repositories = data["repositories"]
    category_count = len(Counter(repository["category"] for repository in repositories))
    lines = [
        "# Repository corpus",
        "",
        f"Generated at `{data['generated_at']}` from `{data['method']['collector']}`.",
        "",
        "## Method",
        "",
        (
            f"The initial corpus contains **{len(repositories)} repositories** across "
            f"**{category_count} categories**, all pinned to commits. The collector scanned "
            f"{sum(repository['files_scanned'] for repository in repositories):,} selected "
            f"source/manifest files ({sum(repository['bytes_scanned'] for repository in repositories) / 1_000_000:.1f} MB). "
            "Selection prioritizes manifests and agent, tool, MCP, permission, approval, sandbox, "
            "executor, and security paths, then materializes "
            f"{sum(repository.get('dependency_files_materialized', 0) for repository in repositories):,} "
            "bounded local Python dependencies reached from MCP forwarding roots."
        ),
        "",
        (
            "Signals mean code evidence was observed. Absence is not proof that a repository lacks a "
            "feature or control. Evidence in `repository-data.json` includes immutable commit, path, "
            "line, excerpt, and matched pattern."
        ),
        "",
        "## Repositories",
        "",
        "| Repository | Category | Commit | Languages | Frameworks | Providers | Capabilities | Protocols | Controls | Candidate risks |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for repository in repositories:
        lines.append(
            f"| [{repository['repository']}]({repository['url']}) | {repository['category']} | "
            f"`{repository['commit'][:8]}` | {', '.join(repository['languages']) or '—'} | "
            f"{signals(repository, 'frameworks')} | {signals(repository, 'providers')} | "
            f"{signals(repository, 'capabilities')} | {signals(repository, 'protocols')} | "
            f"{signals(repository, 'controls')} | {signals(repository, 'risk_patterns')} |"
        )
    lines += [
        "",
        "## Reproduce",
        "",
        "```console",
        "python3 scripts/collect_repositories.py  # reuses the recorded commit lock by default",
        "python3 scripts/render_repositories.py",
        "```",
        "",
    ]
    (ROOT / "research/repositories.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Rendered {len(repositories)} repositories")


if __name__ == "__main__":
    main()

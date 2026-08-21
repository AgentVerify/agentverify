"""Collect reproducible, code-level signals from the AgentVerify research corpus.

The collector uses partial, no-checkout Git clones. It records the exact commit and only
downloads bounded source/manifests selected from the Git tree. The result is deterministic
JSON that can be regenerated without a GitHub API token.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

SIGNATURES: dict[str, dict[str, tuple[str, ...]]] = {
    "frameworks": {
        "langchain": (r"\blangchain(?:_|\.|\b)",),
        "langgraph": (r"\blanggraph(?:\.|\b)", r"StateGraph\s*\("),
        "crewai": (r"\bcrewai(?:\.|\b)", r"\bCrew\s*\("),
        "autogen": (r"\bautogen(?:_|\.|\b)", r"AssistantAgent\s*\("),
        "openai-agents": (r"from agents import", r"@function_tool\b", r"\bRunner\.run"),
        "pydantic-ai": (r"\bpydantic_ai(?:\.|\b)",),
        "google-adk": (r"\bgoogle\.adk\b", r"\bLlmAgent\s*\("),
        "smolagents": (r"\bsmolagents(?:\.|\b)",),
        "semantic-kernel": (r"\bsemantic_kernel(?:\.|\b)",),
        "llama-index": (r"\bllama_index(?:\.|\b)",),
        "vercel-ai": (r"from [\"']ai[\"']", r"\bgenerateText\s*\("),
        "mastra": (r"@mastra/", r"\bmastra(?:\.|\b)"),
    },
    "providers": {
        "openai": (r"\bOpenAI\s*\(", r"\bChatOpenAI\s*\(", r"OPENAI_API_KEY"),
        "anthropic": (r"\bAnthropic\s*\(", r"\bChatAnthropic\s*\(", r"ANTHROPIC_API_KEY"),
        "azure-openai": (r"\bAzureOpenAI\s*\(", r"AZURE_OPENAI_"),
        "google": (r"GOOGLE_API_KEY", r"GEMINI_API_KEY", r"\bChatGoogleGenerativeAI\s*\("),
        "aws-bedrock": (r"\bBedrockChat\s*\(", r"\bbedrock-runtime\b", r"AWS_BEDROCK"),
        "ollama": (r"\bOllama\s*\(", r"OLLAMA_HOST"),
    },
    "capabilities": {
        "shell-execution": (
            r"subprocess\.(?:run|Popen|call|check_output)\s*\(",
            r"child_process\.(?:exec|spawn)",
            r"execSync\s*\(",
            r"Deno\.Command\s*\(",
        ),
        "code-execution": (r"\bexec\s*\(", r"\beval\s*\(", r"CodeInterpreter", r"PythonREPL"),
        "filesystem": (
            r"\bopen\s*\([^\n]+[\"'][wax+]",
            r"(?:writeFile|unlink|rm|rmdir|mkdir)Sync\s*\(",
            r"fs\.(?:promises\.)?(?:writeFile|unlink|rm|rmdir|mkdir)\s*\(",
        ),
        "browser": (r"\bplaywright\b", r"\bselenium\b", r"\bpuppeteer\b", r"BrowserTool"),
        "network": (r"requests\.(?:get|post|put|delete)\s*\(", r"\bfetch\s*\(", r"httpx\."),
        "database": (r"\bsqlalchemy\b", r"\bpostgres(?:ql)?\b", r"\bmongodb\b", r"\bredis\b"),
    },
    "protocols": {
        "mcp": (
            r"modelcontextprotocol",
            r"@modelcontextprotocol/",
            r"\bFastMCP\s*\(",
            r"mcpServers",
        ),
        "a2a": (r"\bA2A\b", r"agent2agent", r"a2a-protocol"),
    },
    "controls": {
        "human-approval": (
            r"human.in.the.loop",
            r"\bapproval\b",
            r"require_confirmation",
            r"interrupt\s*\(",
        ),
        "audit-or-tracing": (
            r"\baudit(?:_|\s|log)",
            r"\btrac(?:e|ing)\b",
            r"opentelemetry",
            r"langsmith",
        ),
        "sandboxing": (
            r"\bsandbox(?:ed|ing)?\b",
            r"\bDockerSandbox\b",
            r"\bcontainer(?:ized|isation|ization)?\b",
        ),
        "allowlist": (r"\ballowlist\b", r"\bwhitelist\b", r"allowed_(?:tools|commands|paths)"),
        "authentication": (
            r"\bauthentication\b",
            r"\bauthorization\b",
            r"\bOAuth2?\b",
            r"\bAPI_KEY\b",
        ),
    },
    "risk_patterns": {
        "shell-true": (r"shell\s*=\s*True",),
        "dynamic-shell-command": (r"subprocess\.(?:run|Popen)\s*\([^\n]{0,100}(?:command|cmd)",),
        "unrestricted-mcp-tool-proxy": (r"call_tool\s*\([^\n]{0,160}(?:arguments|params)",),
        "auto-approve": (r"auto.?approv", r"skip.?confirmation", r"dangerously.?skip"),
        "broad-filesystem-path": (r"allowed_(?:director|path)[^\n]{0,80}[\"']/[\"']",),
    },
}

SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".cs", ".java"}
CONFIG_SUFFIXES = {".yml", ".yaml"}
CONFIG_PATH_WORDS = {"chart", "charts", "deploy", "helm", "k8s", "kubernetes"}
MANIFEST_NAMES = {
    "pyproject.toml",
    "package.json",
    "requirements.txt",
    "setup.py",
    "setup.cfg",
    "Cargo.toml",
    "go.mod",
    "Pipfile",
    "environment.yml",
    "docker-compose.yml",
}
PRIORITY_WORDS = (
    "agent",
    "tool",
    "mcp",
    "permission",
    "approval",
    "sandbox",
    "executor",
    "security",
)
SKIP_PARTS = {"node_modules", "vendor", "dist", "build", ".venv", "fixtures", "snapshots"}
EXTENSION_LANGUAGE = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".cs": "C#",
    ".java": "Java",
}


@dataclass
class Evidence:
    path: str
    line: int
    excerpt: str
    pattern: str


@dataclass
class RepositoryResult:
    repository: str
    url: str
    category: str
    framework_hint: str
    rationale: str
    status: str
    commit: str = ""
    files_in_tree: int = 0
    files_scanned: int = 0
    bytes_scanned: int = 0
    languages: list[str] = field(default_factory=list)
    signals: dict[str, dict[str, list[Evidence]]] = field(default_factory=dict)
    error: str = ""


def run_git(
    args: list[str],
    cwd: Path | None = None,
    timeout: int = 180,
    input_text: str | None = None,
) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        input=input_text,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or f"git exited {completed.returncode}")
    return completed.stdout


def ensure_clone(repository: str, cache_dir: Path, commit: str | None = None) -> Path:
    target = cache_dir / repository.replace("/", "--")
    url = f"https://github.com/{repository}.git"
    if not target.exists():
        run_git(["clone", "--depth=1", "--filter=blob:none", "--no-checkout", url, str(target)])
    if commit:
        try:
            run_git(["cat-file", "-e", f"{commit}^{{commit}}"], cwd=target)
        except RuntimeError:
            run_git(["fetch", "--depth=1", "origin", commit], cwd=target, timeout=300)
        run_git(["update-ref", "HEAD", commit], cwd=target)
    else:
        run_git(["fetch", "--depth=1", "origin", "HEAD"], cwd=target)
        run_git(["update-ref", "HEAD", "FETCH_HEAD"], cwd=target)
    return target


def select_files(paths: list[str], max_files: int) -> list[str]:
    manifests: list[tuple[int, str]] = []
    priority_sources: list[tuple[int, str]] = []
    other_sources: list[tuple[int, str]] = []
    for path in paths:
        parts = set(Path(path).parts)
        if parts & SKIP_PARTS:
            continue
        name = Path(path).name
        suffix = Path(path).suffix.lower()
        lowered_parts = {part.lower() for part in Path(path).parts}
        config_manifest = (
            suffix in CONFIG_SUFFIXES
            and ".github" not in lowered_parts
            and any(word in part for word in CONFIG_PATH_WORDS for part in lowered_parts)
        )
        if name not in MANIFEST_NAMES and suffix not in SOURCE_SUFFIXES and not config_manifest:
            continue
        lowered = path.lower()
        item = (len(Path(path).parts), path)
        if name in MANIFEST_NAMES or config_manifest:
            manifests.append(item)
        elif any(word in lowered for word in PRIORITY_WORDS):
            priority_sources.append(item)
        else:
            other_sources.append(item)
    manifests.sort()
    priority_sources.sort()
    other_sources.sort()
    manifest_budget = min(len(manifests), max(1, max_files // 4))
    selected = manifests[:manifest_budget]
    source_budget = max_files - len(selected)
    selected.extend(priority_sources[:source_budget])
    source_budget = max_files - len(selected)
    selected.extend(other_sources[:source_budget])
    return [item[1] for item in selected]


def materialize_files(clone: Path, paths: list[str]) -> None:
    """Fetch selected partial-clone blobs in one sparse-checkout operation."""
    run_git(["sparse-checkout", "init", "--no-cone"], cwd=clone)
    # Non-cone patterns anchored at the repository root preserve exact paths for typical
    # source trees. Escaping keeps bracket and glob characters in filenames literal.
    escaped = []
    for path in paths:
        pattern = path.replace("\\", "\\\\")
        for character in "*?[":
            pattern = pattern.replace(character, f"\\{character}")
        escaped.append(f"/{pattern}")
    run_git(
        ["sparse-checkout", "set", "--no-cone", "--stdin"],
        cwd=clone,
        timeout=300,
        input_text="\n".join(escaped) + "\n",
    )
    run_git(["checkout", "--force", "HEAD"], cwd=clone, timeout=300)


def compile_signatures() -> dict[str, dict[str, list[tuple[str, re.Pattern[str]]]]]:
    return {
        group: {
            name: [(source, re.compile(source, re.IGNORECASE)) for source in patterns]
            for name, patterns in group_signatures.items()
        }
        for group, group_signatures in SIGNATURES.items()
    }


COMPILED_SIGNATURES = compile_signatures()


def analyze_file(path: str, content: str, signals: dict[str, dict[str, list[Evidence]]]) -> None:
    lines = content.splitlines()
    for group, group_signatures in COMPILED_SIGNATURES.items():
        for name, patterns in group_signatures.items():
            evidence = signals.setdefault(group, {}).setdefault(name, [])
            if len(evidence) >= 3:
                continue
            for line_number, line in enumerate(lines, start=1):
                if len(evidence) >= 3:
                    break
                for source, pattern in patterns:
                    if pattern.search(line):
                        evidence.append(Evidence(path, line_number, line.strip()[:240], source))
                        break


def collect_one(
    row: dict[str, str],
    cache_dir: Path,
    max_files: int,
    max_bytes: int,
    locked_commit: str | None = None,
) -> RepositoryResult:
    repository = row["repository"]
    result = RepositoryResult(
        repository=repository,
        url=f"https://github.com/{repository}",
        category=row["category"],
        framework_hint=row["framework_hint"],
        rationale=row["rationale"],
        status="error",
    )
    try:
        clone = ensure_clone(repository, cache_dir, locked_commit)
        result.commit = run_git(["rev-parse", "HEAD"], cwd=clone).strip()
        paths = run_git(["ls-tree", "-r", "--name-only", "HEAD"], cwd=clone).splitlines()
        result.files_in_tree = len(paths)
        extension_counts = Counter(Path(path).suffix.lower() for path in paths)
        result.languages = [
            language
            for extension, language in sorted(
                EXTENSION_LANGUAGE.items(), key=lambda item: extension_counts[item[0]], reverse=True
            )
            if extension_counts[extension]
        ][:4]
        selected_paths = select_files(paths, max_files)
        materialize_files(clone, selected_paths)
        remaining = max_bytes
        for path in selected_paths:
            if remaining <= 0:
                break
            try:
                source_path = clone / path
                content = source_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            encoded_size = len(content.encode("utf-8", errors="ignore"))
            if encoded_size > remaining:
                content = content.encode("utf-8")[:remaining].decode("utf-8", errors="ignore")
                encoded_size = len(content.encode("utf-8"))
            result.files_scanned += 1
            result.bytes_scanned += encoded_size
            remaining -= encoded_size
            analyze_file(path, content, result.signals)
        result.signals = {
            group: {name: evidence for name, evidence in names.items() if evidence}
            for group, names in result.signals.items()
        }
        result.signals = {group: names for group, names in result.signals.items() if names}
        result.status = "ok"
    except Exception as exc:  # noqa: BLE001 - one failed repository must not abort the corpus
        result.error = f"{type(exc).__name__}: {exc}"
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("research/corpus.csv"))
    parser.add_argument("--output", type=Path, default=Path("research/repository-data.json"))
    parser.add_argument("--cache-dir", type=Path, default=Path(".agentverify-cache/repositories"))
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--max-files", type=int, default=220)
    parser.add_argument("--max-bytes", type=int, default=2_000_000)
    parser.add_argument(
        "--lock-file",
        type=Path,
        default=Path("research/repository-data.json"),
        help="reuse commits from a previous collector result when it exists",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="ignore the lock file and intentionally refresh repositories to origin HEAD",
    )
    return parser.parse_args()


def locked_commits(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        item["repository"]: item["commit"]
        for item in payload.get("repositories", [])
        if item.get("status") == "ok" and item.get("repository") and item.get("commit")
    }


def main() -> int:
    args = parse_args()
    with args.corpus.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    commits = {} if args.refresh else locked_commits(args.lock_file)
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    results: list[RepositoryResult] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                collect_one,
                row,
                args.cache_dir,
                args.max_files,
                args.max_bytes,
                commits.get(row["repository"]),
            ): row
            for row in rows
        }
        for index, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            print(
                f"[{index:>2}/{len(rows)}] {result.status:5} {result.repository}", file=sys.stderr
            )
    results.sort(key=lambda item: item.repository.casefold())
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "method": {
            "collector": "scripts/collect_repositories.py",
            "max_files_per_repository": args.max_files,
            "max_bytes_per_repository": args.max_bytes,
            "lock_file": None if args.refresh else str(args.lock_file),
            "locked_repositories": sum(row["repository"] in commits for row in rows),
            "selection": "manifests, then security/agent/tool/MCP-related sources, then shallow paths",
        },
        "repositories": [asdict(result) for result in results],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    failures = sum(result.status != "ok" for result in results)
    print(f"Wrote {len(results)} repositories to {args.output}; failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

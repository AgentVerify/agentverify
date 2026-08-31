"""Evaluate exact hand labels against local fixtures and pinned corpus checkouts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from agentverify.benchmark import apply_label_filter, failure_summary_from_outcomes
from agentverify.scanner import scan_repository

CLAIM_SCOPE = {
    "public-regression": (
        "curated public regression metrics only; not an unbiased ecosystem accuracy estimate"
    ),
    "sealed-holdout": "sealed holdout evaluation; suitable for unbiased accuracy claims if labels remained sealed",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, default=Path("benchmarks/truthset.json"))
    parser.add_argument("--cache-dir", type=Path, default=Path(".agentverify-cache/repositories"))
    parser.add_argument("--output", type=Path, default=Path("benchmarks/truthset-results.json"))
    parser.add_argument(
        "--evaluation-kind",
        choices=tuple(CLAIM_SCOPE),
        default="public-regression",
        help="declare whether labels are public regressions or a sealed holdout",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="optional holdout/sample manifest used to create the label file",
    )
    parser.add_argument(
        "--check-id",
        action="append",
        default=[],
        help="evaluate only labels with this Agent IR check id; may be repeated",
    )
    parser.add_argument(
        "--rule-id",
        action="append",
        default=[],
        help="evaluate only labels with this reporting rule id; may be repeated",
    )
    parser.add_argument(
        "--label-id-prefix",
        action="append",
        default=[],
        help="evaluate only labels whose id starts with this prefix; may be repeated",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="print per-target scan timings to stderr without changing result JSON",
    )
    parser.add_argument(
        "--scan-label-paths",
        action="store_true",
        help=(
            "development shortcut: scan only files referenced by the evaluated labels; "
            "records selected-label-paths scan scope in result metadata"
        ),
    )
    parser.add_argument(
        "--expand-local-imports",
        action="store_true",
        help=(
            "with --scan-label-paths, also include a recursive local import/export closure "
            "from the selected label files"
        ),
    )
    return parser.parse_args(argv)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def label_scope(labels: list[dict]) -> str:
    has_rules = any("rule_id" in label for label in labels)
    has_ir = any("check_id" in label for label in labels)
    if has_rules and has_ir:
        return "mixed"
    if has_ir:
        return "agent-ir"
    return "reporting-rules"


def label_filter_from_args(args: argparse.Namespace) -> dict[str, list[str]]:
    """Return the explicit development label filter requested on the CLI."""
    label_filter: dict[str, list[str]] = {}
    if args.check_id:
        label_filter["check_ids"] = list(dict.fromkeys(args.check_id))
    if args.rule_id:
        label_filter["rule_ids"] = list(dict.fromkeys(args.rule_id))
    if args.label_id_prefix:
        label_filter["label_id_prefixes"] = list(dict.fromkeys(args.label_id_prefix))
    return label_filter


def benchmark_metadata(
    args: argparse.Namespace,
    *,
    source_labels_path: Path,
    label_filter: dict[str, list[str]],
    labels: list[dict],
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "evaluation_kind": args.evaluation_kind,
        "label_scope": label_scope(labels),
        "labels_source": str(source_labels_path),
        "labels_sha256": file_sha256(source_labels_path),
        "sealed": args.evaluation_kind == "sealed-holdout",
        "claim_scope": CLAIM_SCOPE[args.evaluation_kind],
    }
    if label_filter:
        metadata["label_filter"] = label_filter
    if args.scan_label_paths:
        metadata["scan_scope"] = "selected-label-paths"
        if args.expand_local_imports:
            metadata["scan_path_expansion"] = "local-import-closure"
    if args.manifest is not None:
        metadata["manifest_source"] = str(args.manifest)
        metadata["manifest_sha256"] = file_sha256(args.manifest)
    return metadata


PYTHON_SUFFIXES = (".py",)
TYPESCRIPT_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
SOURCE_SUFFIXES = set(PYTHON_SUFFIXES + TYPESCRIPT_SUFFIXES)


def local_module_candidates(base: Path, *, suffixes: Iterable[str]) -> Iterable[Path]:
    """Yield existing local source module files for an import target base path."""
    suffix_list = tuple(suffixes)
    if base.suffix in suffix_list and base.is_file():
        yield base
    for suffix in suffix_list:
        candidate = base.with_suffix(suffix)
        if candidate.is_file():
            yield candidate
    for suffix in suffix_list:
        candidate = base / f"__init__{suffix}" if suffix == ".py" else base / f"index{suffix}"
        if candidate.is_file():
            yield candidate


def _relative_source_path(root: Path, candidate: Path) -> str | None:
    try:
        relative = candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    if not candidate.is_file() or candidate.suffix not in SOURCE_SUFFIXES:
        return None
    return relative.as_posix()


def typescript_local_imports(root: Path, relative_path: str, text: str) -> set[str]:
    imports: set[str] = set()
    parent = (root / relative_path).parent
    patterns = (
        r"\b(?:import|export)\b[^;\n]*?\bfrom\s*[\"']([^\"']+)[\"']",
        r"\bimport\s*[\"']([^\"']+)[\"']",
        r"\bimport\s*\(\s*[\"']([^\"']+)[\"']\s*\)",
        r"\brequire\s*\(\s*[\"']([^\"']+)[\"']\s*\)",
    )
    for pattern in patterns:
        for specifier in re.findall(pattern, text):
            if not specifier.startswith("."):
                continue
            base = (parent / specifier).resolve()
            for candidate in local_module_candidates(base, suffixes=TYPESCRIPT_SUFFIXES):
                if relative := _relative_source_path(root, candidate):
                    imports.add(relative)
    return imports


def python_relative_base(path: Path, dots: int) -> Path | None:
    base = path.parent
    for _ in range(max(dots - 1, 0)):
        parent = base.parent
        if parent == base:
            return None
        base = parent
    return base


def python_local_imports(root: Path, relative_path: str, text: str) -> set[str]:
    imports: set[str] = set()
    path = root / relative_path
    for match in re.finditer(r"(?m)^\s*from\s+([.\w]+)\s+import\s+([^\n#]+)", text):
        module, imported_names = match.groups()
        imported = [
            name.strip().split(" as ", 1)[0]
            for name in imported_names.strip("() ").split(",")
            if name.strip() and name.strip() != "*"
        ]
        if module.startswith("."):
            dots = len(module) - len(module.lstrip("."))
            base = python_relative_base(path, dots)
            if base is None:
                continue
            module_tail = module[dots:].replace(".", "/")
            module_base = base / module_tail if module_tail else base
        else:
            module_base = root / module.replace(".", "/")
        for candidate in local_module_candidates(module_base, suffixes=PYTHON_SUFFIXES):
            if relative := _relative_source_path(root, candidate):
                imports.add(relative)
        for name in imported:
            if not name.isidentifier():
                continue
            for candidate in local_module_candidates(module_base / name, suffixes=PYTHON_SUFFIXES):
                if relative := _relative_source_path(root, candidate):
                    imports.add(relative)

    for match in re.finditer(r"(?m)^\s*import\s+([^\n#]+)", text):
        for module in match.group(1).split(","):
            name = module.strip().split(" as ", 1)[0]
            if not name or name.startswith("."):
                continue
            for candidate in local_module_candidates(
                root / name.replace(".", "/"), suffixes=PYTHON_SUFFIXES
            ):
                if relative := _relative_source_path(root, candidate):
                    imports.add(relative)
    return imports


def expand_selected_paths_with_local_imports(root: Path, selected_paths: set[str]) -> set[str]:
    """Return selected label paths plus recursive local Python/TS import/export dependencies."""
    expanded = set(selected_paths)
    queue = sorted(selected_paths)
    while queue:
        relative_path = queue.pop(0)
        path = root / relative_path
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        if path.suffix == ".py":
            discovered = python_local_imports(root, relative_path, text)
        elif path.suffix in TYPESCRIPT_SUFFIXES:
            discovered = typescript_local_imports(root, relative_path, text)
        else:
            discovered = set()
        for relative in sorted(discovered - expanded):
            expanded.add(relative)
            queue.append(relative)
    return expanded


def target_path(target: dict, cache_dir: Path) -> Path:
    if target["kind"] == "local":
        return Path(target["path"])
    return cache_dir / target["repository"].replace("/", "--")


def path_from_symbol_id(symbol_id: str | None) -> str | None:
    """Extract the source-relative file path from AgentVerify source symbol ids."""
    if symbol_id is None or ":" not in symbol_id or "#" not in symbol_id:
        return None
    frontend, rest = symbol_id.split(":", 1)
    if frontend not in {"py", "ts"}:
        return None
    path = rest.split("#", 1)[0]
    return path or None


def verify_commit(path: Path, target: dict) -> None:
    if target["kind"] != "repository":
        return
    actual = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    if actual != target["commit"]:
        raise RuntimeError(f"{target['repository']}: expected {target['commit']}, found {actual}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.expand_local_imports and not args.scan_label_paths:
        print("agentverify: --expand-local-imports requires --scan-label-paths", file=sys.stderr)
        return 2
    label_filter = label_filter_from_args(args)
    all_labels = json.loads(args.labels.read_text(encoding="utf-8"))["labels"]
    labels = apply_label_filter(all_labels, label_filter)
    target_label_counts = Counter(json.dumps(label["target"], sort_keys=True) for label in labels)
    target_label_paths: dict[str, set[str]] = defaultdict(set)
    for label in labels:
        key = json.dumps(label["target"], sort_keys=True)
        target_label_paths[key].add(label["path"])
        if relationship := label.get("relationship"):
            for symbol_key in ("source_id", "target_id"):
                if path := path_from_symbol_id(relationship.get(symbol_key)):
                    target_label_paths[key].add(path)
        if (component := label.get("component")) and (
            path := path_from_symbol_id(component.get("symbol_id"))
        ):
            target_label_paths[key].add(path)
    scans = {}
    outcomes = []
    matrices: dict[str, Counter] = defaultdict(Counter)
    for label in labels:
        target = label["target"]
        path = target_path(target, args.cache_dir)
        key = json.dumps(target, sort_keys=True)
        if key not in scans:
            started = time.perf_counter()
            verify_commit(path, target)
            selected_paths = (
                sorted(target_label_paths[key]) if args.scan_label_paths else None
            )
            if selected_paths is not None and args.expand_local_imports:
                selected_paths = sorted(
                    expand_selected_paths_with_local_imports(path, set(selected_paths))
                )
            if selected_paths is None:
                scans[key] = scan_repository(path)
            else:
                scans[key] = scan_repository(path, selected_paths=selected_paths)
            if args.progress:
                elapsed = time.perf_counter() - started
                print(
                    "agentverify: scanned "
                    f"{path} labels={target_label_counts[key]} seconds={elapsed:.3f}",
                    file=sys.stderr,
                )
        ir = scans[key]
        metric_id = label.get("rule_id") or label["check_id"]
        if relationship := label.get("relationship"):
            observed = any(
                edge.evidence.path == label["path"]
                and edge.evidence.line == label["line"]
                and all(
                    (
                        all(
                            edge.attributes.get(name) == expected
                            for name, expected in value.items()
                        )
                        if key == "attributes"
                        else getattr(edge, key) == value
                    )
                    for key, value in relationship.items()
                )
                for edge in ir.relationships
            )
        elif component := label.get("component"):
            observed = any(
                item.evidence.path == label["path"]
                and item.evidence.line == label["line"]
                and all(
                    (
                        all(
                            item.attributes.get(name) == expected
                            for name, expected in value.items()
                        )
                        if key == "attributes"
                        else getattr(item, key) == value
                    )
                    for key, value in component.items()
                )
                for item in ir.components
            )
        else:
            observed = any(
                finding.rule_id == label["rule_id"]
                and finding.evidence.path == label["path"]
                and finding.evidence.line == label["line"]
                for finding in ir.findings
            )
        anchor_ok = True
        if anchor := label.get("anchor"):
            anchor_ok = any(
                component.kind == anchor["kind"]
                and component.name == anchor["name"]
                and component.evidence.path == label["path"]
                and component.evidence.line == label["line"]
                and all(
                    component.attributes.get(name) == expected
                    for name, expected in anchor.get("attributes", {}).items()
                )
                for component in ir.components
            )
        source_ok = True
        if source_contains := label.get("source_contains"):
            source_path = path / label["path"]
            source_lines = source_path.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
            line_index = label["line"] - 1
            source_ok = (
                0 <= line_index < len(source_lines) and source_contains in source_lines[line_index]
            )
        expected = bool(label["expected"])
        bucket = "tp" if expected and observed else "fn" if expected else "fp" if observed else "tn"
        matrices[metric_id][bucket] += 1
        outcome = {"id": label["id"]}
        outcome["rule_id" if label.get("rule_id") else "check_id"] = metric_id
        outcome.update(
            {
                "expected": expected,
                "observed": observed,
                "anchor_ok": anchor_ok,
                "source_ok": source_ok,
                "passed": observed == expected and anchor_ok and source_ok,
            }
        )
        outcomes.append(outcome)
    metrics = {}
    for rule_id, matrix in sorted(matrices.items()):
        tp, fp, fn = matrix["tp"], matrix["fp"], matrix["fn"]
        metrics[rule_id] = {
            **{name: matrix[name] for name in ("tp", "fp", "tn", "fn")},
            "precision": round(tp / (tp + fp), 4) if tp + fp else None,
            "recall": round(tp / (tp + fn), 4) if tp + fn else None,
        }
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "benchmark": benchmark_metadata(
            args,
            source_labels_path=args.labels,
            label_filter=label_filter,
            labels=labels,
        ),
        "labels": len(labels),
        "passed": sum(item["passed"] for item in outcomes),
        "failed": sum(not item["passed"] for item in outcomes),
        "all_labels_passed": all(item["passed"] for item in outcomes),
        "failure_summary": failure_summary_from_outcomes(outcomes),
        "metrics": metrics,
        "outcomes": outcomes,
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: payload[key]
                for key in (
                    "benchmark",
                    "labels",
                    "passed",
                    "failed",
                    "all_labels_passed",
                    "failure_summary",
                    "metrics",
                )
            },
            indent=2,
        )
    )
    return 0 if payload["passed"] == payload["labels"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

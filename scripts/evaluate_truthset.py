"""Evaluate exact hand labels against local fixtures and pinned corpus checkouts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from agentverify.benchmark import failure_summary_from_outcomes
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


def benchmark_metadata(args: argparse.Namespace, labels: list[dict]) -> dict[str, object]:
    metadata: dict[str, object] = {
        "evaluation_kind": args.evaluation_kind,
        "label_scope": label_scope(labels),
        "labels_source": str(args.labels),
        "labels_sha256": file_sha256(args.labels),
        "sealed": args.evaluation_kind == "sealed-holdout",
        "claim_scope": CLAIM_SCOPE[args.evaluation_kind],
    }
    if args.manifest is not None:
        metadata["manifest_source"] = str(args.manifest)
        metadata["manifest_sha256"] = file_sha256(args.manifest)
    return metadata


def target_path(target: dict, cache_dir: Path) -> Path:
    if target["kind"] == "local":
        return Path(target["path"])
    return cache_dir / target["repository"].replace("/", "--")


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
    labels = json.loads(args.labels.read_text(encoding="utf-8"))["labels"]
    scans = {}
    outcomes = []
    matrices: dict[str, Counter] = defaultdict(Counter)
    for label in labels:
        target = label["target"]
        path = target_path(target, args.cache_dir)
        key = json.dumps(target, sort_keys=True)
        if key not in scans:
            verify_commit(path, target)
            scans[key] = scan_repository(path)
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
        "benchmark": benchmark_metadata(args, labels),
        "labels": len(labels),
        "passed": sum(item["passed"] for item in outcomes),
        "failed": sum(not item["passed"] for item in outcomes),
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

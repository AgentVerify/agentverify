"""Benchmark result verification helpers for AgentVerify release workflows."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from .report import render_schema

DEFAULT_BENCHMARK_RESULTS = (
    Path("benchmarks/truthset-results.json"),
    Path("benchmarks/ir-truthset-results.json"),
)
BENCHMARK_VERIFICATION_ERRORS = (
    OSError,
    RuntimeError,
    json.JSONDecodeError,
    SchemaError,
    ValidationError,
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_source(root: Path, source: str) -> Path:
    path = Path(source)
    return path if path.is_absolute() else root / path


def load_benchmark_result_schema(path: Path | None = None) -> dict:
    if path is None:
        schema = json.loads(render_schema("benchmark-result"))
    else:
        schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def outcome_metric_id(outcome: dict) -> str:
    return outcome.get("rule_id") or outcome["check_id"]


def label_metric_id(label: dict) -> str:
    return label.get("rule_id") or label["check_id"]


def label_metric_kind(label: dict) -> str:
    return "rule_id" if label.get("rule_id") else "check_id"


def label_scope(labels: list[dict]) -> str:
    has_rules = any("rule_id" in label for label in labels)
    has_ir = any("check_id" in label for label in labels)
    if has_rules and has_ir:
        return "mixed"
    if has_ir:
        return "agent-ir"
    return "reporting-rules"


def label_matches_filter(label: dict, label_filter: dict[str, list[str]]) -> bool:
    """Return whether a label is included by an optional benchmark label filter."""
    check_ids = label_filter.get("check_ids", [])
    if check_ids and label.get("check_id") not in check_ids:
        return False
    rule_ids = label_filter.get("rule_ids", [])
    if rule_ids and label.get("rule_id") not in rule_ids:
        return False
    label_id_prefixes = label_filter.get("label_id_prefixes", [])
    return not label_id_prefixes or any(
        label["id"].startswith(prefix) for prefix in label_id_prefixes
    )


def apply_label_filter(labels: list[dict], label_filter: dict | None) -> list[dict]:
    """Apply the benchmark-result label filter recorded in metadata."""
    if not label_filter:
        return labels
    normalized = {
        "check_ids": list(label_filter.get("check_ids", [])),
        "rule_ids": list(label_filter.get("rule_ids", [])),
        "label_id_prefixes": list(label_filter.get("label_id_prefixes", [])),
    }
    return [label for label in labels if label_matches_filter(label, normalized)]


def metrics_from_outcomes(outcomes: list[dict]) -> dict[str, dict[str, object]]:
    matrices: dict[str, Counter] = defaultdict(Counter)
    for outcome in outcomes:
        metric_id = outcome_metric_id(outcome)
        expected = outcome["expected"]
        observed = outcome["observed"]
        bucket = "tp" if expected and observed else "fn" if expected else "fp" if observed else "tn"
        matrices[metric_id][bucket] += 1

    metrics: dict[str, dict[str, object]] = {}
    for metric_id, matrix in sorted(matrices.items()):
        tp = matrix["tp"]
        fp = matrix["fp"]
        fn = matrix["fn"]
        metrics[metric_id] = {
            **{name: matrix[name] for name in ("tp", "fp", "tn", "fn")},
            "precision": round(tp / (tp + fp), 4) if tp + fp else None,
            "recall": round(tp / (tp + fn), 4) if tp + fn else None,
        }
    return metrics


def failure_summary_from_outcomes(outcomes: list[dict]) -> dict[str, int]:
    """Return explicit counts for every reason a benchmark outcome did not pass."""
    summary = Counter(
        reason
        for outcome in outcomes
        for reason in (
            (
                "observation_mismatch"
                if outcome["observed"] != outcome["expected"]
                else None
            ),
            "anchor_mismatch" if outcome["anchor_ok"] is not True else None,
            "source_mismatch" if outcome["source_ok"] is not True else None,
        )
        if reason is not None
    )
    return {
        "observation_mismatch": summary["observation_mismatch"],
        "anchor_mismatch": summary["anchor_mismatch"],
        "source_mismatch": summary["source_mismatch"],
    }


def verify_result_invariants(path: Path, payload: dict, labels: list[dict]) -> None:
    outcomes = payload["outcomes"]
    if len(outcomes) != payload["labels"]:
        raise RuntimeError(f"{path}: outcomes count does not match labels")

    declared_scope = payload["benchmark"]["label_scope"]
    actual_scope = label_scope(labels)
    if declared_scope != actual_scope:
        raise RuntimeError(
            f"{path}: label_scope {declared_scope} does not match labels ({actual_scope})"
        )

    for index, (label, outcome) in enumerate(zip(labels, outcomes, strict=True), start=1):
        metric_kind = label_metric_kind(label)
        expected = {
            "id": label["id"],
            metric_kind: label_metric_id(label),
            "expected": bool(label["expected"]),
        }
        actual = {
            "id": outcome["id"],
            metric_kind: outcome.get(metric_kind),
            "expected": outcome["expected"],
        }
        if actual != expected:
            raise RuntimeError(f"{path}: outcome {index} does not match label {label['id']}")

    passed = sum(1 for outcome in outcomes if outcome["passed"])
    if passed != payload["passed"]:
        raise RuntimeError(f"{path}: passed count does not match outcomes")

    failed = len(outcomes) - passed
    if failed != payload["failed"]:
        raise RuntimeError(f"{path}: failed count does not match outcomes")

    failure_summary = failure_summary_from_outcomes(outcomes)
    if failure_summary != payload["failure_summary"]:
        raise RuntimeError(f"{path}: failure_summary does not match outcomes")

    metrics = metrics_from_outcomes(outcomes)
    if metrics != payload["metrics"]:
        raise RuntimeError(f"{path}: metrics do not match outcomes")


def verify_result(path: Path, *, schema: dict, root: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)
    benchmark = payload["benchmark"]
    labels_path = resolve_source(root, benchmark["labels_source"])
    labels_payload = json.loads(labels_path.read_text(encoding="utf-8"))
    labels = labels_payload.get("labels", [])
    if file_sha256(labels_path) != benchmark["labels_sha256"]:
        raise RuntimeError(f"{path}: labels_sha256 does not match {labels_path}")
    labels = apply_label_filter(labels, benchmark.get("label_filter"))
    if len(labels) != payload["labels"]:
        raise RuntimeError(f"{path}: labels count does not match {labels_path}")
    verify_result_invariants(path, payload, labels)
    manifest_source = benchmark.get("manifest_source")
    if manifest_source:
        manifest_path = resolve_source(root, manifest_source)
        if file_sha256(manifest_path) != benchmark["manifest_sha256"]:
            raise RuntimeError(f"{path}: manifest_sha256 does not match {manifest_path}")
    result = {
        "result": str(path),
        "evaluation_kind": benchmark["evaluation_kind"],
        "label_scope": benchmark["label_scope"],
        "sealed": benchmark["sealed"],
        "labels": payload["labels"],
        "passed": payload["passed"],
        "failed": payload["failed"],
        "failure_summary": payload["failure_summary"],
        "labels_source": str(labels_path),
        "claim_scope": benchmark["claim_scope"],
        "digest_ok": True,
    }
    if scan_scope := benchmark.get("scan_scope"):
        result["scan_scope"] = scan_scope
    return result


def enforce_release_requirements(
    result: dict[str, object],
    *,
    evaluation_kind: str | None,
    label_scope: str | None,
    require_sealed: bool,
    require_manifest: bool,
    require_all_passed: bool,
    payload: dict,
) -> None:
    if evaluation_kind is not None and result["evaluation_kind"] != evaluation_kind:
        raise RuntimeError(
            f"{result['result']}: expected evaluation_kind {evaluation_kind}, "
            f"found {result['evaluation_kind']}"
        )
    if label_scope is not None and result["label_scope"] != label_scope:
        raise RuntimeError(
            f"{result['result']}: expected label_scope {label_scope}, found {result['label_scope']}"
        )
    if require_sealed and result["sealed"] is not True:
        raise RuntimeError(f"{result['result']}: expected sealed benchmark result")
    if require_manifest and "manifest_source" not in payload["benchmark"]:
        raise RuntimeError(f"{result['result']}: expected manifest_source")
    if require_all_passed and result["passed"] != result["labels"]:
        raise RuntimeError(
            f"{result['result']}: expected all benchmark labels to pass, "
            f"found {result['passed']} passed of {result['labels']}"
        )


def verify_result_for_release(
    path: Path,
    *,
    schema: dict,
    root: Path,
    evaluation_kind: str | None = None,
    label_scope: str | None = None,
    require_sealed: bool = False,
    require_manifest: bool = False,
    require_all_passed: bool = False,
) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = verify_result(path, schema=schema, root=root)
    enforce_release_requirements(
        result,
        evaluation_kind=evaluation_kind,
        label_scope=label_scope,
        require_sealed=require_sealed,
        require_manifest=require_manifest,
        require_all_passed=require_all_passed,
        payload=payload,
    )
    return result


def verify_benchmark_results(
    results: list[Path] | tuple[Path, ...] = DEFAULT_BENCHMARK_RESULTS,
    *,
    schema_path: Path | None = None,
    root: Path = Path("."),
    evaluation_kind: str | None = None,
    label_scope: str | None = None,
    require_sealed: bool = False,
    require_manifest: bool = False,
    require_all_passed: bool = False,
) -> dict[str, object]:
    schema = load_benchmark_result_schema(schema_path)
    verification_schema = json.loads(render_schema("benchmark-verification"))
    Draft202012Validator.check_schema(verification_schema)
    verified = [
        verify_result_for_release(
            path,
            schema=schema,
            root=root,
            evaluation_kind=evaluation_kind,
            label_scope=label_scope,
            require_sealed=require_sealed,
            require_manifest=require_manifest,
            require_all_passed=require_all_passed,
        )
        for path in results
    ]
    payload: dict[str, object] = {
        "results": verified,
        "passed": True,
        "all_labels_passed": all(item["passed"] == item["labels"] for item in verified),
    }
    Draft202012Validator(verification_schema).validate(payload)
    return payload


def render_benchmark_verification(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2) + "\n"

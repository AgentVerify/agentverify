from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_benchmark_results", ROOT / "scripts/verify_benchmark_results.py"
)
assert SPEC is not None
verify_benchmark_results = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(verify_benchmark_results)


def write_labels(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "labels": [
                    {
                        "id": "label-1",
                        "target": {"kind": "local", "path": "case"},
                        "rule_id": "AV-EXEC001",
                        "path": "agent.py",
                        "line": 1,
                        "expected": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def write_result(path: Path, labels: Path, *, labels_sha256: str | None = None) -> None:
    digest = labels_sha256 or verify_benchmark_results.file_sha256(labels)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-08-26T00:00:00+00:00",
                "benchmark": {
                    "evaluation_kind": "public-regression",
                    "label_scope": "reporting-rules",
                    "labels_source": str(labels),
                    "labels_sha256": digest,
                    "sealed": False,
                    "claim_scope": (
                        "curated public regression metrics only; "
                        "not an unbiased ecosystem accuracy estimate"
                    ),
                },
                "labels": 1,
                "passed": 1,
                "metrics": {
                    "AV-EXEC001": {
                        "tp": 1,
                        "fp": 0,
                        "tn": 0,
                        "fn": 0,
                        "precision": 1.0,
                        "recall": 1.0,
                    }
                },
                "outcomes": [
                    {
                        "id": "label-1",
                        "rule_id": "AV-EXEC001",
                        "expected": True,
                        "observed": True,
                        "anchor_ok": True,
                        "source_ok": True,
                        "passed": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_checked_in_benchmark_results_verify() -> None:
    assert verify_benchmark_results.main([]) == 0


def test_benchmark_result_verifier_checks_label_digest(tmp_path: Path) -> None:
    labels = tmp_path / "labels.json"
    result = tmp_path / "results.json"
    write_labels(labels)
    write_result(result, labels)
    schema = ROOT / "benchmarks/benchmark-results-v1.schema.json"

    assert (
        verify_benchmark_results.main(
            [str(result), "--schema", str(schema), "--root", str(tmp_path)]
        )
        == 0
    )

    write_result(result, labels, labels_sha256="0" * 64)
    with pytest.raises(RuntimeError, match="labels_sha256"):
        verify_benchmark_results.verify_result(
            result,
            schema=verify_benchmark_results.load_schema(schema),
            root=tmp_path,
        )

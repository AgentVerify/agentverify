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


def write_result(
    path: Path,
    labels: Path,
    *,
    labels_sha256: str | None = None,
    evaluation_kind: str = "public-regression",
    manifest: Path | None = None,
    passed: bool = True,
) -> None:
    digest = labels_sha256 or verify_benchmark_results.file_sha256(labels)
    failure_summary = {
        "observation_mismatch": 0 if passed else 1,
        "anchor_mismatch": 0,
        "source_mismatch": 0,
    }
    benchmark = {
        "evaluation_kind": evaluation_kind,
        "label_scope": "reporting-rules",
        "labels_source": str(labels),
        "labels_sha256": digest,
        "sealed": evaluation_kind == "sealed-holdout",
        "claim_scope": (
            "sealed holdout evaluation; suitable for unbiased accuracy claims if labels remained sealed"
            if evaluation_kind == "sealed-holdout"
            else "curated public regression metrics only; "
            "not an unbiased ecosystem accuracy estimate"
        ),
    }
    if manifest is not None:
        benchmark["manifest_source"] = str(manifest)
        benchmark["manifest_sha256"] = verify_benchmark_results.file_sha256(manifest)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-08-26T00:00:00+00:00",
                "benchmark": benchmark,
                "labels": 1,
                "passed": 1 if passed else 0,
                "failed": 0 if passed else 1,
                "failure_summary": failure_summary,
                "metrics": {
                    "AV-EXEC001": {
                        "tp": 1 if passed else 0,
                        "fp": 0,
                        "tn": 0,
                        "fn": 0 if passed else 1,
                        "precision": 1.0 if passed else None,
                        "recall": 1.0 if passed else 0.0,
                    }
                },
                "outcomes": [
                    {
                        "id": "label-1",
                        "rule_id": "AV-EXEC001",
                        "expected": True,
                        "observed": passed,
                        "anchor_ok": True,
                        "source_ok": True,
                        "passed": passed,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def rewrite_result(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


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


def test_benchmark_result_verifier_rejects_label_scope_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    labels = tmp_path / "labels.json"
    result = tmp_path / "results.json"
    write_labels(labels)
    write_result(result, labels)
    schema = ROOT / "benchmarks/benchmark-results-v1.schema.json"
    payload = json.loads(result.read_text(encoding="utf-8"))
    payload["benchmark"]["label_scope"] = "agent-ir"
    rewrite_result(result, payload)

    assert (
        verify_benchmark_results.main(
            [str(result), "--schema", str(schema), "--root", str(tmp_path)]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "label_scope agent-ir does not match labels (reporting-rules)" in captured.err


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "other-label"),
        ("rule_id", "AV-OTHER"),
        ("expected", False),
    ],
)
def test_benchmark_result_verifier_rejects_outcome_label_drift(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    field: str,
    value: object,
) -> None:
    labels = tmp_path / "labels.json"
    result = tmp_path / "results.json"
    write_labels(labels)
    write_result(result, labels)
    schema = ROOT / "benchmarks/benchmark-results-v1.schema.json"
    payload = json.loads(result.read_text(encoding="utf-8"))
    payload["outcomes"][0][field] = value
    rewrite_result(result, payload)

    assert (
        verify_benchmark_results.main(
            [str(result), "--schema", str(schema), "--root", str(tmp_path)]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "outcome 1 does not match label label-1" in captured.err


def test_benchmark_result_verifier_reports_but_allows_failing_labels_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    labels = tmp_path / "labels.json"
    result = tmp_path / "results.json"
    write_labels(labels)
    write_result(result, labels, passed=False)
    schema = ROOT / "benchmarks/benchmark-results-v1.schema.json"

    assert (
        verify_benchmark_results.main(
            [str(result), "--schema", str(schema), "--root", str(tmp_path)]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is True
    assert payload["all_labels_passed"] is False
    assert payload["results"][0]["passed"] == 0
    assert payload["results"][0]["failed"] == 1
    assert payload["results"][0]["all_labels_passed"] is False
    assert payload["results"][0]["failure_summary"] == {
        "observation_mismatch": 1,
        "anchor_mismatch": 0,
        "source_mismatch": 0,
    }


def test_benchmark_result_verifier_can_require_all_labels_passed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    labels = tmp_path / "labels.json"
    result = tmp_path / "results.json"
    write_labels(labels)
    write_result(result, labels, passed=False)
    schema = ROOT / "benchmarks/benchmark-results-v1.schema.json"

    assert (
        verify_benchmark_results.main(
            [
                str(result),
                "--schema",
                str(schema),
                "--root",
                str(tmp_path),
                "--require-all-passed",
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "expected all benchmark labels to pass" in captured.err


def test_benchmark_result_verifier_reports_per_result_all_labels_passed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
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
    payload = json.loads(capsys.readouterr().out)
    assert payload["all_labels_passed"] is True
    assert payload["results"][0]["all_labels_passed"] is True


def test_benchmark_result_verifier_rejects_outcome_count_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    labels = tmp_path / "labels.json"
    result = tmp_path / "results.json"
    write_labels(labels)
    write_result(result, labels)
    schema = ROOT / "benchmarks/benchmark-results-v1.schema.json"
    payload = json.loads(result.read_text(encoding="utf-8"))
    payload["outcomes"] = []
    payload["passed"] = 0
    payload["metrics"] = {}
    rewrite_result(result, payload)

    assert (
        verify_benchmark_results.main(
            [str(result), "--schema", str(schema), "--root", str(tmp_path)]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "outcomes count does not match labels" in captured.err


def test_benchmark_result_verifier_rejects_passed_count_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    labels = tmp_path / "labels.json"
    result = tmp_path / "results.json"
    write_labels(labels)
    write_result(result, labels, passed=False)
    schema = ROOT / "benchmarks/benchmark-results-v1.schema.json"
    payload = json.loads(result.read_text(encoding="utf-8"))
    payload["passed"] = 1
    rewrite_result(result, payload)

    assert (
        verify_benchmark_results.main(
            [str(result), "--schema", str(schema), "--root", str(tmp_path)]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "passed count does not match outcomes" in captured.err


def test_benchmark_result_verifier_rejects_all_labels_passed_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    labels = tmp_path / "labels.json"
    result = tmp_path / "results.json"
    write_labels(labels)
    write_result(result, labels)
    schema = ROOT / "benchmarks/benchmark-results-v1.schema.json"
    payload = json.loads(result.read_text(encoding="utf-8"))
    payload["all_labels_passed"] = False
    rewrite_result(result, payload)

    assert (
        verify_benchmark_results.main(
            [str(result), "--schema", str(schema), "--root", str(tmp_path)]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "all_labels_passed does not match outcomes" in captured.err


def test_benchmark_result_verifier_rejects_failed_count_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    labels = tmp_path / "labels.json"
    result = tmp_path / "results.json"
    write_labels(labels)
    write_result(result, labels, passed=False)
    schema = ROOT / "benchmarks/benchmark-results-v1.schema.json"
    payload = json.loads(result.read_text(encoding="utf-8"))
    payload["failed"] = 0
    rewrite_result(result, payload)

    assert (
        verify_benchmark_results.main(
            [str(result), "--schema", str(schema), "--root", str(tmp_path)]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "failed count does not match outcomes" in captured.err


def test_benchmark_result_verifier_rejects_failure_summary_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    labels = tmp_path / "labels.json"
    result = tmp_path / "results.json"
    write_labels(labels)
    write_result(result, labels, passed=False)
    schema = ROOT / "benchmarks/benchmark-results-v1.schema.json"
    payload = json.loads(result.read_text(encoding="utf-8"))
    payload["failure_summary"]["observation_mismatch"] = 0
    rewrite_result(result, payload)

    assert (
        verify_benchmark_results.main(
            [str(result), "--schema", str(schema), "--root", str(tmp_path)]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "failure_summary does not match outcomes" in captured.err


def test_benchmark_result_verifier_rejects_metric_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    labels = tmp_path / "labels.json"
    result = tmp_path / "results.json"
    write_labels(labels)
    write_result(result, labels)
    schema = ROOT / "benchmarks/benchmark-results-v1.schema.json"
    payload = json.loads(result.read_text(encoding="utf-8"))
    payload["metrics"]["AV-EXEC001"]["tp"] = 0
    payload["metrics"]["AV-EXEC001"]["fn"] = 1
    payload["metrics"]["AV-EXEC001"]["precision"] = None
    payload["metrics"]["AV-EXEC001"]["recall"] = 0.0
    rewrite_result(result, payload)

    assert (
        verify_benchmark_results.main(
            [str(result), "--schema", str(schema), "--root", str(tmp_path)]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "metrics do not match outcomes" in captured.err


def test_benchmark_result_verifier_accepts_sealed_release_requirements(tmp_path: Path) -> None:
    labels = tmp_path / "labels.json"
    manifest = tmp_path / "manifest.json"
    result = tmp_path / "results.json"
    write_labels(labels)
    manifest.write_text('{"schema_version":1,"samples":[]}', encoding="utf-8")
    write_result(result, labels, evaluation_kind="sealed-holdout", manifest=manifest)
    schema = ROOT / "benchmarks/benchmark-results-v1.schema.json"

    assert (
        verify_benchmark_results.main(
            [
                str(result),
                "--schema",
                str(schema),
                "--root",
                str(tmp_path),
                "--require-evaluation-kind",
                "sealed-holdout",
                "--require-label-scope",
                "reporting-rules",
                "--require-sealed",
                "--require-manifest",
            ]
        )
        == 0
    )


def test_benchmark_result_verifier_rejects_public_results_as_sealed_release_claim(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    labels = tmp_path / "labels.json"
    result = tmp_path / "results.json"
    write_labels(labels)
    write_result(result, labels)
    schema = ROOT / "benchmarks/benchmark-results-v1.schema.json"

    assert (
        verify_benchmark_results.main(
            [
                str(result),
                "--schema",
                str(schema),
                "--root",
                str(tmp_path),
                "--require-evaluation-kind",
                "sealed-holdout",
                "--require-sealed",
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "expected evaluation_kind sealed-holdout" in captured.err


def test_benchmark_result_verifier_can_require_manifest(tmp_path: Path, capsys) -> None:
    labels = tmp_path / "labels.json"
    result = tmp_path / "results.json"
    write_labels(labels)
    write_result(result, labels, evaluation_kind="sealed-holdout")
    schema = ROOT / "benchmarks/benchmark-results-v1.schema.json"

    assert (
        verify_benchmark_results.main(
            [
                str(result),
                "--schema",
                str(schema),
                "--root",
                str(tmp_path),
                "--require-manifest",
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "expected manifest_source" in captured.err

    write_result(result, labels, labels_sha256="0" * 64)
    with pytest.raises(RuntimeError, match="labels_sha256"):
        verify_benchmark_results.verify_result(
            result,
            schema=verify_benchmark_results.load_schema(schema),
            root=tmp_path,
        )

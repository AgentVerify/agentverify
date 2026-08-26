from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "evaluate_truthset", ROOT / "scripts/evaluate_truthset.py"
)
assert SPEC is not None
evaluate_truthset = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(evaluate_truthset)


def benchmark_results_schema() -> dict:
    schema = json.loads(
        (ROOT / "benchmarks/benchmark-results-v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    return schema


def test_evaluator_marks_public_regression_metrics(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / "agent.py").write_text(
        "import subprocess\n\ndef run(command):\n    subprocess.run(command, shell=True)\n",
        encoding="utf-8",
    )
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "labels": [
                    {
                        "id": "local-shell",
                        "target": {"kind": "local", "path": str(target)},
                        "rule_id": "AV-EXEC001",
                        "path": "agent.py",
                        "line": 4,
                        "expected": True,
                        "source_contains": "subprocess.run(command, shell=True)",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "results.json"

    assert evaluate_truthset.main(["--labels", str(labels), "--output", str(output)]) == 0

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["benchmark"]["evaluation_kind"] == "public-regression"
    assert result["benchmark"]["label_scope"] == "reporting-rules"
    assert result["benchmark"]["sealed"] is False
    assert result["benchmark"]["labels_source"] == str(labels)
    assert len(result["benchmark"]["labels_sha256"]) == 64
    assert "not an unbiased ecosystem accuracy estimate" in result["benchmark"]["claim_scope"]
    assert result["passed"] == 1
    assert result["failed"] == 0
    assert result["failure_summary"] == {
        "observation_mismatch": 0,
        "anchor_mismatch": 0,
        "source_mismatch": 0,
    }
    assert result["metrics"]["AV-EXEC001"]["tp"] == 1
    assert "public-regression" in capsys.readouterr().out
    Draft202012Validator(benchmark_results_schema()).validate(result)


def test_evaluator_reports_source_anchor_failures_separately(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / "agent.py").write_text(
        "import subprocess\n\ndef run(command):\n    subprocess.run(command, shell=True)\n",
        encoding="utf-8",
    )
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "labels": [
                    {
                        "id": "local-shell",
                        "target": {"kind": "local", "path": str(target)},
                        "rule_id": "AV-EXEC001",
                        "path": "agent.py",
                        "line": 4,
                        "expected": True,
                        "source_contains": "subprocess.Popen(",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "results.json"

    assert evaluate_truthset.main(["--labels", str(labels), "--output", str(output)]) == 1

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["passed"] == 0
    assert result["failed"] == 1
    assert result["failure_summary"] == {
        "observation_mismatch": 0,
        "anchor_mismatch": 0,
        "source_mismatch": 1,
    }
    assert result["metrics"]["AV-EXEC001"]["tp"] == 1
    Draft202012Validator(benchmark_results_schema()).validate(result)


def test_evaluator_marks_sealed_holdout_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / "agent.py").write_text(
        "from agents import Agent\nagent = Agent(name='x')\n", encoding="utf-8"
    )
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "labels": [
                    {
                        "id": "local-agent",
                        "target": {"kind": "local", "path": str(target)},
                        "check_id": "IR-AGENT",
                        "path": "agent.py",
                        "line": 2,
                        "expected": True,
                        "component": {"kind": "agent"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"schema_version":1,"samples":[]}', encoding="utf-8")
    output = tmp_path / "results.json"

    assert (
        evaluate_truthset.main(
            [
                "--labels",
                str(labels),
                "--output",
                str(output),
                "--evaluation-kind",
                "sealed-holdout",
                "--manifest",
                str(manifest),
            ]
        )
        == 0
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["benchmark"]["evaluation_kind"] == "sealed-holdout"
    assert result["benchmark"]["label_scope"] == "agent-ir"
    assert result["benchmark"]["sealed"] is True
    assert result["benchmark"]["manifest_source"] == str(manifest)
    assert len(result["benchmark"]["manifest_sha256"]) == 64
    Draft202012Validator(benchmark_results_schema()).validate(result)


def test_checked_in_benchmark_results_match_schema() -> None:
    schema = benchmark_results_schema()

    for path, expected_scope in (
        (ROOT / "benchmarks/truthset-results.json", "reporting-rules"),
        (ROOT / "benchmarks/ir-truthset-results.json", "agent-ir"),
    ):
        payload = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(payload)
        assert payload["benchmark"]["evaluation_kind"] == "public-regression"
        assert payload["benchmark"]["label_scope"] == expected_scope
        assert payload["benchmark"]["sealed"] is False
        assert payload["labels"] == payload["passed"]

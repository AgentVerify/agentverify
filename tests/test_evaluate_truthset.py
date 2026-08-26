from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "evaluate_truthset", ROOT / "scripts/evaluate_truthset.py"
)
assert SPEC is not None
evaluate_truthset = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(evaluate_truthset)


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
    assert result["metrics"]["AV-EXEC001"]["tp"] == 1
    assert "public-regression" in capsys.readouterr().out


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

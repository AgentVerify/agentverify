from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from agentverify import cli
from agentverify.contracts import export_editor_contracts

ROOT = Path(__file__).resolve().parents[1]


def test_editor_contract_export_writes_valid_rules_and_sample_report(tmp_path: Path) -> None:
    manifest = export_editor_contracts(
        tmp_path,
        sample_root=ROOT / "examples/safe_agent",
    )

    names = {item["path"] for item in manifest["artifacts"]}
    assert names == {
        "agentverify-report-v1.schema.json",
        "agentverify-rules-v1.schema.json",
        "agentverify-rules.json",
        "agentverify-sample-report.json",
    }
    assert {path.name for path in tmp_path.iterdir()} == names | {"manifest.json"}
    assert json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8")) == manifest

    rules_schema = json.loads((tmp_path / "agentverify-rules-v1.schema.json").read_text())
    report_schema = json.loads((tmp_path / "agentverify-report-v1.schema.json").read_text())
    Draft202012Validator.check_schema(rules_schema)
    Draft202012Validator.check_schema(report_schema)
    rules = json.loads((tmp_path / "agentverify-rules.json").read_text(encoding="utf-8"))
    report = json.loads((tmp_path / "agentverify-sample-report.json").read_text(encoding="utf-8"))
    Draft202012Validator(rules_schema).validate(rules)
    Draft202012Validator(report_schema).validate(report)

    assert rules["schema_version"] == 1
    assert len(rules["rules"]) == 24
    assert report["report_format"] == "AgentVerify JSON Report"
    assert report["schema_version"] == 1
    assert report["risk_summary"] == {"by_result_kind": {}, "by_rule": {}, "by_severity": {}}


def test_cli_exports_editor_contracts(tmp_path: Path, capsys) -> None:
    output_dir = tmp_path / "contracts"
    manifest_path = tmp_path / "manifest-copy.json"

    assert (
        cli.main(
            [
                "contracts",
                "--output-dir",
                str(output_dir),
                "--sample-root",
                str(ROOT / "examples/safe_agent"),
                "--output",
                str(manifest_path),
            ]
        )
        == 0
    )
    assert capsys.readouterr().out == ""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest == json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert {item["path"] for item in manifest["artifacts"]} == {
        "agentverify-report-v1.schema.json",
        "agentverify-rules-v1.schema.json",
        "agentverify-rules.json",
        "agentverify-sample-report.json",
    }


def test_editor_integration_docs_reference_exported_artifacts() -> None:
    docs = (ROOT / "docs/editor-integration.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "agentverify contracts" in docs
    assert "python scripts/export_editor_contracts.py" in docs
    assert "agentverify-rules.json" in docs
    assert "agentverify-report-v1.schema.json" in docs
    assert "agentverify rules --format json --output agentverify-rules.json" in docs
    assert "[`docs/editor-integration.md`](docs/editor-integration.md)" in readme

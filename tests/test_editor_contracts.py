from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from jsonschema import Draft202012Validator

from agentverify import cli
from agentverify.contracts import (
    export_editor_contracts,
    render_editor_contract_verification_summary,
    verify_editor_contracts,
)
from agentverify.report import render_json, render_sarif, render_schema
from agentverify.scanner import scan_repository

ROOT = Path(__file__).resolve().parents[1]
LSP_SEVERITY = {"high": 1, "medium": 2, "low": 3, "info": 3}


def _verify_against_verification_schema(payload: dict[str, object]) -> None:
    schema = json.loads(render_schema("editor-contract-verification"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def _editor_diagnostic(finding: dict[str, object]) -> dict[str, object]:
    evidence = finding["evidence"]
    assert isinstance(evidence, dict)
    line = evidence["line"]
    excerpt = evidence.get("excerpt", "")
    assert isinstance(line, int)
    assert isinstance(excerpt, str)
    severity = finding["severity"]
    assert isinstance(severity, str)
    return {
        "uri": evidence["path"],
        "range": {
            "start": {"line": line - 1, "character": 0},
            "end": {"line": line - 1, "character": len(excerpt)},
        },
        "severity": LSP_SEVERITY[severity],
        "code": finding["rule_id"],
        "source": "agentverify",
        "message": f"{finding['message']} Remediation: {finding['remediation']}",
        "data": {
            "fingerprint": finding["fingerprint"],
            "result_kind": finding["result_kind"],
            "confidence": finding["confidence"],
            "ir_path": finding["ir_path"],
        },
    }


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
    assert {
        item["path"]: (item["kind"], item["contract"], item["required"])
        for item in manifest["artifacts"]
    } == {
        "agentverify-report-v1.schema.json": ("schema", "report", True),
        "agentverify-rules-v1.schema.json": ("schema", "rules", True),
        "agentverify-rules.json": ("catalog", "rules", True),
        "agentverify-sample-report.json": ("sample-report", "report", False),
    }

    rules_schema = json.loads((tmp_path / "agentverify-rules-v1.schema.json").read_text())
    report_schema = json.loads((tmp_path / "agentverify-report-v1.schema.json").read_text())
    manifest_schema = json.loads(
        (ROOT / "src/agentverify/schemas/agentverify-editor-contract-manifest-v1.schema.json")
        .read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(rules_schema)
    Draft202012Validator.check_schema(report_schema)
    Draft202012Validator.check_schema(manifest_schema)
    Draft202012Validator(manifest_schema).validate(manifest)
    rules = json.loads((tmp_path / "agentverify-rules.json").read_text(encoding="utf-8"))
    report = json.loads((tmp_path / "agentverify-sample-report.json").read_text(encoding="utf-8"))
    Draft202012Validator(rules_schema).validate(rules)
    Draft202012Validator(report_schema).validate(report)

    assert rules["schema_version"] == 1
    assert len(rules["rules"]) == 25
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
    assert all({"kind", "contract", "required"} <= set(item) for item in manifest["artifacts"])


def test_editor_contract_verifier_accepts_exported_bundle(tmp_path: Path) -> None:
    export_editor_contracts(
        tmp_path,
        sample_root=ROOT / "examples/safe_agent",
    )

    verification = verify_editor_contracts(tmp_path)

    _verify_against_verification_schema(verification)
    assert verification["passed"] is True
    assert verification["manifest_schema_valid"] is True
    assert verification["required_artifacts_present"] is True
    assert verification["errors"] == []
    assert {
        item["path"]: (item["present"], item["digest_ok"], item["bytes_ok"], item["content_valid"])
        for item in verification["artifacts"]
    } == {
        "agentverify-report-v1.schema.json": (True, True, True, True),
        "agentverify-rules-v1.schema.json": (True, True, True, True),
        "agentverify-rules.json": (True, True, True, True),
        "agentverify-sample-report.json": (True, True, True, True),
    }


def test_editor_contract_verification_summary_accepts_exported_bundle(tmp_path: Path) -> None:
    export_editor_contracts(
        tmp_path,
        sample_root=ROOT / "examples/safe_agent",
    )
    verification = verify_editor_contracts(tmp_path)

    assert render_editor_contract_verification_summary(verification) == (
        "AgentVerify Editor Contract Verification\n"
        f"Directory: {tmp_path}\n"
        "Passed: true\n"
        "Manifest schema valid: true\n"
        "Required artifacts present: true\n"
        "Artifacts: 4 total (3 required)\n"
        "Artifact files: 4/4 present\n"
        "Digests: 4/4 ok\n"
        "Byte counts: 4/4 ok\n"
        "Content validation: 4/4 ok\n"
    )


def test_editor_contract_verifier_rejects_digest_drift(tmp_path: Path) -> None:
    export_editor_contracts(
        tmp_path,
        sample_root=ROOT / "examples/safe_agent",
    )
    (tmp_path / "agentverify-rules.json").write_text('{"schema_version":1,"rules":[]}\n')

    verification = verify_editor_contracts(tmp_path)

    _verify_against_verification_schema(verification)
    assert verification["passed"] is False
    rules_result = next(
        item for item in verification["artifacts"] if item["path"] == "agentverify-rules.json"
    )
    assert rules_result["present"] is True
    assert rules_result["digest_ok"] is False
    assert rules_result["bytes_ok"] is False
    assert any("artifact digest mismatch: agentverify-rules.json" in error for error in verification["errors"])


def test_editor_contract_verifier_normalizes_bad_manifest_metadata(tmp_path: Path) -> None:
    export_editor_contracts(
        tmp_path,
        sample_root=ROOT / "examples/safe_agent",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["kind"] = 123
    manifest["artifacts"][0]["contract"] = ["report"]
    manifest["artifacts"][0]["required"] = "yes"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    verification = verify_editor_contracts(tmp_path)

    _verify_against_verification_schema(verification)
    assert verification["passed"] is False
    assert verification["manifest_schema_valid"] is False
    report_result = next(
        item
        for item in verification["artifacts"]
        if item["path"] == "agentverify-report-v1.schema.json"
    )
    assert report_result["kind"] is None
    assert report_result["contract"] is None
    assert report_result["required"] is None
    assert report_result["present"] is True
    assert report_result["digest_ok"] is True
    assert report_result["bytes_ok"] is True
    assert report_result["content_valid"] is True
    assert any("manifest schema validation failed:" in error for error in verification["errors"])


def test_editor_contract_verifier_rejects_manifest_path_traversal(tmp_path: Path) -> None:
    bundle = tmp_path / "contracts"
    export_editor_contracts(bundle, sample_root=ROOT / "examples/safe_agent")
    outside = tmp_path / "outside.json"
    outside_content = "{}\n"
    outside.write_text(outside_content, encoding="utf-8")
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"].append(
        {
            "path": "../outside.json",
            "sha256": sha256(outside_content.encode("utf-8")).hexdigest(),
            "bytes": len(outside_content.encode("utf-8")),
            "kind": "catalog",
            "contract": "rules",
            "required": False,
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    verification = verify_editor_contracts(bundle)

    _verify_against_verification_schema(verification)
    assert verification["passed"] is False
    traversal_result = next(
        item for item in verification["artifacts"] if item["path"] == "../outside.json"
    )
    assert traversal_result["path_valid"] is False
    assert traversal_result["present"] is False
    assert traversal_result["digest_ok"] is False
    assert any("invalid artifact path: ../outside.json" in error for error in verification["errors"])


def test_cli_contract_verifier_prints_summary(tmp_path: Path, capsys) -> None:
    bundle = tmp_path / "contracts"
    export_editor_contracts(bundle, sample_root=ROOT / "examples/safe_agent")

    assert cli.main(["contracts", "--verify-dir", str(bundle), "--format", "summary"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == (
        "AgentVerify Editor Contract Verification\n"
        f"Directory: {bundle}\n"
        "Passed: true\n"
        "Manifest schema valid: true\n"
        "Required artifacts present: true\n"
        "Artifacts: 4 total (3 required)\n"
        "Artifact files: 4/4 present\n"
        "Digests: 4/4 ok\n"
        "Byte counts: 4/4 ok\n"
        "Content validation: 4/4 ok\n"
    )


def test_cli_contract_summary_format_requires_verify_dir(capsys) -> None:
    assert cli.main(["contracts", "--format", "summary"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "agentverify: --format summary requires --verify-dir\n"


def test_cli_contract_verifier_rejects_missing_required_artifact(
    tmp_path: Path, capsys
) -> None:
    bundle = tmp_path / "contracts"
    manifest_path = tmp_path / "verification.json"
    export_editor_contracts(bundle, sample_root=ROOT / "examples/safe_agent")
    (bundle / "agentverify-report-v1.schema.json").unlink()

    assert (
        cli.main(
            [
                "contracts",
                "--verify-dir",
                str(bundle),
                "--output",
                str(manifest_path),
            ]
        )
        == 1
    )

    assert capsys.readouterr().out == ""
    verification = json.loads(manifest_path.read_text(encoding="utf-8"))
    _verify_against_verification_schema(verification)
    assert verification["passed"] is False
    assert any("missing artifact file: agentverify-report-v1.schema.json" in error for error in verification["errors"])


def test_editor_integration_docs_reference_exported_artifacts() -> None:
    docs = (ROOT / "docs/editor-integration.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "agentverify contracts" in docs
    assert "Mapping findings to editor diagnostics" in docs
    assert "[`examples/editor-diagnostics.json`](../examples/editor-diagnostics.json)" in docs
    assert "python scripts/export_editor_contracts.py" in docs
    assert "agentverify-rules.json" in docs
    assert "agentverify-report-v1.schema.json" in docs
    assert "agentverify rules --format json --output agentverify-rules.json" in docs
    assert "agentverify schema editor-contract-manifest" in docs
    assert "agentverify schema editor-contract-verification" in docs
    assert "agentverify contracts --verify-dir agentverify-editor-contracts" in docs
    assert "agentverify contracts --verify-dir agentverify-editor-contracts --format summary" in docs
    assert "agentverify contracts --verify-dir" in readme
    assert "agentverify contracts --verify-dir agentverify-editor-contracts --format summary" in readme
    assert "`kind`" in docs
    assert "`contract`" in docs
    assert "`required`" in docs
    assert "[`examples/editor-diagnostics.json`](examples/editor-diagnostics.json)" in readme
    assert "[`docs/editor-integration.md`](docs/editor-integration.md)" in readme
    assert "agentverify schema editor-contract-manifest" in readme
    assert "agentverify schema editor-contract-verification" in readme


def test_editor_diagnostics_example_matches_real_report() -> None:
    report = json.loads(render_json(scan_repository(ROOT / "cases/approval_callback_bypass")))
    review_findings = [item for item in report["findings"] if item["result_kind"] == "review"]
    finding = next(item for item in report["findings"] if item["result_kind"] == "finding")
    expected = {
        "schema_version": 1,
        "source_report": "agentverify scan cases/approval_callback_bypass --format json",
        "diagnostics": [
            _editor_diagnostic(review_findings[0]),
            _editor_diagnostic(review_findings[1]),
            _editor_diagnostic(finding),
        ],
    }

    actual = json.loads((ROOT / "examples/editor-diagnostics.json").read_text(encoding="utf-8"))
    assert actual == expected


def test_github_code_scanning_sarif_example_matches_real_report() -> None:
    expected = json.loads(render_sarif(scan_repository(ROOT / "cases/approval_callback_bypass")))
    actual = json.loads((ROOT / "examples/github-code-scanning.sarif").read_text(encoding="utf-8"))

    assert actual == expected
    assert actual["version"] == "2.1.0"
    assert actual["runs"][0]["tool"]["driver"]["name"] == "AgentVerify"
    assert [rule["id"] for rule in actual["runs"][0]["tool"]["driver"]["rules"]] == [
        "AV-APPROVAL001",
        "AV-APPROVAL003",
    ]
    assert {
        result["properties"]["resultKind"] for result in actual["runs"][0]["results"]
    } == {"finding", "review"}

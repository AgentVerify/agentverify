from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import Draft202012Validator

from agentverify import cli
from agentverify.benchmark import CORE_ENGINE_TOTAL_FIELDS, file_sha256
from agentverify.policy import load_policy, render_policy_signing_payload
from agentverify.report import render_bom, render_json, render_sarif, render_schema
from agentverify.rules import RULE_CATALOG
from agentverify.scanner import scan_repository

ROOT = Path(__file__).resolve().parents[1]


def write_signed_policy_artifacts(
    tmp_path: Path,
    repository: Path,
    *,
    signed_at: str = "2026-08-26T00:00:00Z",
) -> tuple[Path, Path]:
    policy, digest = load_policy(repository)
    signing_payload = render_policy_signing_payload(policy, source=repository.name, digest=digest)
    private_key = Ed25519PrivateKey.generate()
    signature = private_key.sign(signing_payload.encode("utf-8"))
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    key_trust_root = tmp_path / "policy-key-trust-root.json"
    key_trust_root.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "trust_model": "local-key-signature",
                "keys": [
                    {
                        "key_id": "security-team-2026",
                        "algorithm": "ed25519",
                        "public_key": base64.b64encode(public_key).decode("ascii"),
                        "trusted_for": ["policy-signing"],
                        "not_before": "2026-01-01T00:00:00Z",
                        "not_after": "2027-01-01T00:00:00Z",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    signature_bundle = tmp_path / "policy-signature.json"
    signature_bundle.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "signature_format": "agentverify-policy-signature",
                "signed_at": signed_at,
                "payload": json.loads(signing_payload),
                "signatures": [
                    {
                        "key_id": "security-team-2026",
                        "algorithm": "ed25519",
                        "signature": base64.b64encode(signature).decode("ascii"),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return key_trust_root, signature_bundle


def test_cli_handles_closed_output_pipe(monkeypatch: pytest.MonkeyPatch) -> None:
    def closed_pipe(*args: object, **kwargs: object) -> None:
        raise BrokenPipeError

    monkeypatch.setattr("builtins.print", closed_pipe)
    assert cli.main(["scan", str(ROOT / "examples/safe_agent")]) == 0


def test_cli_writes_report_to_output_file(tmp_path: Path, capsys) -> None:
    output = tmp_path / "agentverify.json"

    assert (
        cli.main(
            [
                "scan",
                str(ROOT / "examples/safe_agent"),
                "--format",
                "json",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    payload = __import__("json").loads(output.read_text(encoding="utf-8"))
    assert payload["report_format"] == "AgentVerify JSON Report"
    assert payload["schema_version"] == 1
    assert payload["files_scanned"] == 1


def test_cli_output_preserves_threshold_exit_and_short_alias(tmp_path: Path, capsys) -> None:
    output = tmp_path / "agentverify.sarif"

    assert (
        cli.main(
            [
                "scan",
                str(ROOT / "cases/python_dangerous"),
                "--format",
                "sarif",
                "-o",
                str(output),
                "--fail-on",
                "high",
            ]
        )
        == 1
    )
    assert capsys.readouterr().out == ""
    payload = __import__("json").loads(output.read_text(encoding="utf-8"))
    assert [result["ruleId"] for result in payload["runs"][0]["results"]] == ["AV-EXEC001"]


def test_cli_summary_format_is_compact_and_preserves_threshold_exit(capsys) -> None:
    assert (
        cli.main(
            [
                "scan",
                str(ROOT / "cases/python_dangerous"),
                "--format",
                "summary",
                "--fail-on",
                "high",
            ]
        )
        == 1
    )

    output = capsys.readouterr().out
    assert output.startswith("AgentVerify Summary\n")
    assert "Findings: 1\n" in output
    assert "Components:" in output
    assert "Relationships:" in output
    assert "severity high: 1" in output
    assert "kind finding: 1" in output
    assert "AV-EXEC001: 1 [finding; high; confidence high]" in output
    assert "Top findings:\n  AV-EXEC001 high/finding at agent.py:13" in output
    assert "AI Components:" not in output
    assert "Risk Findings:" not in output


def test_cli_summary_includes_baseline_and_policy_status(tmp_path: Path, capsys) -> None:
    target = ROOT / "cases/python_dangerous"
    baseline = tmp_path / "baseline.json"
    baseline.write_text(render_json(scan_repository(target)), encoding="utf-8")
    policy = tmp_path / "strict.json"
    policy.write_text(
        '{"schema_version":1,"gates":[{"id":"new-high","max_count":0}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "scan",
                str(target),
                "--baseline",
                str(baseline),
                "--policy",
                str(policy),
                "--format",
                "summary",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert "Baseline: 0 new, 1 unchanged, 0 no longer reported" in output
    assert "Policy: unnamed [passed; 1 gates]" in output
    assert "  new-high: 0 matched / 0 allowed [passed]" in output
    assert "No findings" in output


def test_cli_output_preserves_policy_exit(tmp_path: Path, capsys) -> None:
    policy = tmp_path / "strict.json"
    policy.write_text(
        '{"schema_version":1,"gates":[{"id":"no-high","max_count":0}]}',
        encoding="utf-8",
    )
    output = tmp_path / "agentverify.json"

    assert (
        cli.main(
            [
                "scan",
                str(ROOT / "cases/python_dangerous"),
                "--format",
                "json",
                "--output",
                str(output),
                "--policy",
                str(policy),
            ]
        )
        == 1
    )
    assert capsys.readouterr().out == ""
    payload = __import__("json").loads(output.read_text(encoding="utf-8"))
    assert payload["policy_summary"]["passed"] is False
    assert payload["policy_summary"]["gates"][0]["matched_count"] == 1


def test_cli_reports_output_write_errors(tmp_path: Path, capsys) -> None:
    assert (
        cli.main(
            [
                "scan",
                str(ROOT / "examples/safe_agent"),
                "--output",
                str(tmp_path),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "agentverify: cannot write output:" in captured.err


def test_review_does_not_fail_by_default_but_can_be_opted_in(capsys) -> None:
    path = str(ROOT / "cases/python_auto_approval")

    assert cli.main(["scan", path, "--fail-on", "high"]) == 0
    assert cli.main(["scan", path, "--fail-on", "high", "--fail-on-kind", "any"]) == 1
    capsys.readouterr()


def test_json_baseline_suppresses_known_fingerprint(tmp_path: Path, capsys) -> None:
    target = ROOT / "cases/python_dangerous"
    baseline = tmp_path / "baseline.json"
    baseline.write_text(render_json(scan_repository(target)), encoding="utf-8")

    assert cli.main(["scan", str(target), "--baseline", str(baseline)]) == 0
    output = capsys.readouterr().out
    assert "Suppressed findings: 1" in output
    assert "Baseline: 0 new, 1 unchanged, 0 no longer reported" in output
    assert "No findings" in output


def test_native_ai_bom_can_be_reused_as_baseline(tmp_path: Path, capsys) -> None:
    target = ROOT / "cases/python_dangerous"
    baseline = tmp_path / "baseline.bom.json"
    baseline.write_text(render_bom(scan_repository(target)), encoding="utf-8")

    assert cli.main(["scan", str(target), "--baseline", str(baseline), "--format", "bom"]) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["risks"] == []
    assert payload["metadata"]["baseline_summary"]["unchanged"] == 1


def test_sarif_can_be_reused_as_baseline(tmp_path: Path, capsys) -> None:
    target = ROOT / "cases/python_dangerous"
    baseline = tmp_path / "baseline.sarif"
    baseline.write_text(render_sarif(scan_repository(target)), encoding="utf-8")

    assert cli.main(["scan", str(target), "--baseline", str(baseline), "--format", "json"]) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["findings"] == []
    assert payload["baseline_summary"]["unchanged"] == 1


def test_unknown_json_baseline_object_is_rejected(tmp_path: Path, capsys) -> None:
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"notes":"not an AgentVerify, BOM, or SARIF baseline"}', encoding="utf-8")

    assert (
        cli.main(["scan", str(ROOT / "cases/python_dangerous"), "--baseline", str(baseline)]) == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "agentverify: invalid baseline:" in captured.err
    assert "AgentVerify JSON report, AI BOM, SARIF report, or fingerprint list" in captured.err


def test_malformed_fingerprint_list_baseline_is_rejected(tmp_path: Path, capsys) -> None:
    baseline = tmp_path / "baseline.json"
    baseline.write_text('["a41f9bb99818a0005c7d", {"fingerprint":"not-allowed"}]', encoding="utf-8")

    assert (
        cli.main(["scan", str(ROOT / "cases/python_dangerous"), "--baseline", str(baseline)]) == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "fingerprint list baseline must contain only non-empty strings" in captured.err


def test_malformed_agentverify_json_baseline_is_rejected(tmp_path: Path, capsys) -> None:
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        '{"report_format":"AgentVerify JSON Report","schema_version":1,"findings":[{}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(["scan", str(ROOT / "cases/python_dangerous"), "--baseline", str(baseline)]) == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "AgentVerify JSON baseline findings[0] must contain a fingerprint string" in captured.err


def test_sarif_baseline_without_agentverify_fingerprints_is_rejected(
    tmp_path: Path, capsys
) -> None:
    baseline = tmp_path / "baseline.sarif"
    baseline.write_text(
        '{"version":"2.1.0","runs":[{"tool":{"driver":{"name":"OtherTool"}},'
        '"results":[{"ruleId":"OTHER"}]}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(["scan", str(ROOT / "cases/python_dangerous"), "--baseline", str(baseline)]) == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "SARIF baseline does not contain AgentVerify fingerprints" in captured.err


def test_partial_baseline_does_not_claim_resolved_findings(tmp_path: Path, capsys) -> None:
    baseline = tmp_path / "baseline.json"
    baseline.write_text('["old-fingerprint"]', encoding="utf-8")
    paths = tmp_path / "changed.txt"
    paths.write_text("agent.py\n", encoding="utf-8")

    target = ROOT / "examples/safe_agent"
    assert (
        cli.main(
            [
                "scan",
                str(target),
                "--baseline",
                str(baseline),
                "--paths-from",
                str(paths),
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = __import__("json").loads(capsys.readouterr().out)
    schema = __import__("json").loads(
        (ROOT / "src/agentverify/schemas/agentverify-report-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(payload)
    assert payload["baseline_summary"] == {
        "baseline_fingerprints": 1,
        "current_fingerprints": 0,
        "new": 0,
        "unchanged": 0,
        "no_longer_reported": None,
    }


def test_version(capsys) -> None:
    with pytest.raises(SystemExit, match="0"):
        cli.main(["--version"])
    assert capsys.readouterr().out.strip() == "agentverify 0.1.0"


def test_cli_lists_enabled_reporting_rules_as_json(capsys) -> None:
    assert cli.main(["rules", "--format", "json"]) == 0

    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["schema_version"] == 1
    assert [rule["rule_id"] for rule in payload["rules"]] == sorted(
        rule["rule_id"] for rule in payload["rules"]
    )
    assert len(payload["rules"]) == 25
    assert next(rule for rule in payload["rules"] if rule["rule_id"] == "AV-EXEC001") == {
        "confidence": "high",
        "remediation": (
            "Pass a fixed argv list with shell disabled, or strictly validate and "
            "allowlist the command."
        ),
        "result_kind": "finding",
        "rule_id": "AV-EXEC001",
        "severity": "high",
        "summary": "A dynamic command is executed through a system shell",
    }


def test_cli_describes_one_rule_and_can_write_it(tmp_path: Path, capsys) -> None:
    output = tmp_path / "rule.txt"

    assert cli.main(["rules", "AV-FS001", "--output", str(output)]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    content = output.read_text(encoding="utf-8")
    assert content.startswith("AV-FS001 [review; high; confidence medium]\n")
    assert "AV-FS002" not in content
    assert "Remediation:" in content


def test_cli_emits_native_ai_bom(capsys) -> None:
    assert cli.main(["scan", str(ROOT / "examples/safe_agent"), "--format", "bom"]) == 0

    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["bom_format"] == "AgentVerify AI BOM"
    assert payload["metadata"]["generator"] == {"name": "AgentVerify", "version": "0.1.0"}
    assert any(asset["kind"] == "agent" for asset in payload["assets"])


def test_cli_prints_bundled_bom_schema(capsys) -> None:
    assert cli.main(["schema", "bom"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    Draft202012Validator.check_schema(schema)
    assert schema["title"] == "AgentVerify AI BOM 1.2"


def test_cli_lists_bundled_schemas(capsys) -> None:
    assert cli.main(["schema"]) == 0

    assert capsys.readouterr().out.splitlines() == [
        "benchmark-result",
        "benchmark-verification",
        "bom",
        "editor-contract-manifest",
        "editor-contract-verification",
        "engine-results",
        "engine-results-verification",
        "holdout-labels",
        "holdout-manifest",
        "policy",
        "policy-key-trust-root",
        "policy-signature",
        "policy-signing-payload",
        "policy-summary",
        "policy-trust-root",
        "report",
        "rules",
    ]


def test_cli_prints_bundled_editor_contract_manifest_schema(capsys) -> None:
    assert cli.main(["schema", "editor-contract-manifest"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    Draft202012Validator.check_schema(schema)
    assert schema["title"] == "AgentVerify Editor Contract Manifest 1"


def test_cli_prints_bundled_editor_contract_verification_schema(capsys) -> None:
    assert cli.main(["schema", "editor-contract-verification"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    Draft202012Validator.check_schema(schema)
    assert schema["title"] == "AgentVerify Editor Contract Verification 1"


def test_cli_prints_bundled_engine_results_schema(capsys) -> None:
    assert cli.main(["schema", "engine-results"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    Draft202012Validator.check_schema(schema)
    assert schema["title"] == "AgentVerify Engine Results 1"
    Draft202012Validator(schema).validate(
        __import__("json").loads(
            (ROOT / "benchmarks/engine-results.json").read_text(encoding="utf-8")
        )
    )


def test_cli_prints_bundled_engine_results_verification_schema(capsys) -> None:
    assert cli.main(["schema", "engine-results-verification"]) == 0

    schema = json.loads(capsys.readouterr().out)
    Draft202012Validator.check_schema(schema)
    assert schema["title"] == "AgentVerify Engine Results Verification 1"


def test_cli_prints_bundled_holdout_template_schemas(capsys) -> None:
    assert cli.main(["schema", "holdout-manifest"]) == 0
    manifest_schema = __import__("json").loads(capsys.readouterr().out)
    Draft202012Validator.check_schema(manifest_schema)
    assert manifest_schema["title"] == "AgentVerify Holdout Manifest 1"
    Draft202012Validator(manifest_schema).validate(
        __import__("json").loads(
            (ROOT / "benchmarks/holdout-manifest.template.json").read_text(encoding="utf-8")
        )
    )

    assert cli.main(["schema", "holdout-labels"]) == 0
    labels_schema = __import__("json").loads(capsys.readouterr().out)
    Draft202012Validator.check_schema(labels_schema)
    assert labels_schema["title"] == "AgentVerify Holdout Labels 1"
    Draft202012Validator(labels_schema).validate(
        __import__("json").loads(
            (ROOT / "benchmarks/holdout-labels.template.json").read_text(encoding="utf-8")
        )
    )


def test_cli_validates_checked_in_holdout_templates(capsys) -> None:
    assert (
        cli.main(
            [
                "holdout",
                "validate",
                "--manifest",
                str(ROOT / "benchmarks/holdout-manifest.template.json"),
                "--labels",
                str(ROOT / "benchmarks/holdout-labels.template.json"),
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["holdout_validation_format"] == "AgentVerify Holdout Validation"
    assert payload["schema_version"] == 1
    assert payload["passed"] is True
    assert [(item["kind"], item["schema"], item["passed"]) for item in payload["files"]] == [
        ("manifest", "holdout-manifest", True),
        ("labels", "holdout-labels", True),
    ]


def test_cli_holdout_validate_requires_an_input(capsys) -> None:
    assert cli.main(["holdout", "validate"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "requires --manifest, --labels, or both" in captured.err


def test_cli_holdout_validate_reports_schema_errors(tmp_path: Path, capsys) -> None:
    invalid = tmp_path / "holdout-labels.json"
    invalid.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "invalid-labels",
                "status": "draft",
                "manifest": "benchmarks/holdout-manifest.template.json",
                "review": {
                    "reviewers": ["reviewer-a"],
                    "adjudication_required": True,
                    "labels_sealed_until_round_closed": True,
                },
                "labels": [],
            }
        ),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "holdout",
                "validate",
                "--labels",
                str(invalid),
                "--format",
                "json",
            ]
        )
        == 2
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert captured.err == ""
    assert payload["passed"] is False
    assert payload["files"][0]["kind"] == "labels"
    assert payload["files"][0]["passed"] is False
    assert "schema validation failed at $.labels" in payload["files"][0]["errors"][0]


def test_cli_holdout_validate_writes_text_output_file(tmp_path: Path, capsys) -> None:
    output = tmp_path / "holdout-validation.txt"

    assert (
        cli.main(
            [
                "holdout",
                "validate",
                "--manifest",
                str(ROOT / "benchmarks/holdout-manifest.template.json"),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert "Holdout validation passed" in output.read_text(encoding="utf-8")


def test_cli_prints_bundled_benchmark_result_schema(capsys) -> None:
    assert cli.main(["schema", "benchmark-result"]) == 0

    raw = capsys.readouterr().out
    schema = __import__("json").loads(raw)
    Draft202012Validator.check_schema(schema)
    assert schema["title"] == "AgentVerify Benchmark Results 1"
    assert raw == (ROOT / "benchmarks/benchmark-results-v1.schema.json").read_text(encoding="utf-8")
    Draft202012Validator(schema).validate(
        __import__("json").loads(
            (ROOT / "benchmarks/truthset-results.json").read_text(encoding="utf-8")
        )
    )
    Draft202012Validator(schema).validate(
        __import__("json").loads(
            (ROOT / "benchmarks/ir-truthset-results.json").read_text(encoding="utf-8")
        )
    )


def test_cli_prints_bundled_benchmark_verification_schema(capsys) -> None:
    assert cli.main(["schema", "benchmark-verification"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    Draft202012Validator.check_schema(schema)
    assert schema["title"] == "AgentVerify Benchmark Verification 1"


def test_cli_verifies_checked_in_benchmark_results(capsys) -> None:
    assert (
        cli.main(
            [
                "benchmark",
                "verify",
                "--require-evaluation-kind",
                "public-regression",
                "--require-all-passed",
            ]
        )
        == 0
    )

    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["passed"] is True
    assert payload["all_labels_passed"] is True
    assert [
        (
            item["label_scope"],
            item["labels"],
            item["failed"],
            item["failure_summary"],
            item["digest_ok"],
        )
        for item in payload["results"]
    ] == [
            (
                "reporting-rules",
                730,
                0,
                {
                "observation_mismatch": 0,
                "anchor_mismatch": 0,
                "source_mismatch": 0,
            },
            True,
        ),
            (
                "agent-ir",
                2451,
                0,
                {
                "observation_mismatch": 0,
                "anchor_mismatch": 0,
                "source_mismatch": 0,
            },
            True,
        ),
    ]
    schema = __import__("json").loads(render_schema("benchmark-verification"))
    Draft202012Validator(schema).validate(payload)


def test_checked_benchmark_verification_example_matches_cli_output(capsys) -> None:
    assert (
        cli.main(
            [
                "benchmark",
                "verify",
                "--require-evaluation-kind",
                "public-regression",
                "--require-all-passed",
            ]
        )
        == 0
    )

    generated = __import__("json").loads(capsys.readouterr().out)
    checked = __import__("json").loads(
        (ROOT / "examples/benchmark-verification.json").read_text(encoding="utf-8")
    )
    assert checked == generated
    schema = __import__("json").loads(render_schema("benchmark-verification"))
    Draft202012Validator(schema).validate(checked)


def test_cli_benchmark_verify_writes_output_file(tmp_path: Path, capsys) -> None:
    output = tmp_path / "benchmark-verification.json"

    assert (
        cli.main(
            [
                "benchmark",
                "verify",
                str(ROOT / "benchmarks/truthset-results.json"),
                "--root",
                str(ROOT),
                "--require-label-scope",
                "reporting-rules",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    payload = __import__("json").loads(output.read_text(encoding="utf-8"))
    assert payload["results"][0]["labels"] == 730
    assert payload["results"][0]["digest_ok"] is True
    schema = __import__("json").loads(render_schema("benchmark-verification"))
    Draft202012Validator(schema).validate(payload)


def test_cli_verifies_checked_in_engine_results(capsys) -> None:
    assert cli.main(["benchmark", "verify-engine"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "engine_results_verification_format": "AgentVerify Engine Results Verification",
        "schema_version": 1,
        "result": "benchmarks/engine-results.json",
        "schema": "engine-results",
        "passed": True,
        "engine_schema_version": 159,
        "generated_at": payload["generated_at"],
        "repositories": 71,
        "successful": 71,
        "summary_repositories": 71,
        "summary_successful": 71,
        "aggregate_total_fields_checked": list(CORE_ENGINE_TOTAL_FIELDS),
    }
    schema = json.loads(render_schema("engine-results-verification"))
    Draft202012Validator(schema).validate(payload)


def test_cli_benchmark_verify_engine_writes_output_file(tmp_path: Path, capsys) -> None:
    output = tmp_path / "engine-results-verification.json"

    assert (
        cli.main(
            [
                "benchmark",
                "verify-engine",
                str(ROOT / "benchmarks/engine-results.json"),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["repositories"] == 71
    assert payload["schema"] == "engine-results"
    assert payload["aggregate_total_fields_checked"] == list(CORE_ENGINE_TOTAL_FIELDS)
    schema = json.loads(render_schema("engine-results-verification"))
    Draft202012Validator(schema).validate(payload)


def test_checked_engine_results_verification_example_matches_cli_output(capsys) -> None:
    assert cli.main(["benchmark", "verify-engine"]) == 0

    generated = json.loads(capsys.readouterr().out)
    checked = json.loads(
        (ROOT / "examples/engine-results-verification.json").read_text(encoding="utf-8")
    )
    assert checked == generated
    schema = json.loads(render_schema("engine-results-verification"))
    Draft202012Validator(schema).validate(checked)


def test_cli_benchmark_verify_engine_rejects_summary_drift(
    tmp_path: Path, capsys
) -> None:
    payload = json.loads((ROOT / "benchmarks/engine-results.json").read_text(encoding="utf-8"))
    payload["summary"]["repositories"] = payload["summary"]["repositories"] + 1
    result = tmp_path / "engine-results.json"
    result.write_text(json.dumps(payload), encoding="utf-8")

    assert cli.main(["benchmark", "verify-engine", str(result)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "summary.repositories does not match repository entries" in captured.err


def test_cli_benchmark_verify_engine_rejects_aggregate_drift(
    tmp_path: Path, capsys
) -> None:
    payload = json.loads((ROOT / "benchmarks/engine-results.json").read_text(encoding="utf-8"))
    payload["summary"]["files_scanned"] = payload["summary"]["files_scanned"] + 1
    result = tmp_path / "engine-results.json"
    result.write_text(json.dumps(payload), encoding="utf-8")

    assert cli.main(["benchmark", "verify-engine", str(result)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "summary.files_scanned does not match repository total" in captured.err


def test_cli_benchmark_verify_rejects_public_results_as_sealed_claim(capsys) -> None:
    assert (
        cli.main(
            [
                "benchmark",
                "verify",
                str(ROOT / "benchmarks/truthset-results.json"),
                "--root",
                str(ROOT),
                "--require-evaluation-kind",
                "sealed-holdout",
                "--require-sealed",
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "agentverify: benchmark verification failed:" in captured.err
    assert "expected evaluation_kind sealed-holdout" in captured.err


def test_cli_benchmark_verify_can_require_all_labels_passed(tmp_path: Path, capsys) -> None:
    labels = tmp_path / "labels.json"
    labels.write_text(
        __import__("json").dumps(
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
    result = tmp_path / "results.json"
    result.write_text(
        __import__("json").dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-08-26T00:00:00+00:00",
                "benchmark": {
                    "evaluation_kind": "public-regression",
                    "label_scope": "reporting-rules",
                    "labels_source": str(labels),
                    "labels_sha256": file_sha256(labels),
                    "sealed": False,
                    "claim_scope": (
                        "curated public regression metrics only; "
                        "not an unbiased ecosystem accuracy estimate"
                    ),
                },
                "labels": 1,
                "passed": 0,
                "failed": 1,
                "failure_summary": {
                    "observation_mismatch": 1,
                    "anchor_mismatch": 0,
                    "source_mismatch": 0,
                },
                "metrics": {
                    "AV-EXEC001": {
                        "tp": 0,
                        "fp": 0,
                        "tn": 0,
                        "fn": 1,
                        "precision": None,
                        "recall": 0.0,
                    }
                },
                "outcomes": [
                    {
                        "id": "label-1",
                        "rule_id": "AV-EXEC001",
                        "expected": True,
                        "observed": False,
                        "anchor_ok": True,
                        "source_ok": True,
                        "passed": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert cli.main(["benchmark", "verify", str(result), "--root", str(tmp_path)]) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["passed"] is True
    assert payload["all_labels_passed"] is False

    assert (
        cli.main(
            [
                "benchmark",
                "verify",
                str(result),
                "--root",
                str(tmp_path),
                "--require-all-passed",
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert "expected all benchmark labels to pass" in captured.err


def test_cli_prints_bundled_policy_schema(capsys) -> None:
    assert cli.main(["schema", "policy"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    policy = __import__("json").loads(
        (ROOT / "examples/ci-policy.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)
    Draft202012Validator(schema).validate(
        __import__("json").loads(
            (ROOT / "examples/repository-policy.json").read_text(encoding="utf-8")
        )
    )
    assert schema["title"] == "AgentVerify Policy 1"
    assert schema["$defs"]["gate"]["properties"]["rules"]["items"]["enum"] == list(RULE_CATALOG)


def test_cli_prints_bundled_policy_summary_schema(capsys) -> None:
    assert cli.main(["schema", "policy-summary"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    Draft202012Validator.check_schema(schema)
    assert schema["title"] == "AgentVerify Policy Summary 1"
    assert schema["properties"]["policy_format"]["const"] == "AgentVerify Policy Summary"
    assert schema["$defs"]["trust"]["properties"]["signature_verified"]["type"] == "boolean"


def test_cli_prints_bundled_policy_key_trust_root_schema(capsys) -> None:
    assert cli.main(["schema", "policy-key-trust-root"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    Draft202012Validator.check_schema(schema)
    assert schema["title"] == "AgentVerify Policy Key Trust Root 1"
    assert schema["properties"]["trust_model"]["const"] == "local-key-signature"
    Draft202012Validator(schema).validate(
        {
            "schema_version": 1,
            "trust_model": "local-key-signature",
            "keys": [
                {
                    "key_id": "security-team-2026",
                    "algorithm": "ed25519",
                    "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                    "trusted_for": ["policy-signing"],
                    "not_before": "2026-01-01T00:00:00Z",
                    "not_after": "2027-01-01T00:00:00Z",
                }
            ],
        }
    )


def test_cli_prints_bundled_policy_signature_schema(capsys) -> None:
    assert cli.main(["schema", "policy-signature"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    Draft202012Validator.check_schema(schema)
    assert schema["title"] == "AgentVerify Policy Signature 1"
    assert schema["properties"]["signature_format"]["const"] == "agentverify-policy-signature"
    digest = "0" * 64
    Draft202012Validator(schema).validate(
        {
            "schema_version": 1,
            "signature_format": "agentverify-policy-signature",
            "signed_at": "2026-08-26T00:00:00Z",
            "payload": {
                "policy_signing_payload_format": "AgentVerify Policy Signing Payload",
                "schema_version": 1,
                "root_source": "repository-policy.json",
                "root_sha256": digest,
                "policy_set": [
                    {"source": "org-policy.json", "sha256": "a" * 64},
                    {"source": "repository-policy.json", "sha256": digest},
                ],
            },
            "signatures": [
                {
                    "key_id": "security-team-2026",
                    "algorithm": "ed25519",
                    "signature": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                }
            ],
        }
    )


def test_cli_prints_bundled_policy_signing_payload_schema(capsys) -> None:
    assert cli.main(["schema", "policy-signing-payload"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    Draft202012Validator.check_schema(schema)
    assert schema["title"] == "AgentVerify Policy Signing Payload 1"
    assert (
        schema["properties"]["policy_signing_payload_format"]["const"]
        == "AgentVerify Policy Signing Payload"
    )


def test_cli_prints_bundled_policy_trust_root_schema(capsys) -> None:
    assert cli.main(["schema", "policy-trust-root"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    Draft202012Validator.check_schema(schema)
    assert schema["title"] == "AgentVerify Policy Trust Root 1"
    assert schema["properties"]["trust_model"]["const"] == "local-content-digest-allowlist"


def test_example_policy_trust_root_matches_composed_policy(capsys) -> None:
    assert (
        cli.main(
            [
                "policy",
                str(ROOT / "examples/repository-policy.json"),
                "--trust-root",
                str(ROOT / "examples/policy-trust-root.json"),
                "--require-trusted",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = __import__("json").loads(capsys.readouterr().out)
    trust_root = payload["trust"]["trust_root"]
    assert trust_root["trusted"] is True
    assert trust_root["matched_sources"] == ["org-policy.json", "repository-policy.json"]


def test_example_policies_gate_every_high_approval_review() -> None:
    expected = sorted(
        rule_id
        for rule_id, definition in RULE_CATALOG.items()
        if rule_id.startswith("AV-APPROVAL")
        and definition.result_kind == "review"
        and definition.severity == "high"
    )

    for path in (ROOT / "examples/ci-policy.json", ROOT / "examples/repository-policy.json"):
        policy, _ = load_policy(path)
        gate = next(item for item in policy["gates"] if item["id"] == "no-approval-bypass-reviews")
        assert gate["rules"] == expected


def test_cli_prints_bundled_report_schema(capsys) -> None:
    assert cli.main(["schema", "report"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    report = __import__("json").loads(render_json(scan_repository(ROOT / "cases/python_dangerous")))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report)
    assert report["report_format"] == "AgentVerify JSON Report"
    assert report["schema_version"] == 1
    assert schema["title"] == "AgentVerify JSON Report 1"
    assert schema["$defs"]["riskSummary"]["required"] == [
        "by_rule",
        "by_result_kind",
        "by_severity",
    ]


def test_cli_prints_bundled_rules_schema(capsys) -> None:
    assert cli.main(["schema", "rules"]) == 0

    schema = __import__("json").loads(capsys.readouterr().out)
    rules = __import__("json").loads(cli.render_rules(None, output_format="json"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(rules)
    assert schema["title"] == "AgentVerify Rules Catalog 1"
    assert schema["$defs"]["rule"]["properties"]["rule_id"]["enum"] == list(RULE_CATALOG)


def test_cli_writes_bundled_schema_to_output_file(tmp_path: Path, capsys) -> None:
    output = tmp_path / "agentverify-policy.schema.json"

    assert cli.main(["schema", "policy", "--output", str(output)]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    schema = __import__("json").loads(output.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["title"] == "AgentVerify Policy 1"


def test_policy_gate_fails_without_hiding_matching_findings(tmp_path: Path, capsys) -> None:
    policy = tmp_path / "strict-policy.json"
    policy.write_text(
        '{"schema_version":1,"name":"strict","gates":['
        '{"id":"high-findings","result_kinds":["finding"],'
        '"min_severity":"high","max_count":0}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "scan",
                str(ROOT / "cases/python_dangerous"),
                "--policy",
                str(policy),
                "--format",
                "json",
            ]
        )
        == 1
    )
    payload = __import__("json").loads(capsys.readouterr().out)
    assert [finding["rule_id"] for finding in payload["findings"]] == ["AV-EXEC001"]
    summary = payload["policy_summary"]
    assert summary["passed"] is False
    assert summary["source"] == "strict-policy.json"
    assert len(summary["sha256"]) == 64
    assert summary["gates"][0]["matched_count"] == 1
    assert summary["gates"][0]["matched_fingerprints"] == [payload["findings"][0]["fingerprint"]]


def test_policy_gate_can_allow_a_review_budget(tmp_path: Path, capsys) -> None:
    policy = tmp_path / "review-budget.json"
    policy.write_text(
        '{"schema_version":1,"gates":['
        '{"id":"approval-review-budget","rules":["AV-APPROVAL001"],'
        '"result_kinds":["review"],"min_severity":"high","max_count":1}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(["scan", str(ROOT / "cases/python_auto_approval"), "--policy", str(policy)]) == 0
    )
    output = capsys.readouterr().out
    assert "Policy: unnamed [passed; 1 gates]" in output
    assert "approval-review-budget: 1 matched / 1 allowed [passed]" in output


def test_policy_is_evaluated_after_baseline(tmp_path: Path, capsys) -> None:
    target = ROOT / "cases/python_dangerous"
    baseline = tmp_path / "baseline.json"
    baseline.write_text(render_json(scan_repository(target)), encoding="utf-8")
    policy = tmp_path / "strict.json"
    policy.write_text(
        '{"schema_version":1,"gates":[{"id":"new-high","max_count":0}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "scan",
                str(target),
                "--baseline",
                str(baseline),
                "--policy",
                str(policy),
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["findings"] == []
    assert payload["policy_summary"]["evaluated_after_baseline"] is True
    assert payload["policy_summary"]["gates"][0]["matched_count"] == 0


def test_composed_policy_retains_each_gate_source_and_digest(tmp_path: Path, capsys) -> None:
    org = tmp_path / "org.json"
    org.write_text(
        '{"schema_version":1,"name":"org","gates":['
        '{"id":"org-high","result_kinds":["finding"],"max_count":0}]}',
        encoding="utf-8",
    )
    repository = tmp_path / "repository.json"
    repository.write_text(
        '{"schema_version":1,"name":"repository","extends":["org.json"],"gates":['
        '{"id":"repository-reviews","result_kinds":["review"],"max_count":5}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "scan",
                str(ROOT / "cases/python_dangerous"),
                "--policy",
                str(repository),
                "--format",
                "json",
            ]
        )
        == 1
    )
    summary = __import__("json").loads(capsys.readouterr().out)["policy_summary"]
    assert summary["name"] == "repository"
    assert [source["source"] for source in summary["sources"]] == [
        "org.json",
        "repository.json",
    ]
    assert [gate["policy_source"] for gate in summary["gates"]] == [
        "org.json",
        "repository.json",
    ]
    assert all(len(source["sha256"]) == 64 for source in summary["sources"])
    assert summary["gates"][0]["matched_count"] == 1
    assert summary["gates"][0]["passed"] is False

    assert cli.main(["scan", str(ROOT / "examples/safe_agent"), "--policy", str(repository)]) == 0
    text = capsys.readouterr().out
    assert "Policy sources: 2" in text
    assert "org-high (org.json): 0 matched / 0 allowed [passed]" in text


def test_cli_policy_explains_composed_policy_without_scanning(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    org = tmp_path / "org.json"
    org.write_text(
        '{"schema_version":1,"name":"org","gates":['
        '{"id":"org-high","result_kinds":["finding"],"max_count":0}]}',
        encoding="utf-8",
    )
    repository = tmp_path / "repository.json"
    repository.write_text(
        '{"schema_version":1,"name":"repository","extends":["org.json"],"gates":['
        '{"id":"repository-reviews","result_kinds":["review"],"max_count":5}]}',
        encoding="utf-8",
    )

    def unexpected_scan(*args: object, **kwargs: object) -> None:
        raise AssertionError("policy explanation must not scan a repository")

    monkeypatch.setattr(cli, "scan_repository", unexpected_scan)

    assert cli.main(["policy", str(repository), "--format", "json"]) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["policy_format"] == "AgentVerify Policy Summary"
    assert payload["schema_version"] == 1
    assert payload["name"] == "repository"
    assert payload["source"] == "repository.json"
    assert len(payload["sha256"]) == 64
    assert [source["source"] for source in payload["sources"]] == ["org.json", "repository.json"]
    assert [gate["policy_source"] for gate in payload["gates"]] == [
        "org.json",
        "repository.json",
    ]
    assert payload["trust"] == {
        "content_hashes": True,
        "note": (
            "SHA-256 digests identify local policy content; they do not prove author authenticity."
        ),
        "signature_verified": False,
    }
    schema = __import__("json").loads(
        (ROOT / "src/agentverify/schemas/agentverify-policy-summary-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(payload)


def test_cli_policy_writes_text_explanation(tmp_path: Path, capsys) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text(
        '{"schema_version":1,"name":"release","gates":['
        '{"id":"no-high","rules":["AV-EXEC001"],"max_count":0}]}',
        encoding="utf-8",
    )
    output = tmp_path / "policy.txt"

    assert cli.main(["policy", str(policy), "--output", str(output)]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    text = output.read_text(encoding="utf-8")
    assert text.startswith("AgentVerify Policy\nName: release\n")
    assert "no-high (policy.json): rules=AV-EXEC001" in text
    assert "Trust: content hashes only; no author signature verified" in text


def test_cli_policy_rejects_invalid_policy_without_scanning(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / "invalid.json"
    policy.write_text(
        '{"schema_version":1,"gates":[],"disable_rules":["AV-EXEC001"]}',
        encoding="utf-8",
    )

    def unexpected_scan(*args: object, **kwargs: object) -> None:
        raise AssertionError("policy validation must not scan a repository")

    monkeypatch.setattr(cli, "scan_repository", unexpected_scan)

    assert cli.main(["policy", str(policy)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "agentverify: invalid policy:" in captured.err
    assert "unknown policy fields: disable_rules" in captured.err


def test_cli_policy_accepts_local_digest_trust_root(tmp_path: Path, capsys) -> None:
    org = tmp_path / "org.json"
    org.write_text(
        '{"schema_version":1,"name":"org","gates":['
        '{"id":"org-high","result_kinds":["finding"],"max_count":0}]}',
        encoding="utf-8",
    )
    repository = tmp_path / "repository.json"
    repository.write_text(
        '{"schema_version":1,"name":"repository","extends":["org.json"],"gates":['
        '{"id":"repository-reviews","result_kinds":["review"],"max_count":5}]}',
        encoding="utf-8",
    )
    policy, _ = load_policy(repository)
    trust_root = tmp_path / "policy-trust-root.json"
    trust_root.write_text(
        __import__("json").dumps(
            {
                "schema_version": 1,
                "trust_model": "local-content-digest-allowlist",
                "policies": policy["_sources"],
            }
        ),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "policy",
                str(repository),
                "--trust-root",
                str(trust_root),
                "--require-trusted",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = __import__("json").loads(capsys.readouterr().out)
    trust = payload["trust"]
    assert trust["signature_verified"] is False
    assert trust["trust_root"]["trusted"] is True
    assert trust["trust_root"]["matched_sources"] == ["org.json", "repository.json"]
    assert trust["trust_root"]["missing_sources"] == []
    schema = __import__("json").loads(
        (ROOT / "src/agentverify/schemas/agentverify-policy-summary-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(payload)


def test_cli_policy_can_export_local_digest_trust_root(tmp_path: Path, capsys) -> None:
    org = tmp_path / "org.json"
    org.write_text(
        '{"schema_version":1,"name":"org","gates":['
        '{"id":"org-high","result_kinds":["finding"],"max_count":0}]}',
        encoding="utf-8",
    )
    repository = tmp_path / "repository.json"
    repository.write_text(
        '{"schema_version":1,"name":"repository","extends":["org.json"],"gates":['
        '{"id":"repository-reviews","result_kinds":["review"],"max_count":5}]}',
        encoding="utf-8",
    )
    trust_root = tmp_path / "generated-trust-root.json"

    assert (
        cli.main(["policy", str(repository), "--export-trust-root", "--output", str(trust_root)])
        == 0
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    payload = __import__("json").loads(trust_root.read_text(encoding="utf-8"))
    assert payload["trust_model"] == "local-content-digest-allowlist"
    assert [item["source"] for item in payload["policies"]] == ["org.json", "repository.json"]
    schema = __import__("json").loads(
        (ROOT / "src/agentverify/schemas/agentverify-policy-trust-root-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(payload)

    assert (
        cli.main(
            [
                "policy",
                str(repository),
                "--trust-root",
                str(trust_root),
                "--require-trusted",
                "--format",
                "json",
            ]
        )
        == 0
    )


def test_cli_policy_can_export_deterministic_signing_payload(tmp_path: Path, capsys) -> None:
    org = tmp_path / "org.json"
    org.write_text(
        '{"schema_version":1,"name":"org","gates":['
        '{"id":"org-high","result_kinds":["finding"],"max_count":0}]}',
        encoding="utf-8",
    )
    repository = tmp_path / "repository.json"
    repository.write_text(
        '{"schema_version":1,"name":"repository","extends":["org.json"],"gates":['
        '{"id":"repository-reviews","result_kinds":["review"],"max_count":5}]}',
        encoding="utf-8",
    )
    payload_path = tmp_path / "policy-signing-payload.json"

    assert (
        cli.main(
            [
                "policy",
                str(repository),
                "--export-signing-payload",
                "--output",
                str(payload_path),
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    payload = __import__("json").loads(payload_path.read_text(encoding="utf-8"))
    assert payload["policy_signing_payload_format"] == "AgentVerify Policy Signing Payload"
    assert payload["schema_version"] == 1
    assert payload["root_source"] == "repository.json"
    assert len(payload["root_sha256"]) == 64
    assert [item["source"] for item in payload["policy_set"]] == ["org.json", "repository.json"]
    assert payload["root_sha256"] == payload["policy_set"][-1]["sha256"]
    assert "signature_verified" not in payload
    schema = __import__("json").loads(
        (
            ROOT / "src/agentverify/schemas/agentverify-policy-signing-payload-v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)

    first = payload_path.read_text(encoding="utf-8")
    assert (
        cli.main(
            [
                "policy",
                str(repository),
                "--export-signing-payload",
                "--output",
                str(payload_path),
            ]
        )
        == 0
    )
    assert payload_path.read_text(encoding="utf-8") == first


def test_cli_policy_verifies_detached_policy_signature(tmp_path: Path, capsys) -> None:
    org = tmp_path / "org.json"
    org.write_text(
        '{"schema_version":1,"name":"org","gates":['
        '{"id":"org-high","result_kinds":["finding"],"max_count":0}]}',
        encoding="utf-8",
    )
    repository = tmp_path / "repository.json"
    repository.write_text(
        '{"schema_version":1,"name":"repository","extends":["org.json"],"gates":['
        '{"id":"repository-reviews","result_kinds":["review"],"max_count":5}]}',
        encoding="utf-8",
    )
    key_trust_root, signature_bundle = write_signed_policy_artifacts(tmp_path, repository)

    assert (
        cli.main(
            [
                "policy",
                str(repository),
                "--signature",
                str(signature_bundle),
                "--trust-root",
                str(key_trust_root),
                "--require-trusted",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    trust = payload["trust"]
    assert trust["signature_verified"] is True
    signature = trust["signature"]
    assert signature["trusted"] is True
    assert signature["trust_model"] == "local-key-signature"
    assert signature["signature_format"] == "agentverify-policy-signature"
    assert signature["matched_sources"] == ["org.json", "repository.json"]
    assert signature["missing_sources"] == []
    assert signature["digest_mismatches"] == []
    assert signature["payload_mismatches"] == []
    assert signature["verified_signatures"] == [{"key_id": "security-team-2026"}]
    assert signature["invalid_signatures"] == []
    schema = json.loads(
        (ROOT / "src/agentverify/schemas/agentverify-policy-summary-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(payload)


def test_cli_policy_signature_fails_closed_when_policy_changes(tmp_path: Path, capsys) -> None:
    org = tmp_path / "org.json"
    org.write_text(
        '{"schema_version":1,"name":"org","gates":['
        '{"id":"org-high","result_kinds":["finding"],"max_count":0}]}',
        encoding="utf-8",
    )
    repository = tmp_path / "repository.json"
    repository.write_text(
        '{"schema_version":1,"name":"repository","extends":["org.json"],"gates":['
        '{"id":"repository-reviews","result_kinds":["review"],"max_count":5}]}',
        encoding="utf-8",
    )
    key_trust_root, signature_bundle = write_signed_policy_artifacts(tmp_path, repository)
    org.write_text(
        '{"schema_version":1,"name":"org","gates":['
        '{"id":"org-high","result_kinds":["finding"],"max_count":1}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "policy",
                str(repository),
                "--signature",
                str(signature_bundle),
                "--trust-root",
                str(key_trust_root),
                "--require-trusted",
                "--format",
                "json",
            ]
        )
        == 1
    )

    payload = json.loads(capsys.readouterr().out)
    signature = payload["trust"]["signature"]
    assert payload["trust"]["signature_verified"] is False
    assert signature["trusted"] is False
    assert signature["digest_mismatches"][0]["source"] == "org.json"
    assert "policy_set" in signature["payload_mismatches"]
    assert signature["verified_signatures"] == [{"key_id": "security-team-2026"}]
    schema = json.loads(
        (ROOT / "src/agentverify/schemas/agentverify-policy-summary-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(payload)


def test_cli_policy_signature_fails_closed_on_invalid_signature(tmp_path: Path, capsys) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text(
        '{"schema_version":1,"name":"release","gates":[{"id":"no-high","max_count":0}]}',
        encoding="utf-8",
    )
    key_trust_root, signature_bundle = write_signed_policy_artifacts(tmp_path, policy)
    bundle = json.loads(signature_bundle.read_text(encoding="utf-8"))
    bundle["signatures"][0]["signature"] = base64.b64encode(b"\0" * 64).decode("ascii")
    signature_bundle.write_text(json.dumps(bundle), encoding="utf-8")

    assert (
        cli.main(
            [
                "policy",
                str(policy),
                "--signature",
                str(signature_bundle),
                "--trust-root",
                str(key_trust_root),
                "--require-trusted",
                "--format",
                "json",
            ]
        )
        == 1
    )
    signature = json.loads(capsys.readouterr().out)["trust"]["signature"]
    assert signature["trusted"] is False
    assert signature["verified_signatures"] == []
    assert signature["invalid_signatures"] == [{"key_id": "security-team-2026"}]


def test_cli_policy_signature_requires_key_trust_root(tmp_path: Path, capsys) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text(
        '{"schema_version":1,"name":"release","gates":[{"id":"no-high","max_count":0}]}',
        encoding="utf-8",
    )
    _, signature_bundle = write_signed_policy_artifacts(tmp_path, policy)

    assert cli.main(["policy", str(policy), "--signature", str(signature_bundle)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--signature requires --trust-root" in captured.err


def test_cli_policy_signature_rejects_invalid_key_trust_root(tmp_path: Path, capsys) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text(
        '{"schema_version":1,"name":"release","gates":[{"id":"no-high","max_count":0}]}',
        encoding="utf-8",
    )
    key_trust_root, signature_bundle = write_signed_policy_artifacts(tmp_path, policy)
    key_trust_root.write_text(
        '{"schema_version":1,"trust_model":"local-content-digest-allowlist","keys":[]}',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "policy",
                str(policy),
                "--signature",
                str(signature_bundle),
                "--trust-root",
                str(key_trust_root),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid policy key trust root" in captured.err
    assert "trust_model must be local-key-signature" in captured.err


def test_cli_policy_signature_rejects_export_option_conflict(tmp_path: Path, capsys) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text(
        '{"schema_version":1,"name":"release","gates":[{"id":"no-high","max_count":0}]}',
        encoding="utf-8",
    )
    key_trust_root, signature_bundle = write_signed_policy_artifacts(tmp_path, policy)

    assert (
        cli.main(
            [
                "policy",
                str(policy),
                "--export-signing-payload",
                "--signature",
                str(signature_bundle),
                "--trust-root",
                str(key_trust_root),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "export options cannot be combined" in captured.err


def test_cli_policy_export_trust_root_rejects_conflicting_trust_options(
    tmp_path: Path, capsys
) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text(
        '{"schema_version":1,"name":"release","gates":[{"id":"no-high","max_count":0}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "policy",
                str(policy),
                "--export-trust-root",
                "--require-trusted",
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "export options cannot be combined" in captured.err


def test_cli_policy_export_options_are_mutually_exclusive(tmp_path: Path, capsys) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text(
        '{"schema_version":1,"name":"release","gates":[{"id":"no-high","max_count":0}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "policy",
                str(policy),
                "--export-trust-root",
                "--export-signing-payload",
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--export-trust-root cannot be combined with --export-signing-payload" in captured.err


def test_cli_policy_trust_root_can_fail_required_trust(tmp_path: Path, capsys) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text(
        '{"schema_version":1,"name":"release","gates":[{"id":"no-high","max_count":0}]}',
        encoding="utf-8",
    )
    trust_root = tmp_path / "policy-trust-root.json"
    trust_root.write_text(
        '{"schema_version":1,"trust_model":"local-content-digest-allowlist",'
        '"policies":[{"source":"policy.json","sha256":"0000000000000000000000000000000000000000000000000000000000000000"}]}',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "policy",
                str(policy),
                "--trust-root",
                str(trust_root),
                "--require-trusted",
                "--format",
                "json",
            ]
        )
        == 1
    )
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["trust"]["trust_root"]["trusted"] is False
    assert payload["trust"]["trust_root"]["digest_mismatches"][0]["source"] == "policy.json"


def test_cli_policy_rejects_invalid_trust_root(tmp_path: Path, capsys) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text(
        '{"schema_version":1,"name":"release","gates":[{"id":"no-high","max_count":0}]}',
        encoding="utf-8",
    )
    trust_root = tmp_path / "policy-trust-root.json"
    trust_root.write_text(
        '{"schema_version":1,"trust_model":"signed-policy","policies":[]}',
        encoding="utf-8",
    )

    assert cli.main(["policy", str(policy), "--trust-root", str(trust_root)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid policy trust root" in captured.err
    assert "trust_model must be local-content-digest-allowlist" in captured.err


def test_cli_policy_requires_trust_root_for_required_trust(tmp_path: Path, capsys) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text(
        '{"schema_version":1,"name":"release","gates":[{"id":"no-high","max_count":0}]}',
        encoding="utf-8",
    )

    assert cli.main(["policy", str(policy), "--require-trusted"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--require-trusted requires --trust-root" in captured.err


def test_invalid_policy_is_rejected_before_scanning(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / "invalid.json"
    policy.write_text(
        '{"schema_version":1,"gates":[],"disable_rules":["AV-EXEC001"]}',
        encoding="utf-8",
    )

    def unexpected_scan(*args: object, **kwargs: object) -> None:
        raise AssertionError("scan must not run")

    monkeypatch.setattr(cli, "scan_repository", unexpected_scan)

    assert cli.main(["scan", str(ROOT / "cases/python_dangerous"), "--policy", str(policy)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown policy fields: disable_rules" in captured.err


def test_unknown_policy_rule_is_rejected_before_scanning(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / "invalid-rule.json"
    policy.write_text(
        '{"schema_version":1,"gates":[{"id":"typo","rules":["AV-EXECC001"],"max_count":0}]}',
        encoding="utf-8",
    )

    def unexpected_scan(*args: object, **kwargs: object) -> None:
        raise AssertionError("scan must not run")

    monkeypatch.setattr(cli, "scan_repository", unexpected_scan)

    assert cli.main(["scan", str(ROOT / "cases/python_dangerous"), "--policy", str(policy)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "rules contains unsupported values: AV-EXECC001" in captured.err


def test_impossible_policy_rule_filter_is_rejected_before_scanning(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / "dead-filter.json"
    policy.write_text(
        '{"schema_version":1,"gates":['
        '{"id":"wrong-kind","rules":["AV-APPROVAL001"],"max_count":0}]}',
        encoding="utf-8",
    )

    def unexpected_scan(*args: object, **kwargs: object) -> None:
        raise AssertionError("scan must not run")

    monkeypatch.setattr(cli, "scan_repository", unexpected_scan)

    assert (
        cli.main(["scan", str(ROOT / "cases/python_auto_approval"), "--policy", str(policy)]) == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "AV-APPROVAL001 emits review" in captured.err


def test_paths_from_scans_only_selected_repository_paths(tmp_path: Path, capsys) -> None:
    paths = tmp_path / "changed.txt"
    paths.write_text("cases/python_dangerous/agent.py\n", encoding="utf-8")

    assert cli.main(["scan", str(ROOT), "--paths-from", str(paths), "--format", "json"]) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["scan_scope"] == "selected-paths"
    assert payload["path_filters"] == ["cases/python_dangerous/agent.py"]
    assert payload["files_scanned"] == 1
    assert [finding["rule_id"] for finding in payload["findings"]] == ["AV-EXEC001"]


def test_paths_from_rejects_escape(tmp_path: Path, capsys) -> None:
    paths = tmp_path / "changed.txt"
    paths.write_text("../outside.py\n", encoding="utf-8")

    assert cli.main(["scan", str(ROOT), "--paths-from", str(paths)]) == 2
    assert "must stay inside the scan root" in capsys.readouterr().err


def test_empty_paths_from_scans_nothing_but_dot_selects_root(tmp_path: Path, capsys) -> None:
    paths = tmp_path / "changed.txt"
    paths.write_text("", encoding="utf-8")
    target = ROOT / "cases/python_dangerous"

    assert cli.main(["scan", str(target), "--paths-from", str(paths), "--format", "json"]) == 0
    empty = __import__("json").loads(capsys.readouterr().out)
    assert empty["files_scanned"] == 0
    assert empty["path_filters"] == []

    paths.write_text(".\n", encoding="utf-8")
    assert cli.main(["scan", str(target), "--paths-from", str(paths), "--format", "json"]) == 0
    selected = __import__("json").loads(capsys.readouterr().out)
    assert selected["files_scanned"] == 1
    assert selected["path_filters"] == ["."]


def test_cli_can_require_suppression_expiry(tmp_path: Path, capsys) -> None:
    (tmp_path / "agent.py").write_text(
        """import subprocess
# agentverify: ignore AV-EXEC001 -- temporary exception
subprocess.run(command, shell=True)
""",
        encoding="utf-8",
    )

    assert (
        cli.main(["scan", str(tmp_path), "--require-suppression-expiry", "--fail-on", "high"]) == 1
    )
    output = capsys.readouterr().out
    assert "AV-EXEC001" in output
    assert "missing-expiry" in output

"""Exportable machine contracts for AgentVerify integrations."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from . import __version__
from .report import render_json, render_rules, render_schema
from .scanner import scan_repository

CONTRACT_VERIFICATION_ERRORS = (
    OSError,
    json.JSONDecodeError,
    SchemaError,
    ValidationError,
)

CONTRACT_FILES = {
    "agentverify-report-v1.schema.json": {
        "kind": "schema",
        "contract": "report",
        "required": True,
    },
    "agentverify-editor-diagnostics-v1.schema.json": {
        "kind": "schema",
        "contract": "editor-diagnostics",
        "required": True,
    },
    "agentverify-rules-v1.schema.json": {
        "kind": "schema",
        "contract": "rules",
        "required": True,
    },
    "agentverify-rules.json": {
        "kind": "catalog",
        "contract": "rules",
        "required": True,
    },
}


def _write(path: Path, content: str, **metadata: object) -> dict[str, object]:
    path.write_text(content, encoding="utf-8")
    digest = sha256(content.encode("utf-8")).hexdigest()
    return {
        "path": path.name,
        "sha256": digest,
        "bytes": len(content.encode("utf-8")),
        **metadata,
    }


def export_editor_contracts(
    output_dir: Path,
    *,
    sample_root: Path | None = None,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rules_schema = json.loads(render_schema("rules"))
    report_schema = json.loads(render_schema("report"))
    editor_diagnostics_schema = json.loads(render_schema("editor-diagnostics"))
    manifest_schema = json.loads(render_schema("editor-contract-manifest"))
    Draft202012Validator.check_schema(rules_schema)
    Draft202012Validator.check_schema(report_schema)
    Draft202012Validator.check_schema(editor_diagnostics_schema)
    Draft202012Validator.check_schema(manifest_schema)

    artifacts = []
    for filename, metadata in CONTRACT_FILES.items():
        name = str(metadata["contract"])
        if metadata["kind"] == "schema":
            content = render_schema(name)
        else:
            content = render_rules(None, output_format="json")
            Draft202012Validator(rules_schema).validate(json.loads(content))
        artifacts.append(_write(output_dir / filename, content, **metadata))

    if sample_root is not None:
        report = render_json(scan_repository(sample_root))
        Draft202012Validator(report_schema).validate(json.loads(report))
        artifacts.append(
            _write(
                output_dir / "agentverify-sample-report.json",
                report,
                kind="sample-report",
                contract="report",
                required=False,
            )
        )

    manifest = {
        "schema_version": 1,
        "generator": {"name": "AgentVerify", "version": __version__},
        "purpose": "editor-ci-contract-export",
        "artifacts": artifacts,
    }
    Draft202012Validator(manifest_schema).validate(manifest)
    manifest_content = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    _write(output_dir / "manifest.json", manifest_content)
    return manifest


def render_editor_contract_manifest(manifest: dict[str, object]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def _artifact_index(manifest: dict[str, object]) -> dict[str, dict[str, object]]:
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        return {}
    return {
        str(item["path"]): item
        for item in artifacts
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }


def _safe_bundle_artifact_path(bundle_dir: Path, relative_path: str) -> tuple[Path | None, str | None]:
    if (
        not relative_path
        or relative_path in {".", ".."}
        or "/" in relative_path
        or "\\" in relative_path
        or "\x00" in relative_path
        or Path(relative_path).is_absolute()
        or Path(relative_path).name != relative_path
    ):
        return None, f"invalid artifact path: {relative_path}"
    return bundle_dir / relative_path, None


def verify_editor_contracts(bundle_dir: Path) -> dict[str, object]:
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_schema = json.loads(render_schema("editor-contract-manifest"))
    verification_schema = json.loads(render_schema("editor-contract-verification"))
    Draft202012Validator.check_schema(manifest_schema)
    Draft202012Validator.check_schema(verification_schema)

    errors: list[str] = []
    try:
        Draft202012Validator(manifest_schema).validate(manifest)
        manifest_schema_valid = True
    except ValidationError as error:
        manifest_schema_valid = False
        errors.append(f"manifest schema validation failed: {error.message}")

    artifacts_by_path = _artifact_index(manifest)
    artifact_paths = [
        item.get("path")
        for item in manifest.get("artifacts", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    duplicate_paths = sorted({path for path in artifact_paths if artifact_paths.count(path) > 1})
    for path in duplicate_paths:
        errors.append(f"duplicate artifact entry: {path}")
    required_paths = set(CONTRACT_FILES)
    missing_required_paths = sorted(required_paths - set(artifacts_by_path))
    for path in missing_required_paths:
        errors.append(f"manifest is missing required artifact entry: {path}")

    rules_schema = None
    report_schema = None
    artifact_results: list[dict[str, object]] = []
    for artifact in manifest.get("artifacts", []):
        if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
            continue
        relative_path = artifact["path"]
        kind = artifact.get("kind")
        contract = artifact.get("contract")
        required = artifact.get("required")
        result: dict[str, object] = {
            "path": relative_path,
            "kind": kind if isinstance(kind, str) else None,
            "contract": contract if isinstance(contract, str) else None,
            "required": required if isinstance(required, bool) else None,
            "path_valid": True,
            "present": False,
            "digest_ok": False,
            "bytes_ok": False,
            "content_valid": None,
        }
        artifact_path, path_error = _safe_bundle_artifact_path(bundle_dir, relative_path)
        if path_error is not None or artifact_path is None:
            result["path_valid"] = False
            errors.append(path_error or f"invalid artifact path: {relative_path}")
            artifact_results.append(result)
            continue
        result["present"] = artifact_path.is_file()
        if not artifact_path.is_file():
            errors.append(f"missing artifact file: {relative_path}")
            artifact_results.append(result)
            continue

        raw = artifact_path.read_bytes()
        digest = sha256(raw).hexdigest()
        expected_digest = artifact.get("sha256")
        expected_bytes = artifact.get("bytes")
        result["digest_ok"] = digest == expected_digest
        result["bytes_ok"] = len(raw) == expected_bytes
        if not result["digest_ok"]:
            errors.append(f"artifact digest mismatch: {relative_path}")
        if not result["bytes_ok"]:
            errors.append(f"artifact byte count mismatch: {relative_path}")

        content_valid = True
        try:
            if relative_path == "agentverify-rules-v1.schema.json":
                rules_schema = json.loads(raw.decode("utf-8"))
                Draft202012Validator.check_schema(rules_schema)
            elif relative_path == "agentverify-report-v1.schema.json":
                report_schema = json.loads(raw.decode("utf-8"))
                Draft202012Validator.check_schema(report_schema)
            elif relative_path == "agentverify-editor-diagnostics-v1.schema.json":
                editor_diagnostics_schema = json.loads(raw.decode("utf-8"))
                Draft202012Validator.check_schema(editor_diagnostics_schema)
        except (json.JSONDecodeError, UnicodeDecodeError, SchemaError) as error:
            content_valid = False
            errors.append(f"artifact content validation failed for {relative_path}: {error}")
        result["content_valid"] = content_valid
        artifact_results.append(result)

    for artifact in manifest.get("artifacts", []):
        if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
            continue
        relative_path = artifact["path"]
        artifact_path, path_error = _safe_bundle_artifact_path(bundle_dir, relative_path)
        if path_error is not None or artifact_path is None:
            continue
        if not artifact_path.is_file():
            continue
        matching_results = [item for item in artifact_results if item["path"] == relative_path]
        if not matching_results:
            continue
        try:
            if relative_path == "agentverify-rules.json" and rules_schema is not None:
                Draft202012Validator(rules_schema).validate(
                    json.loads(artifact_path.read_text(encoding="utf-8"))
                )
                matching_results[0]["content_valid"] = True
            elif relative_path == "agentverify-sample-report.json" and report_schema is not None:
                Draft202012Validator(report_schema).validate(
                    json.loads(artifact_path.read_text(encoding="utf-8"))
                )
                matching_results[0]["content_valid"] = True
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as error:
            matching_results[0]["content_valid"] = False
            errors.append(f"artifact content validation failed for {relative_path}: {error}")

    passed = manifest_schema_valid and not errors
    payload: dict[str, object] = {
        "schema_version": 1,
        "verification": "AgentVerify Editor Contract Bundle Verification",
        "directory": str(bundle_dir),
        "manifest_schema_valid": manifest_schema_valid,
        "required_artifacts_present": not missing_required_paths,
        "artifacts": artifact_results,
        "passed": passed,
        "errors": errors,
    }
    Draft202012Validator(verification_schema).validate(payload)
    return payload


def render_editor_contract_verification(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_editor_contract_verification_summary(payload: dict[str, object]) -> str:
    artifacts = payload["artifacts"]
    if not isinstance(artifacts, list):
        raise TypeError("artifacts must be an array")
    required = [artifact for artifact in artifacts if artifact.get("required") is True]
    content_checked = [
        artifact for artifact in artifacts if isinstance(artifact.get("content_valid"), bool)
    ]
    lines = [
        "AgentVerify Editor Contract Verification",
        f"Directory: {payload['directory']}",
        f"Passed: {str(payload['passed']).lower()}",
        f"Manifest schema valid: {str(payload['manifest_schema_valid']).lower()}",
        f"Required artifacts present: {str(payload['required_artifacts_present']).lower()}",
        f"Artifacts: {len(artifacts)} total ({len(required)} required)",
        f"Artifact files: {sum(1 for artifact in artifacts if artifact['present'] is True)}/{len(artifacts)} present",
        f"Digests: {sum(1 for artifact in artifacts if artifact['digest_ok'] is True)}/{len(artifacts)} ok",
        f"Byte counts: {sum(1 for artifact in artifacts if artifact['bytes_ok'] is True)}/{len(artifacts)} ok",
        (
            "Content validation: "
            f"{sum(1 for artifact in content_checked if artifact['content_valid'] is True)}/"
            f"{len(content_checked)} ok"
        ),
    ]
    errors = payload.get("errors", [])
    if errors:
        lines.append(f"Errors: {len(errors)}")
        lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines) + "\n"

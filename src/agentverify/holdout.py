"""Holdout setup validation helpers."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from .report import render_schema

HOLDOUT_SCHEMA_NAMES = {
    "manifest": "holdout-manifest",
    "labels": "holdout-labels",
}
HOLDOUT_VALIDATION_ERRORS = (json.JSONDecodeError, SchemaError)


def _error_path(error: ValidationError) -> str:
    path = "$"
    for part in error.absolute_path:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"
    return path


def _schema_for_kind(kind: str) -> dict:
    schema = json.loads(render_schema(HOLDOUT_SCHEMA_NAMES[kind]))
    Draft202012Validator.check_schema(schema)
    return schema


def validate_holdout_file(kind: str, path: Path) -> dict[str, object]:
    """Validate one holdout setup file and return a report entry."""

    schema = _schema_for_kind(kind)
    entry: dict[str, object] = {
        "kind": kind,
        "path": str(path),
        "schema": HOLDOUT_SCHEMA_NAMES[kind],
        "schema_title": schema.get("title"),
        "passed": False,
        "errors": [],
    }

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        entry["errors"] = [f"invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}"]
        return entry
    except UnicodeDecodeError as error:
        entry["errors"] = [f"invalid UTF-8: {error}"]
        return entry
    except OSError as error:
        entry["errors"] = [f"cannot read file: {error}"]
        return entry

    errors = sorted(
        Draft202012Validator(schema).iter_errors(payload),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if errors:
        entry["errors"] = [
            f"schema validation failed at {_error_path(error)}: {error.message}"
            for error in errors
        ]
        return entry

    entry["passed"] = True
    return entry


def validate_holdout_files(
    *, manifest: Path | None = None, labels: Path | None = None
) -> dict[str, object]:
    """Validate requested holdout setup files."""

    files = []
    if manifest is not None:
        files.append(validate_holdout_file("manifest", manifest))
    if labels is not None:
        files.append(validate_holdout_file("labels", labels))
    return {
        "holdout_validation_format": "AgentVerify Holdout Validation",
        "schema_version": 1,
        "passed": all(file["passed"] is True for file in files),
        "files": files,
    }


def render_holdout_validation(payload: dict[str, object], *, output_format: str = "json") -> str:
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"

    status = "passed" if payload["passed"] is True else "failed"
    lines = [f"Holdout validation {status}"]
    for file in payload["files"]:
        file_status = "passed" if file["passed"] is True else "failed"
        lines.append(f"  {file['kind']}: {file['path']} [{file_status}]")
        for error in file["errors"]:
            lines.append(f"    - {error}")
    return "\n".join(lines) + "\n"

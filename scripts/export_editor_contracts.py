"""Export AgentVerify contracts useful for editor and CI integrations."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from jsonschema import Draft202012Validator

from agentverify import __version__
from agentverify.report import render_json, render_rules, render_schema
from agentverify.scanner import scan_repository

CONTRACT_FILES = {
    "agentverify-report-v1.schema.json": ("schema", "report"),
    "agentverify-rules-v1.schema.json": ("schema", "rules"),
    "agentverify-rules.json": ("catalog", "rules"),
}


def _write(path: Path, content: str) -> dict[str, object]:
    path.write_text(content, encoding="utf-8")
    digest = sha256(content.encode("utf-8")).hexdigest()
    return {"path": path.name, "sha256": digest, "bytes": len(content.encode("utf-8"))}


def export_editor_contracts(
    output_dir: Path,
    *,
    sample_root: Path | None = None,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rules_schema = json.loads(render_schema("rules"))
    report_schema = json.loads(render_schema("report"))
    Draft202012Validator.check_schema(rules_schema)
    Draft202012Validator.check_schema(report_schema)

    artifacts = []
    for filename, (kind, name) in CONTRACT_FILES.items():
        if kind == "schema":
            content = render_schema(name)
        else:
            content = render_rules(None, output_format="json")
            Draft202012Validator(rules_schema).validate(json.loads(content))
        artifacts.append(_write(output_dir / filename, content))

    if sample_root is not None:
        report = render_json(scan_repository(sample_root))
        Draft202012Validator(report_schema).validate(json.loads(report))
        artifacts.append(_write(output_dir / "agentverify-sample-report.json", report))

    manifest = {
        "schema_version": 1,
        "generator": {"name": "AgentVerify", "version": __version__},
        "purpose": "editor-ci-contract-export",
        "artifacts": artifacts,
    }
    manifest_content = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    _write(output_dir / "manifest.json", manifest_content)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export schema-backed AgentVerify contracts for editor and CI tooling."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("agentverify-editor-contracts"),
        help="directory to create or update with exported contract artifacts",
    )
    parser.add_argument(
        "--sample-root",
        type=Path,
        help="optional repository path to scan and include as agentverify-sample-report.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = export_editor_contracts(args.output_dir, sample_root=args.sample_root)
    print(json.dumps(manifest, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

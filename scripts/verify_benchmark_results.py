"""Validate benchmark result files and their embedded input provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

DEFAULT_RESULTS = (
    Path("benchmarks/truthset-results.json"),
    Path("benchmarks/ir-truthset-results.json"),
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_source(root: Path, source: str) -> Path:
    path = Path(source)
    return path if path.is_absolute() else root / path


def load_schema(path: Path) -> dict:
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def verify_result(path: Path, *, schema: dict, root: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)
    benchmark = payload["benchmark"]
    labels_path = resolve_source(root, benchmark["labels_source"])
    labels_payload = json.loads(labels_path.read_text(encoding="utf-8"))
    labels = labels_payload.get("labels", [])
    if file_sha256(labels_path) != benchmark["labels_sha256"]:
        raise RuntimeError(f"{path}: labels_sha256 does not match {labels_path}")
    if len(labels) != payload["labels"]:
        raise RuntimeError(f"{path}: labels count does not match {labels_path}")
    manifest_source = benchmark.get("manifest_source")
    if manifest_source:
        manifest_path = resolve_source(root, manifest_source)
        if file_sha256(manifest_path) != benchmark["manifest_sha256"]:
            raise RuntimeError(f"{path}: manifest_sha256 does not match {manifest_path}")
    return {
        "result": str(path),
        "evaluation_kind": benchmark["evaluation_kind"],
        "label_scope": benchmark["label_scope"],
        "labels": payload["labels"],
        "passed": payload["passed"],
        "labels_source": str(labels_path),
        "digest_ok": True,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate AgentVerify benchmark results and input digests."
    )
    parser.add_argument("results", nargs="*", type=Path, default=list(DEFAULT_RESULTS))
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("benchmarks/benchmark-results-v1.schema.json"),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="repository root used to resolve relative labels_source and manifest_source values",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        schema = load_schema(args.schema)
        results = [verify_result(path, schema=schema, root=args.root) for path in args.results]
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"agentverify benchmark verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"results": results, "passed": True}, indent=2) + "\n", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

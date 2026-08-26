"""Verify release wheel contents that AgentVerify depends on at runtime."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

REQUIRED_SCHEMA_FILES = frozenset(
    {
        "agentverify/schemas/agentverify-ai-bom-v1.schema.json",
        "agentverify/schemas/agentverify-policy-v1.schema.json",
        "agentverify/schemas/agentverify-report-v1.schema.json",
        "agentverify/schemas/agentverify-rules-v1.schema.json",
    }
)


def latest_wheel(dist_dir: Path) -> Path:
    wheels = sorted(dist_dir.glob("agentverify-*.whl"), key=lambda path: path.stat().st_mtime)
    if not wheels:
        raise FileNotFoundError(f"no agentverify wheel found in {dist_dir}")
    return wheels[-1]


def wheel_names(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return set(archive.namelist())


def verify_wheel(path: Path) -> dict[str, object]:
    names = wheel_names(path)
    missing = sorted(REQUIRED_SCHEMA_FILES - names)
    present = sorted(REQUIRED_SCHEMA_FILES & names)
    payload: dict[str, object] = {
        "wheel": str(path),
        "required_schema_files": len(REQUIRED_SCHEMA_FILES),
        "present_schema_files": present,
        "missing_schema_files": missing,
        "passed": not missing,
    }
    if missing:
        raise RuntimeError(json.dumps(payload, indent=2))
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that an AgentVerify wheel contains required runtime schemas."
    )
    parser.add_argument(
        "wheel",
        nargs="?",
        type=Path,
        help="wheel to inspect; defaults to the newest agentverify wheel in --dist-dir",
    )
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        wheel = args.wheel if args.wheel is not None else latest_wheel(args.dist_dir)
        payload = verify_wheel(wheel)
    except (FileNotFoundError, RuntimeError, zipfile.BadZipFile) as error:
        print(f"agentverify distribution verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2) + "\n", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

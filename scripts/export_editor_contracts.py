"""Export AgentVerify contracts useful for editor and CI integrations."""

from __future__ import annotations

import argparse
from pathlib import Path

from agentverify.contracts import export_editor_contracts, render_editor_contract_manifest


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
    print(render_editor_contract_manifest(manifest), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

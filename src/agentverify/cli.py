"""Command-line interface for AgentVerify."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .report import render_json, render_sarif, render_text
from .scanner import scan_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentverify", description="Analyze AI agent applications"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan", help="scan a repository")
    scan.add_argument("path", type=Path)
    scan.add_argument("--format", choices=("text", "json", "sarif"), default="text")
    scan.add_argument("--fail-on", choices=("none", "medium", "high"), default="none")
    scan.add_argument(
        "--include-tests", action="store_true", help="include findings from test and fixture paths"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.path.is_dir():
        print(f"agentverify: not a directory: {args.path}", file=sys.stderr)
        return 2
    ir = scan_repository(args.path, include_tests=args.include_tests)
    try:
        report = {
            "json": render_json,
            "sarif": render_sarif,
            "text": render_text,
        }[args.format](ir)
        print(report, end="")
    except BrokenPipeError:
        return 0
    severities = {finding.severity for finding in ir.findings}
    if args.fail_on == "high" and "high" in severities:
        return 1
    if args.fail_on == "medium" and severities & {"medium", "high"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

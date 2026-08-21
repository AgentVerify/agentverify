"""Command-line interface for AgentVerify."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .policy import SEVERITY_RANK, PolicyError, evaluate_policy, load_policy
from .report import render_bom, render_json, render_sarif, render_schema, render_text
from .scanner import scan_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentverify", description="Analyze AI agent applications"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan", help="scan a repository")
    scan.add_argument("path", type=Path)
    scan.add_argument("--format", choices=("text", "json", "bom", "sarif"), default="text")
    scan.add_argument("--fail-on", choices=("none", "medium", "high"), default="none")
    scan.add_argument(
        "--fail-on-kind",
        choices=("finding", "review", "any"),
        default="finding",
        help="result kind considered by --fail-on (default: finding)",
    )
    scan.add_argument(
        "--include-tests", action="store_true", help="include findings from test and fixture paths"
    )
    scan.add_argument(
        "--baseline",
        type=Path,
        help="suppress fingerprints in a previous AgentVerify JSON, AI BOM, or SARIF report",
    )
    scan.add_argument(
        "--paths-from",
        type=Path,
        help="scan only repository-relative files/directories listed one per line",
    )
    scan.add_argument(
        "--require-suppression-expiry",
        action="store_true",
        help="keep inline-suppressed findings unless the directive has an active ISO expiry date",
    )
    scan.add_argument(
        "--policy",
        type=Path,
        help="evaluate a schema-v1 JSON policy against post-baseline results",
    )
    schema = subparsers.add_parser("schema", help="print a bundled machine-readable schema")
    schema.add_argument("name", choices=("bom", "policy"))
    return parser


def baseline_fingerprints(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return {str(item) for item in payload}
    if not isinstance(payload, dict):
        raise TypeError("baseline must be a JSON object or fingerprint list")
    if isinstance(payload.get("findings"), list):
        return {
            str(item["fingerprint"])
            for item in payload["findings"]
            if isinstance(item, dict) and item.get("fingerprint")
        }
    if payload.get("bom_format") == "AgentVerify AI BOM" and isinstance(payload.get("risks"), list):
        return {
            str(item["id"])
            for item in payload["risks"]
            if isinstance(item, dict) and item.get("id")
        }
    fingerprints = set()
    for run in payload.get("runs", []):
        for result in run.get("results", []):
            values = result.get("partialFingerprints", {})
            if values.get("agentverify/v1"):
                fingerprints.add(str(values["agentverify/v1"]))
    return fingerprints


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "schema":
        try:
            print(render_schema(args.name), end="")
        except BrokenPipeError:
            return 0
        return 0
    if not args.path.is_dir():
        print(f"agentverify: not a directory: {args.path}", file=sys.stderr)
        return 2
    selected_paths = None
    if args.paths_from:
        try:
            selected_paths = args.paths_from.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            print(f"agentverify: invalid path list: {error}", file=sys.stderr)
            return 2
    loaded_policy = None
    policy_digest = None
    if args.policy:
        try:
            loaded_policy, policy_digest = load_policy(args.policy)
        except (OSError, PolicyError) as error:
            print(f"agentverify: invalid policy: {error}", file=sys.stderr)
            return 2
    try:
        ir = scan_repository(
            args.path,
            include_tests=args.include_tests,
            selected_paths=selected_paths,
            require_suppression_expiry=args.require_suppression_expiry,
        )
    except ValueError as error:
        print(f"agentverify: invalid path list: {error}", file=sys.stderr)
        return 2
    if args.baseline:
        try:
            known = baseline_fingerprints(args.baseline)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            print(f"agentverify: invalid baseline: {error}", file=sys.stderr)
            return 2
        current = {finding.fingerprint for finding in ir.findings}
        unchanged = current & known
        new = current - known
        ir.findings = [finding for finding in ir.findings if finding.fingerprint in new]
        ir.suppressed_findings += len(unchanged)
        ir.baseline_summary = {
            "baseline_fingerprints": len(known),
            "current_fingerprints": len(current),
            "new": len(new),
            "unchanged": len(unchanged),
            "no_longer_reported": len(known - current) if ir.scan_scope == "repository" else None,
        }
    policy_passed = True
    if args.policy and loaded_policy is not None and policy_digest is not None:
        policy_passed = evaluate_policy(
            ir, loaded_policy, source=args.policy.name, digest=policy_digest
        )
    try:
        report = {
            "bom": render_bom,
            "json": render_json,
            "sarif": render_sarif,
            "text": render_text,
        }[args.format](ir)
        print(report, end="")
    except BrokenPipeError:
        return 0
    considered = [
        finding
        for finding in ir.findings
        if args.fail_on_kind == "any" or finding.result_kind == args.fail_on_kind
    ]
    threshold_failed = args.fail_on != "none" and any(
        SEVERITY_RANK.get(finding.severity, 0) >= SEVERITY_RANK[args.fail_on]
        for finding in considered
    )
    if threshold_failed or not policy_passed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

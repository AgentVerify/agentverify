"""Command-line interface for AgentVerify."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .policy import SEVERITY_RANK, PolicyError, evaluate_policy, load_policy
from .report import (
    render_bom,
    render_json,
    render_rules,
    render_sarif,
    render_schema,
    render_summary,
    render_text,
)
from .rules import RULE_CATALOG
from .scanner import scan_repository


def _fingerprints_from_objects(items: object, *, field: str, baseline_kind: str) -> set[str]:
    if not isinstance(items, list):
        raise TypeError(f"{baseline_kind} baseline must contain a {field} array")
    fingerprints = set()
    fingerprint_key = "fingerprint" if field == "findings" else "id"
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not item.get(fingerprint_key):
            raise TypeError(
                f"{baseline_kind} baseline {field}[{index}] must contain a {fingerprint_key} string"
            )
        if not isinstance(item[fingerprint_key], str):
            raise TypeError(
                f"{baseline_kind} baseline {field}[{index}].{fingerprint_key} must be a string"
            )
        fingerprints.add(item[fingerprint_key])
    return fingerprints


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentverify", description="Analyze AI agent applications"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan", help="scan a repository")
    scan.add_argument("path", type=Path)
    scan.add_argument(
        "--format", choices=("text", "summary", "json", "bom", "sarif"), default="text"
    )
    scan.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="PATH",
        help="write the report to PATH instead of standard output",
    )
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
    schema.add_argument("name", choices=("bom", "policy", "report", "rules"))
    schema.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="PATH",
        help="write the schema to PATH instead of standard output",
    )
    rules = subparsers.add_parser("rules", help="list enabled reporting rules")
    rules.add_argument("rule_id", nargs="?", choices=tuple(RULE_CATALOG))
    rules.add_argument("--format", choices=("text", "json"), default="text")
    rules.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="PATH",
        help="write rule metadata to PATH instead of standard output",
    )
    return parser


def baseline_fingerprints(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        if not all(isinstance(item, str) and item for item in payload):
            raise TypeError("fingerprint list baseline must contain only non-empty strings")
        return set(payload)
    if not isinstance(payload, dict):
        raise TypeError("baseline must be a JSON object or fingerprint list")
    if payload.get("report_format") == "AgentVerify JSON Report" or "findings" in payload:
        return _fingerprints_from_objects(
            payload.get("findings"), field="findings", baseline_kind="AgentVerify JSON"
        )
    if payload.get("bom_format") == "AgentVerify AI BOM":
        return _fingerprints_from_objects(
            payload.get("risks"), field="risks", baseline_kind="AgentVerify AI BOM"
        )
    if "runs" not in payload:
        raise TypeError(
            "baseline must be an AgentVerify JSON report, AI BOM, SARIF report, or fingerprint list"
        )
    if not isinstance(payload.get("runs"), list):
        raise TypeError("SARIF baseline must contain a runs array")
    fingerprints = set()
    other_results = 0
    for run in payload["runs"]:
        if not isinstance(run, dict):
            continue
        tool = run.get("tool", {})
        driver = tool.get("driver", {}) if isinstance(tool, dict) else {}
        is_agentverify_run = isinstance(driver, dict) and driver.get("name") == "AgentVerify"
        results = run.get("results", [])
        if not isinstance(results, list):
            raise TypeError("SARIF baseline runs[].results must be an array")
        for result in results:
            if not isinstance(result, dict):
                continue
            if not is_agentverify_run:
                other_results += 1
            values = result.get("partialFingerprints", {})
            if isinstance(values, dict) and values.get("agentverify/v1"):
                if not isinstance(values["agentverify/v1"], str):
                    raise TypeError(
                        "SARIF baseline partialFingerprints.agentverify/v1 must be a string"
                    )
                fingerprints.add(str(values["agentverify/v1"]))
            elif is_agentverify_run:
                raise TypeError(
                    "AgentVerify SARIF baseline results must contain "
                    "partialFingerprints.agentverify/v1"
                )
    if not fingerprints and other_results:
        raise TypeError("SARIF baseline does not contain AgentVerify fingerprints")
    return fingerprints


def emit_output(content: str, output: Path | None) -> int | None:
    """Emit content and return an early CLI exit code only on handled I/O conditions."""
    if output is None:
        try:
            print(content, end="")
        except BrokenPipeError:
            return 0
        return None
    try:
        output.write_text(content, encoding="utf-8")
    except OSError as error:
        print(f"agentverify: cannot write output: {error}", file=sys.stderr)
        return 2
    return None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "schema":
        return emit_output(render_schema(args.name), args.output) or 0
    if args.command == "rules":
        return emit_output(render_rules(args.rule_id, output_format=args.format), args.output) or 0
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
    report = {
        "bom": render_bom,
        "json": render_json,
        "sarif": render_sarif,
        "summary": render_summary,
        "text": render_text,
    }[args.format](ir)
    if (output_exit := emit_output(report, args.output)) is not None:
        return output_exit
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

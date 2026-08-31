"""Command-line interface for AgentVerify."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .benchmark import (
    BENCHMARK_VERIFICATION_ERRORS,
    DEFAULT_BENCHMARK_RESULTS,
    DEFAULT_ENGINE_RESULTS,
    ENGINE_RESULTS_VERIFICATION_ERRORS,
    render_benchmark_verification,
    render_engine_results_verification,
    render_engine_results_verification_summary,
    verify_benchmark_results,
    verify_engine_results,
)
from .contracts import (
    CONTRACT_VERIFICATION_ERRORS,
    export_editor_contracts,
    render_editor_contract_manifest,
    render_editor_contract_verification,
    verify_editor_contracts,
)
from .holdout import (
    HOLDOUT_VALIDATION_ERRORS,
    render_holdout_validation,
    validate_holdout_files,
)
from .policy import (
    SEVERITY_RANK,
    PolicyError,
    evaluate_policy,
    load_policy,
    load_policy_key_trust_root,
    load_policy_signature,
    load_policy_trust_root,
    policy_summary,
    render_policy_signing_payload,
    render_policy_summary,
    render_policy_trust_root,
)
from .report import (
    SCHEMA_FILES,
    render_bom,
    render_json,
    render_rules,
    render_sarif,
    render_schema,
    render_schema_list,
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
    schema = subparsers.add_parser("schema", help="list or print bundled machine-readable schemas")
    schema.add_argument(
        "name",
        nargs="?",
        choices=tuple(SCHEMA_FILES),
        help="schema name; omit to list available schemas",
    )
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
    contracts = subparsers.add_parser(
        "contracts", help="export editor and CI integration contract artifacts"
    )
    contracts.add_argument(
        "--output-dir",
        type=Path,
        default=Path("agentverify-editor-contracts"),
        help="directory to create or update with exported contract artifacts",
    )
    contracts.add_argument(
        "--sample-root",
        type=Path,
        help="optional repository path to scan and include as agentverify-sample-report.json",
    )
    contracts.add_argument(
        "--verify-dir",
        type=Path,
        metavar="PATH",
        help="verify an exported contract bundle directory instead of exporting a new bundle",
    )
    contracts.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="PATH",
        help="write the export manifest to PATH instead of standard output",
    )
    policy = subparsers.add_parser("policy", help="validate and explain a schema-v1 policy")
    policy.add_argument("path", type=Path)
    policy.add_argument("--format", choices=("text", "json"), default="text")
    policy.add_argument(
        "--export-trust-root",
        action="store_true",
        help="emit a schema-v1 local digest allowlist for this composed policy",
    )
    policy.add_argument(
        "--export-signing-payload",
        action="store_true",
        help="emit a deterministic source-digest payload for external policy signing",
    )
    policy.add_argument(
        "--trust-root",
        type=Path,
        help=(
            "validate composed policy content against a schema-v1 local digest allowlist, "
            "or against a local key trust root when --signature is supplied"
        ),
    )
    policy.add_argument(
        "--signature",
        type=Path,
        help="verify a schema-v1 detached policy signature bundle with --trust-root keys",
    )
    policy.add_argument(
        "--require-trusted",
        action="store_true",
        help="return exit code 1 unless policy trust verification succeeds",
    )
    policy.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="PATH",
        help="write policy metadata to PATH instead of standard output",
    )
    benchmark = subparsers.add_parser("benchmark", help="verify benchmark result artifacts")
    benchmark_subparsers = benchmark.add_subparsers(dest="benchmark_command", required=True)
    benchmark_verify = benchmark_subparsers.add_parser(
        "verify", help="validate benchmark results and input digests"
    )
    benchmark_verify.add_argument(
        "results",
        nargs="*",
        type=Path,
        default=list(DEFAULT_BENCHMARK_RESULTS),
        help="benchmark result JSON files; defaults to the checked-in public results",
    )
    benchmark_verify.add_argument(
        "--schema",
        type=Path,
        help="benchmark-result schema; defaults to the AgentVerify bundled schema",
    )
    benchmark_verify.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="repository root used to resolve relative labels_source and manifest_source values",
    )
    benchmark_verify.add_argument(
        "--require-evaluation-kind",
        choices=("public-regression", "sealed-holdout"),
        help="fail unless every result declares this benchmark evaluation kind",
    )
    benchmark_verify.add_argument(
        "--require-label-scope",
        choices=("reporting-rules", "agent-ir", "mixed"),
        help="fail unless every result declares this label scope",
    )
    benchmark_verify.add_argument(
        "--require-sealed",
        action="store_true",
        help="fail unless every result declares sealed=true",
    )
    benchmark_verify.add_argument(
        "--require-manifest",
        action="store_true",
        help="fail unless every result declares a manifest source and matching digest",
    )
    benchmark_verify.add_argument(
        "--require-all-passed",
        action="store_true",
        help="fail unless every result has passed equal to labels",
    )
    benchmark_verify.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="PATH",
        help="write verification JSON to PATH instead of standard output",
    )
    benchmark_verify_engine = benchmark_subparsers.add_parser(
        "verify-engine", help="validate engine-results JSON snapshots"
    )
    benchmark_verify_engine.add_argument(
        "result",
        nargs="?",
        type=Path,
        default=DEFAULT_ENGINE_RESULTS,
        help="engine-results JSON file; defaults to the checked-in public engine snapshot",
    )
    benchmark_verify_engine.add_argument(
        "--schema",
        type=Path,
        help="engine-results schema; defaults to the AgentVerify bundled schema",
    )
    benchmark_verify_engine.add_argument(
        "--format",
        choices=("json", "summary"),
        default="json",
        help="verification output format; defaults to json",
    )
    benchmark_verify_engine.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="PATH",
        help="write verification output to PATH instead of standard output",
    )
    holdout = subparsers.add_parser("holdout", help="validate holdout setup artifacts")
    holdout_subparsers = holdout.add_subparsers(dest="holdout_command", required=True)
    holdout_validate = holdout_subparsers.add_parser(
        "validate", help="validate holdout manifest and label files"
    )
    holdout_validate.add_argument(
        "--manifest",
        type=Path,
        help="holdout manifest JSON file to validate against the bundled manifest schema",
    )
    holdout_validate.add_argument(
        "--labels",
        type=Path,
        help="holdout labels JSON file to validate against the bundled labels schema",
    )
    holdout_validate.add_argument("--format", choices=("text", "json"), default="text")
    holdout_validate.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="PATH",
        help="write validation output to PATH instead of standard output",
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
        return (
            emit_output(
                render_schema(args.name) if args.name is not None else render_schema_list(),
                args.output,
            )
            or 0
        )
    if args.command == "rules":
        return emit_output(render_rules(args.rule_id, output_format=args.format), args.output) or 0
    if args.command == "contracts":
        if args.verify_dir is not None:
            if args.sample_root is not None:
                print("agentverify: --verify-dir cannot be combined with --sample-root", file=sys.stderr)
                return 2
            try:
                verification = verify_editor_contracts(args.verify_dir)
            except CONTRACT_VERIFICATION_ERRORS as error:
                print(f"agentverify: cannot verify contracts: {error}", file=sys.stderr)
                return 2
            output_error = emit_output(render_editor_contract_verification(verification), args.output)
            if output_error:
                return output_error
            return 0 if verification["passed"] is True else 1
        try:
            manifest = export_editor_contracts(args.output_dir, sample_root=args.sample_root)
        except OSError as error:
            print(f"agentverify: cannot export contracts: {error}", file=sys.stderr)
            return 2
        return emit_output(render_editor_contract_manifest(manifest), args.output) or 0
    if args.command == "benchmark":
        if args.benchmark_command == "verify-engine":
            try:
                payload = verify_engine_results(args.result, schema_path=args.schema)
            except ENGINE_RESULTS_VERIFICATION_ERRORS as error:
                print(f"agentverify: engine-results verification failed: {error}", file=sys.stderr)
                return 2
            rendered = (
                render_engine_results_verification_summary(payload)
                if args.format == "summary"
                else render_engine_results_verification(payload)
            )
            return emit_output(rendered, args.output) or 0
        try:
            payload = verify_benchmark_results(
                args.results,
                schema_path=args.schema,
                root=args.root,
                evaluation_kind=args.require_evaluation_kind,
                label_scope=args.require_label_scope,
                require_sealed=args.require_sealed,
                require_manifest=args.require_manifest,
                require_all_passed=args.require_all_passed,
            )
        except BENCHMARK_VERIFICATION_ERRORS as error:
            print(f"agentverify: benchmark verification failed: {error}", file=sys.stderr)
            return 2
        return emit_output(render_benchmark_verification(payload), args.output) or 0
    if args.command == "holdout":
        if args.manifest is None and args.labels is None:
            print(
                "agentverify: holdout validate requires --manifest, --labels, or both",
                file=sys.stderr,
            )
            return 2
        try:
            payload = validate_holdout_files(manifest=args.manifest, labels=args.labels)
        except HOLDOUT_VALIDATION_ERRORS as error:
            print(f"agentverify: holdout validation failed: {error}", file=sys.stderr)
            return 2
        output_error = emit_output(
            render_holdout_validation(payload, output_format=args.format), args.output
        )
        if output_error:
            return output_error
        return 0 if payload["passed"] is True else 2
    if args.command == "policy":
        if args.export_trust_root and args.export_signing_payload:
            print(
                "agentverify: --export-trust-root cannot be combined with --export-signing-payload",
                file=sys.stderr,
            )
            return 2
        if (args.export_trust_root or args.export_signing_payload) and (
            args.trust_root or args.require_trusted or args.signature
        ):
            print(
                "agentverify: export options cannot be combined with "
                "--trust-root, --signature, or --require-trusted",
                file=sys.stderr,
            )
            return 2
        if args.signature and not args.trust_root:
            print("agentverify: --signature requires --trust-root", file=sys.stderr)
            return 2
        if args.require_trusted and not args.trust_root:
            print("agentverify: --require-trusted requires --trust-root", file=sys.stderr)
            return 2
        try:
            loaded_policy, policy_digest = load_policy(args.path)
        except (OSError, PolicyError) as error:
            print(f"agentverify: invalid policy: {error}", file=sys.stderr)
            return 2
        if args.export_trust_root:
            return emit_output(render_policy_trust_root(loaded_policy), args.output) or 0
        if args.export_signing_payload:
            return (
                emit_output(
                    render_policy_signing_payload(
                        loaded_policy,
                        source=args.path.name,
                        digest=policy_digest,
                    ),
                    args.output,
                )
                or 0
            )
        trust_root = None
        trust_root_digest = None
        key_trust_root = None
        key_trust_root_digest = None
        signature_bundle = None
        signature_digest = None
        if args.trust_root:
            if args.signature:
                try:
                    key_trust_root, key_trust_root_digest = load_policy_key_trust_root(
                        args.trust_root
                    )
                except (OSError, PolicyError) as error:
                    print(f"agentverify: invalid policy key trust root: {error}", file=sys.stderr)
                    return 2
            else:
                try:
                    trust_root, trust_root_digest = load_policy_trust_root(args.trust_root)
                except (OSError, PolicyError) as error:
                    print(f"agentverify: invalid policy trust root: {error}", file=sys.stderr)
                    return 2
        if args.signature:
            try:
                signature_bundle, signature_digest = load_policy_signature(args.signature)
            except (OSError, PolicyError) as error:
                print(f"agentverify: invalid policy signature: {error}", file=sys.stderr)
                return 2
        report = render_policy_summary(
            loaded_policy,
            source=args.path.name,
            digest=policy_digest,
            output_format=args.format,
            trust_root=trust_root,
            trust_root_source=args.trust_root.name if args.trust_root else None,
            trust_root_digest=trust_root_digest,
            key_trust_root=key_trust_root,
            key_trust_root_source=args.trust_root.name if args.signature else None,
            key_trust_root_digest=key_trust_root_digest,
            signature_bundle=signature_bundle,
            signature_source=args.signature.name if args.signature else None,
            signature_digest=signature_digest,
        )
        trusted = True
        if signature_bundle is not None:
            summary = policy_summary(
                loaded_policy,
                source=args.path.name,
                digest=policy_digest,
                key_trust_root=key_trust_root,
                key_trust_root_source=args.trust_root.name,
                key_trust_root_digest=key_trust_root_digest,
                signature_bundle=signature_bundle,
                signature_source=args.signature.name,
                signature_digest=signature_digest,
            )
            trusted = bool(summary["trust"]["signature_verified"])
        elif trust_root is not None:
            summary = policy_summary(
                loaded_policy,
                source=args.path.name,
                digest=policy_digest,
                trust_root=trust_root,
                trust_root_source=args.trust_root.name,
                trust_root_digest=trust_root_digest,
            )
            trusted = bool(summary["trust"]["trust_root"]["trusted"])
        if (output_exit := emit_output(report, args.output)) is not None:
            return output_exit
        if args.require_trusted and not trusted:
            return 1
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

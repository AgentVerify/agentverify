"""Validate benchmark result files and their embedded input provenance."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentverify.benchmark import (
    BENCHMARK_VERIFICATION_ERRORS,
    DEFAULT_BENCHMARK_RESULTS,
    enforce_release_requirements,
    file_sha256,
    load_benchmark_result_schema,
    render_benchmark_verification,
    resolve_source,
    verify_benchmark_results,
    verify_result,
    verify_result_for_release,
)

DEFAULT_RESULTS = DEFAULT_BENCHMARK_RESULTS
load_schema = load_benchmark_result_schema

__all__ = [
    "BENCHMARK_VERIFICATION_ERRORS",
    "DEFAULT_RESULTS",
    "enforce_release_requirements",
    "file_sha256",
    "load_schema",
    "main",
    "parse_args",
    "resolve_source",
    "verify_benchmark_results",
    "verify_result",
    "verify_result_for_release",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate AgentVerify benchmark results and input digests."
    )
    parser.add_argument("results", nargs="*", type=Path, default=list(DEFAULT_RESULTS))
    parser.add_argument(
        "--schema",
        type=Path,
        help="benchmark-result schema; defaults to the AgentVerify bundled schema",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="repository root used to resolve relative labels_source and manifest_source values",
    )
    parser.add_argument(
        "--require-evaluation-kind",
        choices=("public-regression", "sealed-holdout"),
        help="fail unless every result declares this benchmark evaluation kind",
    )
    parser.add_argument(
        "--require-label-scope",
        choices=("reporting-rules", "agent-ir", "mixed"),
        help="fail unless every result declares this label scope",
    )
    parser.add_argument(
        "--require-sealed",
        action="store_true",
        help="fail unless every result declares sealed=true",
    )
    parser.add_argument(
        "--require-manifest",
        action="store_true",
        help="fail unless every result declares a manifest source and matching digest",
    )
    parser.add_argument(
        "--require-all-passed",
        action="store_true",
        help="fail unless every result has passed equal to labels",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
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
        print(f"agentverify benchmark verification failed: {error}", file=sys.stderr)
        return 1
    print(render_benchmark_verification(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

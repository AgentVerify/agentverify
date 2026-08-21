"""Run the AgentVerify engine against every pinned repository checkout."""

from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from agentverify.scanner import scan_repository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("research/corpus.csv"))
    parser.add_argument("--cache-dir", type=Path, default=Path(".agentverify-cache/repositories"))
    parser.add_argument("--output", type=Path, default=Path("benchmarks/engine-results.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with args.corpus.open(newline="", encoding="utf-8") as handle:
        repositories = list(csv.DictReader(handle))
    results = []
    started = time.perf_counter()
    for index, row in enumerate(repositories, start=1):
        repository = row["repository"]
        checkout = args.cache_dir / repository.replace("/", "--")
        if not checkout.is_dir():
            results.append({"repository": repository, "status": "missing"})
            continue
        repo_started = time.perf_counter()
        ir = scan_repository(checkout)
        result = {
            "repository": repository,
            "status": "ok",
            "files_scanned": ir.files_scanned,
            "config_files_scanned": ir.config_files_scanned,
            "components": dict(sorted(Counter(item.kind for item in ir.components).items())),
            "relationships": len(ir.relationships),
            "findings": dict(sorted(Counter(item.rule_id for item in ir.findings).items())),
            "parse_warnings": len(ir.errors),
            "parse_warning_details": ir.errors[:10],
            "elapsed_seconds": round(time.perf_counter() - repo_started, 4),
        }
        results.append(result)
        print(f"[{index:>2}/{len(repositories)}] {repository}: {ir.files_scanned} files")
    successful = [result for result in results if result["status"] == "ok"]
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "defaults": {"include_tests": False},
        "summary": {
            "repositories": len(results),
            "successful": len(successful),
            "source_bearing": sum(result["files_scanned"] > 0 for result in successful),
            "zero_source_repositories": [
                result["repository"] for result in successful if result["files_scanned"] == 0
            ],
            "files_scanned": sum(result["files_scanned"] for result in successful),
            "config_files_scanned": sum(result["config_files_scanned"] for result in successful),
            "relationships": sum(result["relationships"] for result in successful),
            "parse_warnings": sum(result["parse_warnings"] for result in successful),
            "findings": dict(
                sorted(
                    sum((Counter(result["findings"]) for result in successful), Counter()).items()
                )
            ),
            "elapsed_seconds": round(time.perf_counter() - started, 4),
        },
        "repositories": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    return 0 if len(successful) == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

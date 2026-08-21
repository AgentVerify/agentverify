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

PUBLISHED_NAME_KINDS = {
    "capability",
    "control",
    "control-setting",
    "framework",
    "protocol",
    "provider",
    "sandbox-boundary",
}


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
        imported_edges = [edge for edge in ir.relationships if edge.attributes.get("target_path")]
        component_symbol_ids = {item.symbol_id for item in ir.components if item.symbol_id}
        relationship_symbol_ids = [
            symbol_id
            for edge in ir.relationships
            for symbol_id in (edge.source_id, edge.target_id)
            if symbol_id
        ]
        typescript_agent_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "agent"
            and edge.evidence.path.endswith((".ts", ".tsx", ".js", ".jsx"))
        ]
        typescript_agent_tool_edges = [
            edge for edge in typescript_agent_edges if edge.target_kind == "tool"
        ]
        result = {
            "repository": repository,
            "category": row["category"],
            "status": "ok",
            "files_scanned": ir.files_scanned,
            "config_files_scanned": ir.config_files_scanned,
            "components": dict(sorted(Counter(item.kind for item in ir.components).items())),
            "component_names": {
                kind: sorted({item.name for item in ir.components if item.kind == kind})
                for kind in sorted(PUBLISHED_NAME_KINDS)
                if any(item.kind == kind for item in ir.components)
            },
            "relationships": len(ir.relationships),
            "symbolized_components": sum(bool(item.symbol_id) for item in ir.components),
            "identified_symbol_endpoints": len(relationship_symbol_ids),
            "resolved_symbol_endpoints": sum(
                symbol_id in component_symbol_ids for symbol_id in relationship_symbol_ids
            ),
            "unmatched_identified_symbol_endpoints": sum(
                symbol_id not in component_symbol_ids for symbol_id in relationship_symbol_ids
            ),
            "resolved_symbol_endpoints_by_frontend": {
                frontend: sum(
                    symbol_id.startswith(f"{frontend}:") and symbol_id in component_symbol_ids
                    for symbol_id in relationship_symbol_ids
                )
                for frontend in ("py", "ts")
            },
            "typescript_graph": {
                "agent_edges": len(typescript_agent_edges),
                "agent_delegations": sum(
                    edge.relation == "delegates-to" for edge in typescript_agent_edges
                ),
                "agent_tool_edges": len(typescript_agent_tool_edges),
                "resolved_agent_tool_edges": sum(
                    edge.target_id in component_symbol_ids for edge in typescript_agent_tool_edges
                ),
            },
            "resolved_import_edges": len(imported_edges),
            "resolved_import_edges_by_frontend": {
                "python": sum(edge.evidence.path.endswith(".py") for edge in imported_edges),
                "typescript": sum(
                    edge.evidence.path.endswith((".ts", ".tsx", ".js", ".jsx"))
                    for edge in imported_edges
                ),
            },
            "findings": dict(sorted(Counter(item.rule_id for item in ir.findings).items())),
            "suppressed_findings": ir.suppressed_findings,
            "parse_warnings": len(ir.errors),
            "parse_warning_details": ir.errors[:10],
            "elapsed_seconds": round(time.perf_counter() - repo_started, 4),
        }
        results.append(result)
        print(f"[{index:>2}/{len(repositories)}] {repository}: {ir.files_scanned} files")
    successful = [result for result in results if result["status"] == "ok"]
    payload = {
        "schema_version": 3,
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
            "symbolized_components": sum(result["symbolized_components"] for result in successful),
            "identified_symbol_endpoints": sum(
                result["identified_symbol_endpoints"] for result in successful
            ),
            "resolved_symbol_endpoints": sum(
                result["resolved_symbol_endpoints"] for result in successful
            ),
            "unmatched_identified_symbol_endpoints": sum(
                result["unmatched_identified_symbol_endpoints"] for result in successful
            ),
            "relationship_endpoints": 2 * sum(result["relationships"] for result in successful),
            "resolved_symbol_endpoints_by_frontend": {
                frontend: sum(
                    result["resolved_symbol_endpoints_by_frontend"][frontend]
                    for result in successful
                )
                for frontend in ("py", "ts")
            },
            "typescript_graph": {
                name: sum(result["typescript_graph"][name] for result in successful)
                for name in (
                    "agent_edges",
                    "agent_delegations",
                    "agent_tool_edges",
                    "resolved_agent_tool_edges",
                )
            },
            "resolved_import_edges": sum(result["resolved_import_edges"] for result in successful),
            "resolved_import_edges_by_frontend": {
                frontend: sum(
                    result["resolved_import_edges_by_frontend"][frontend] for result in successful
                )
                for frontend in ("python", "typescript")
            },
            "parse_warnings": sum(result["parse_warnings"] for result in successful),
            "suppressed_findings": sum(result["suppressed_findings"] for result in successful),
            "findings": dict(
                sorted(
                    sum((Counter(result["findings"]) for result in successful), Counter()).items()
                )
            ),
            "observed_component_names": {
                kind: dict(
                    sorted(
                        Counter(
                            name
                            for result in successful
                            for name in result["component_names"].get(kind, [])
                        ).items()
                    )
                )
                for kind in sorted(
                    {kind for result in successful for kind in result["component_names"]}
                )
            },
            "category_coverage": {
                category: {
                    "repositories": len(rows),
                    "source_bearing": sum(row["files_scanned"] > 0 for row in rows),
                    **{
                        f"with_{kind}": sum(bool(row["component_names"].get(kind)) for row in rows)
                        for kind in ("framework", "provider", "protocol", "capability")
                    },
                }
                for category in sorted({result["category"] for result in successful})
                if (rows := [result for result in successful if result["category"] == category])
            },
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

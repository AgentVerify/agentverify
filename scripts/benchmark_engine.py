"""Run the AgentVerify engine against every pinned repository checkout."""

from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from agentverify.report import render_bom
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
    parser.add_argument(
        "--repository-data",
        type=Path,
        default=Path("research/repository-data.json"),
    )
    parser.add_argument("--cache-dir", type=Path, default=Path(".agentverify-cache/repositories"))
    parser.add_argument("--output", type=Path, default=Path("benchmarks/engine-results.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with args.corpus.open(newline="", encoding="utf-8") as handle:
        repositories = list(csv.DictReader(handle))
    repository_data = (
        json.loads(args.repository_data.read_text(encoding="utf-8"))
        if args.repository_data.is_file()
        else {"method": {}, "repositories": []}
    )
    dependency_files = {
        item["repository"]: int(item.get("dependency_files_materialized", 0))
        for item in repository_data.get("repositories", [])
    }
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
        bom = json.loads(render_bom(ir))
        bom_endpoint_resolutions = Counter(
            endpoint["resolution"]
            for relationship in bom["relationships"]
            for endpoint in (relationship["source"], relationship["target"])
        )
        bom_ambiguous_endpoints = Counter(
            f"{side}:{relationship[side]['kind']}"
            for relationship in bom["relationships"]
            for side in ("source", "target")
            if relationship[side]["resolution"] == "ambiguous"
        )
        imported_edges = [edge for edge in ir.relationships if edge.attributes.get("target_path")]
        repeated_binding_targets = [
            edge
            for edge in ir.relationships
            if edge.attributes.get("target_identity") == "ambiguous-repeated-binding"
        ]
        if any(edge.target_id is not None for edge in repeated_binding_targets):
            raise RuntimeError(
                f"{repository}: ambiguous repeated-binding target carries a symbol ID"
            )
        resolved_binding_targets = Counter(
            edge.attributes["target_identity"]
            for edge in ir.relationships
            if edge.attributes.get("target_identity")
            in {"lexical-single-definition", "module-single-definition"}
        )
        if any(
            edge.target_id is None
            for edge in ir.relationships
            if edge.attributes.get("target_identity") in resolved_binding_targets
        ):
            raise RuntimeError(f"{repository}: resolved binding target lacks a symbol ID")
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
        typescript_registered_tools = [
            item
            for item in ir.components
            if item.kind == "tool"
            and item.evidence.path.endswith((".ts", ".tsx", ".js", ".jsx"))
            and item.attributes.get("constructor") in {"createTool", "registerTool"}
        ]
        typescript_object_property_tools = [
            item
            for item in ir.components
            if item.kind == "tool"
            and item.evidence.path.endswith((".ts", ".tsx", ".js", ".jsx"))
            and item.attributes.get("binding") == "object-property"
        ]
        typescript_structured_tool_ids = {
            item.symbol_id
            for item in (*typescript_registered_tools, *typescript_object_property_tools)
            if item.symbol_id
        }
        python_post_registered_tools = [
            item
            for item in ir.components
            if item.kind == "tool"
            and item.evidence.path.endswith(".py")
            and item.attributes.get("registration") == "post-definition"
        ]
        python_post_registered_tool_ids = {
            item.symbol_id for item in python_post_registered_tools if item.symbol_id
        }
        typescript_network_helper_capabilities = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "network"
            and item.attributes.get("summary") == "same-file-helper"
        ]
        path_boundary_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "capability"
            and edge.source_name == "filesystem"
            and edge.relation == "governed-by"
            and edge.target_kind == "control"
            and edge.target_name == "path-boundary"
        ]
        typescript_path_boundary_edges = [
            edge
            for edge in path_boundary_edges
            if edge.evidence.path.endswith((".ts", ".tsx", ".js", ".jsx"))
        ]
        python_path_boundary_edges = [
            edge for edge in path_boundary_edges if edge.evidence.path.endswith(".py")
        ]
        python_path_prefix_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "capability"
            and edge.source_name == "filesystem"
            and edge.relation == "governed-by"
            and edge.target_kind == "control"
            and edge.target_name == "path-prefix-check"
            and edge.evidence.path.endswith(".py")
        ]
        python_filesystem_mutations = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "filesystem"
            and item.evidence.path.endswith(".py")
            and item.attributes.get("canonical_api")
        ]
        mcp_forwarding_control_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "capability"
            and edge.source_name == "mcp-tool-forwarding"
            and edge.relation == "governed-by"
            and edge.target_kind == "control"
        ]
        mcp_fixed_binding_edges = [
            edge
            for edge in mcp_forwarding_control_edges
            if edge.target_name == "fixed-tool-binding"
        ]
        mcp_registry_control_edges = [
            edge for edge in mcp_forwarding_control_edges if edge.target_name == "tool-registry"
        ]
        result = {
            "repository": repository,
            "category": row["category"],
            "status": "ok",
            "files_scanned": ir.files_scanned,
            "dependency_files_materialized": dependency_files.get(repository, 0),
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
            "ambiguous_repeated_binding_targets": len(repeated_binding_targets),
            "resolved_binding_targets_by_basis": dict(sorted(resolved_binding_targets.items())),
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
            "typescript_tool_registrations": {
                "mastra_create_tool": sum(
                    item.attributes.get("constructor") == "createTool"
                    for item in typescript_registered_tools
                ),
                "mcp_register_tool": sum(
                    item.attributes.get("constructor") == "registerTool"
                    for item in typescript_registered_tools
                ),
                "object_property_tools": len(typescript_object_property_tools),
                "capability_edges": sum(
                    edge.source_id in typescript_structured_tool_ids
                    and edge.target_kind == "capability"
                    for edge in ir.relationships
                ),
                "network_helper_edges": len(typescript_network_helper_capabilities),
                "path_boundary_edges": len(typescript_path_boundary_edges),
            },
            "python_tool_registrations": {
                "post_definition": len(python_post_registered_tools),
                "transparent_wrapped": sum(
                    bool(item.attributes.get("wrappers"))
                    for item in python_post_registered_tools
                ),
                "wrapper_layers": sum(
                    len(item.attributes.get("wrappers", []))
                    for item in python_post_registered_tools
                ),
                "relative_import": sum(
                    item.attributes.get("resolution")
                    == "relative-import-single-definition"
                    for item in python_post_registered_tools
                ),
                "same_module": sum(
                    item.attributes.get("resolution")
                    == "same-module-single-definition"
                    for item in python_post_registered_tools
                ),
                "approval_enabled": sum(
                    item.attributes.get("needs_approval") is True
                    for item in python_post_registered_tools
                ),
                "capability_edges": sum(
                    edge.source_id in python_post_registered_tool_ids
                    and edge.target_kind == "capability"
                    for edge in ir.relationships
                ),
            },
            "path_boundary_controls": {
                "python": len(python_path_boundary_edges),
                "typescript": len(typescript_path_boundary_edges),
                "python_relative_to": sum(
                    edge.attributes.get("helper") == "Path.relative_to"
                    for edge in python_path_boundary_edges
                ),
                "python_helper_returns": sum(
                    edge.attributes.get("summary") == "same-class-return"
                    for edge in python_path_boundary_edges
                ),
                "constrained": sum(
                    edge.attributes.get("boundary_scope") == "constrained"
                    for edge in path_boundary_edges
                ),
                "unresolved": sum(
                    edge.attributes.get("boundary_scope") != "constrained"
                    for edge in path_boundary_edges
                ),
            },
            "path_prefix_checks": {
                "python": len(python_path_prefix_edges),
                "weak_string_prefix": sum(
                    edge.attributes.get("strength") == "weak-prefix"
                    for edge in python_path_prefix_edges
                ),
            },
            "python_filesystem_mutations": {
                "total": len(python_filesystem_mutations),
                "callable_aliases": sum(
                    bool(item.attributes.get("callable_alias"))
                    for item in python_filesystem_mutations
                ),
                "pathlib_methods": sum(
                    bool(item.attributes.get("receiver_proof"))
                    for item in python_filesystem_mutations
                ),
                "dynamic_paths": sum(
                    bool(item.attributes.get("dynamic_path"))
                    for item in python_filesystem_mutations
                ),
                "guarded": sum(
                    bool(item.attributes.get("path_boundary_guard"))
                    for item in python_filesystem_mutations
                ),
                "operations": dict(
                    sorted(
                        Counter(
                            str(item.attributes.get("operation", "unresolved"))
                            for item in python_filesystem_mutations
                        ).items()
                    )
                ),
                "apis": dict(
                    sorted(
                        Counter(
                            str(item.attributes["canonical_api"])
                            for item in python_filesystem_mutations
                        ).items()
                    )
                ),
            },
            "mcp_forwarding_controls": dict(
                sorted(Counter(edge.target_name for edge in mcp_forwarding_control_edges).items())
            ),
            "mcp_fixed_binding_scopes": dict(
                sorted(
                    Counter(
                        str(edge.attributes.get("binding_scope", "unresolved"))
                        for edge in mcp_fixed_binding_edges
                    ).items()
                )
            ),
            "mcp_registry_control_sources": dict(
                sorted(
                    Counter(
                        str(edge.attributes.get("summary", "same-function-lookup"))
                        for edge in mcp_registry_control_edges
                    ).items()
                )
            ),
            "resolved_import_edges": len(imported_edges),
            "resolved_import_edges_by_frontend": {
                "python": sum(edge.evidence.path.endswith(".py") for edge in imported_edges),
                "typescript": sum(
                    edge.evidence.path.endswith((".ts", ".tsx", ".js", ".jsx"))
                    for edge in imported_edges
                ),
            },
            "bom_endpoint_resolutions": dict(sorted(bom_endpoint_resolutions.items())),
            "bom_ambiguous_endpoints_by_side_kind": dict(sorted(bom_ambiguous_endpoints.items())),
            "findings": dict(sorted(Counter(item.rule_id for item in ir.findings).items())),
            "suppressed_findings": ir.suppressed_findings,
            "parse_warnings": len(ir.errors),
            "parse_warning_details": ir.errors[:10],
            "elapsed_seconds": round(time.perf_counter() - repo_started, 4),
        }
        results.append(result)
        print(f"[{index:>2}/{len(repositories)}] {repository}: {ir.files_scanned} files")
    successful = [result for result in results if result["status"] == "ok"]
    finding_rule_ids = sorted({rule_id for result in successful for rule_id in result["findings"]})
    payload = {
        "schema_version": 23,
        "generated_at": datetime.now(UTC).isoformat(),
        "defaults": {"include_tests": False},
        "sampling": {
            key: repository_data.get("method", {}).get(key)
            for key in (
                "max_files_per_repository",
                "max_dependency_files_per_repository",
                "max_bytes_per_repository",
            )
        },
        "summary": {
            "repositories": len(results),
            "successful": len(successful),
            "source_bearing": sum(result["files_scanned"] > 0 for result in successful),
            "zero_source_repositories": [
                result["repository"] for result in successful if result["files_scanned"] == 0
            ],
            "files_scanned": sum(result["files_scanned"] for result in successful),
            "dependency_files_materialized": sum(
                result["dependency_files_materialized"] for result in successful
            ),
            "repositories_with_dependency_expansion": sum(
                result["dependency_files_materialized"] > 0 for result in successful
            ),
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
            "ambiguous_repeated_binding_targets": sum(
                result["ambiguous_repeated_binding_targets"] for result in successful
            ),
            "resolved_binding_targets_by_basis": dict(
                sorted(
                    sum(
                        (
                            Counter(result["resolved_binding_targets_by_basis"])
                            for result in successful
                        ),
                        Counter(),
                    ).items()
                )
            ),
            "relationship_endpoints": 2 * sum(result["relationships"] for result in successful),
            "bom_endpoint_resolutions": dict(
                sorted(
                    sum(
                        (Counter(result["bom_endpoint_resolutions"]) for result in successful),
                        Counter(),
                    ).items()
                )
            ),
            "bom_ambiguous_endpoints_by_side_kind": dict(
                sorted(
                    sum(
                        (
                            Counter(result["bom_ambiguous_endpoints_by_side_kind"])
                            for result in successful
                        ),
                        Counter(),
                    ).items()
                )
            ),
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
            "typescript_tool_registrations": {
                name: sum(result["typescript_tool_registrations"][name] for result in successful)
                for name in (
                    "mastra_create_tool",
                    "mcp_register_tool",
                    "object_property_tools",
                    "capability_edges",
                    "network_helper_edges",
                    "path_boundary_edges",
                )
            },
            "python_tool_registrations": {
                name: sum(result["python_tool_registrations"][name] for result in successful)
                for name in (
                    "post_definition",
                    "transparent_wrapped",
                    "wrapper_layers",
                    "relative_import",
                    "same_module",
                    "approval_enabled",
                    "capability_edges",
                )
            },
            "path_boundary_controls": {
                name: sum(result["path_boundary_controls"][name] for result in successful)
                for name in (
                    "python",
                    "typescript",
                    "python_relative_to",
                    "python_helper_returns",
                    "constrained",
                    "unresolved",
                )
            },
            "path_prefix_checks": {
                name: sum(result["path_prefix_checks"][name] for result in successful)
                for name in ("python", "weak_string_prefix")
            },
            "python_filesystem_mutations": {
                "total": sum(
                    result["python_filesystem_mutations"]["total"]
                    for result in successful
                ),
                "callable_aliases": sum(
                    result["python_filesystem_mutations"]["callable_aliases"]
                    for result in successful
                ),
                "pathlib_methods": sum(
                    result["python_filesystem_mutations"]["pathlib_methods"]
                    for result in successful
                ),
                "dynamic_paths": sum(
                    result["python_filesystem_mutations"]["dynamic_paths"]
                    for result in successful
                ),
                "guarded": sum(
                    result["python_filesystem_mutations"]["guarded"]
                    for result in successful
                ),
                "operations": dict(
                    sorted(
                        sum(
                            (
                                Counter(result["python_filesystem_mutations"]["operations"])
                                for result in successful
                            ),
                            Counter(),
                        ).items()
                    )
                ),
                "apis": dict(
                    sorted(
                        sum(
                            (
                                Counter(result["python_filesystem_mutations"]["apis"])
                                for result in successful
                            ),
                            Counter(),
                        ).items()
                    )
                ),
            },
            "mcp_forwarding_controls": dict(
                sorted(
                    sum(
                        (Counter(result["mcp_forwarding_controls"]) for result in successful),
                        Counter(),
                    ).items()
                )
            ),
            "mcp_fixed_binding_scopes": dict(
                sorted(
                    sum(
                        (Counter(result["mcp_fixed_binding_scopes"]) for result in successful),
                        Counter(),
                    ).items()
                )
            ),
            "mcp_registry_control_sources": dict(
                sorted(
                    sum(
                        (Counter(result["mcp_registry_control_sources"]) for result in successful),
                        Counter(),
                    ).items()
                )
            ),
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
            "finding_repositories": {
                rule_id: sum(bool(result["findings"].get(rule_id)) for result in successful)
                for rule_id in finding_rule_ids
            },
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
    summary = payload["summary"]
    if sum(summary["bom_endpoint_resolutions"].values()) != summary["relationship_endpoints"]:
        raise RuntimeError("AI BOM endpoint resolution counts do not cover every relationship")
    if sum(summary["bom_ambiguous_endpoints_by_side_kind"].values()) != summary[
        "bom_endpoint_resolutions"
    ].get("ambiguous", 0):
        raise RuntimeError("AI BOM ambiguous endpoint breakdown does not match its total")
    if summary["finding_repositories"].keys() != summary["findings"].keys() or any(
        summary["finding_repositories"][rule_id] > count
        for rule_id, count in summary["findings"].items()
    ):
        raise RuntimeError("finding repository counts do not match finding totals")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    return 0 if len(successful) == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

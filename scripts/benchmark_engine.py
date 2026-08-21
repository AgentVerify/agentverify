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
        python_registry_tools = [
            item
            for item in ir.components
            if item.kind == "tool"
            and item.attributes.get("registration") == "registry-decorator"
        ]
        python_registry_tool_ids = {
            item.symbol_id for item in python_registry_tools if item.symbol_id
        }
        python_browser_evaluations = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "code-execution"
            and item.attributes.get("execution_context") == "browser-page"
        ]
        python_imported_network_helpers = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "network"
            and item.attributes.get("summary") == "imported-function"
        ]
        python_imported_network_locations = {
            (item.evidence.path, item.evidence.line)
            for item in python_imported_network_helpers
        }
        python_imported_class_network_helpers = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "network"
            and item.attributes.get("summary") == "imported-class-method"
        ]
        python_imported_class_network_locations = {
            (item.evidence.path, item.evidence.line)
            for item in python_imported_class_network_helpers
        }
        python_urllib_network = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "network"
            and item.attributes.get("canonical_api") == "urllib.request.urlopen"
        ]
        python_urllib_network_locations = {
            (item.evidence.path, item.evidence.line) for item in python_urllib_network
        }
        python_network_origin_controls = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "capability"
            and edge.source_name == "network"
            and edge.relation == "governed-by"
            and edge.target_kind == "control"
            and edge.target_name == "network-origin-allowlist"
            and edge.evidence.path.endswith(".py")
        ]
        python_secure_network_controls = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "capability"
            and edge.source_name == "network"
            and edge.relation == "governed-by"
            and edge.target_kind == "control"
            and edge.target_name == "network-ssrf-policy"
            and edge.attributes.get("scope") == "production"
            and edge.attributes.get("frontend") == "python"
        ]
        typescript_secure_network_controls = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "capability"
            and edge.source_name == "network"
            and edge.relation == "governed-by"
            and edge.target_kind == "control"
            and edge.target_name == "network-ssrf-policy"
            and edge.attributes.get("scope") == "production"
            and edge.attributes.get("frontend") == "typescript"
        ]
        typescript_axios_instance_network = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "network"
            and item.attributes.get("summary") == "same-file-axios-instance"
        ]
        typescript_axios_instance_locations = {
            (item.evidence.path, item.evidence.line)
            for item in typescript_axios_instance_network
        }
        typescript_composio_cli_upload = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "network"
            and item.attributes.get("analysis")
            == "typescript-composio-cli-file-upload-flow"
        ]
        typescript_composio_cli_upload_locations = {
            (item.evidence.path, item.evidence.line)
            for item in typescript_composio_cli_upload
        }
        typescript_google_adk_openapi_rest_tool = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "network"
            and item.attributes.get("analysis")
            == "typescript-google-adk-openapi-rest-tool"
        ]
        typescript_google_adk_openapi_rest_tool_locations = {
            (item.evidence.path, item.evidence.line)
            for item in typescript_google_adk_openapi_rest_tool
        }
        python_openai_mcp_approval_default = [
            item
            for item in ir.components
            if item.kind == "control-setting"
            and item.name == "mcp-tool-approval"
            and item.attributes.get("analysis")
            == "python-openai-agents-mcp-approval-default"
        ]
        python_google_adk_bigquery_audit_controls = [
            item
            for item in ir.components
            if item.kind == "control"
            and item.name == "durable-action-audit"
            and item.attributes.get("analysis")
            == "python-google-adk-bigquery-action-audit"
        ]
        python_google_adk_bigquery_audit_storage = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "audit-storage"
            and item.attributes.get("analysis")
            == "python-google-adk-bigquery-action-audit"
        ]
        python_google_adk_bigquery_audit_settings = [
            item
            for item in ir.components
            if item.kind == "control-setting"
            and item.name == "action-audit"
            and item.attributes.get("analysis")
            == "python-google-adk-bigquery-action-audit"
        ]
        typescript_network_origin_controls = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "capability"
            and edge.source_name == "network"
            and edge.relation == "governed-by"
            and edge.target_kind == "control"
            and edge.target_name == "network-origin-policy"
            and edge.evidence.path.endswith((".ts", ".tsx", ".js", ".jsx"))
        ]
        a2a_rpc_capabilities = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "a2a-rpc"
            and item.attributes.get("scope") == "production"
        ]
        a2a_card_origin_controls = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "capability"
            and edge.source_name == "a2a-rpc"
            and edge.relation == "governed-by"
            and edge.target_kind == "control"
            and edge.target_name == "a2a-card-rpc-origin-policy"
            and edge.attributes.get("scope") == "production"
        ]
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
            "python_registry_tools": {
                "total": len(python_registry_tools),
                "functions": sum(
                    item.attributes.get("registration_target") == "function"
                    for item in python_registry_tools
                ),
                "classes": sum(
                    item.attributes.get("registration_target") == "class"
                    for item in python_registry_tools
                ),
                "resolved_entrypoints": sum(
                    item.attributes.get("registration_target") == "function"
                    or bool(item.attributes.get("entrypoints"))
                    for item in python_registry_tools
                ),
                "metagpt": sum(
                    item.attributes.get("framework") == "MetaGPT"
                    for item in python_registry_tools
                ),
                "qwen_agent": sum(
                    item.attributes.get("framework") == "Qwen-Agent"
                    for item in python_registry_tools
                ),
                "capability_edges": sum(
                    edge.source_id in python_registry_tool_ids
                    and edge.target_kind == "capability"
                    for edge in ir.relationships
                ),
            },
            "python_browser_evaluate": {
                "total": len(python_browser_evaluations),
                "dynamic": sum(
                    item.attributes.get("dynamic_input") is True
                    for item in python_browser_evaluations
                ),
                "receiver_proven": sum(
                    item.attributes.get("receiver_proof")
                    not in {None, "unresolved-browser-import-context"}
                    for item in python_browser_evaluations
                ),
                "receiver_proofs": dict(
                    sorted(
                        Counter(
                            str(item.attributes.get("receiver_proof", "unresolved"))
                            for item in python_browser_evaluations
                        ).items()
                    )
                ),
            },
            "python_imported_network_helpers": {
                "capabilities": len(python_imported_network_helpers),
                "dynamic_origins": sum(
                    bool(item.attributes.get("dynamic_origin"))
                    for item in python_imported_network_helpers
                ),
                "helpers": len(
                    {
                        (item.attributes.get("helper_path"), item.attributes.get("helper_line"))
                        for item in python_imported_network_helpers
                    }
                ),
                "capability_edges": sum(
                    edge.target_kind == "capability"
                    and edge.target_name == "network"
                    and (edge.evidence.path, edge.evidence.line)
                    in python_imported_network_locations
                    for edge in ir.relationships
                ),
            },
            "python_imported_class_network_helpers": {
                "capabilities": len(python_imported_class_network_helpers),
                "dynamic_origins": sum(
                    bool(item.attributes.get("dynamic_origin"))
                    for item in python_imported_class_network_helpers
                ),
                "callees": len(
                    {
                        (
                            item.attributes.get("callee_path"),
                            item.attributes.get("callee_class"),
                            item.attributes.get("callee_method"),
                        )
                        for item in python_imported_class_network_helpers
                    }
                ),
                "capability_edges": sum(
                    edge.target_kind == "capability"
                    and edge.target_name == "network"
                    and (edge.evidence.path, edge.evidence.line)
                    in python_imported_class_network_locations
                    for edge in ir.relationships
                ),
            },
            "python_urllib_network": {
                "capabilities": len(python_urllib_network),
                "dynamic_origins": sum(
                    bool(item.attributes.get("dynamic_origin"))
                    for item in python_urllib_network
                ),
                "capability_edges": sum(
                    edge.target_kind == "capability"
                    and edge.target_name == "network"
                    and (edge.evidence.path, edge.evidence.line)
                    in python_urllib_network_locations
                    for edge in ir.relationships
                ),
            },
            "python_network_origin_controls": {
                "total": len(python_network_origin_controls),
                "redirects_disabled": sum(
                    edge.attributes.get("redirect_scope") == "disabled"
                    for edge in python_network_origin_controls
                ),
                "redirects_unresolved": sum(
                    edge.attributes.get("redirect_scope") != "disabled"
                    for edge in python_network_origin_controls
                ),
                "dns_unresolved": sum(
                    edge.attributes.get("dns_scope") == "unresolved"
                    for edge in python_network_origin_controls
                ),
            },
            "python_secure_network_controls": {
                "total": len(python_secure_network_controls),
                "enabled_default": sum(
                    edge.attributes.get("enforcement_default") == "enabled"
                    for edge in python_secure_network_controls
                ),
                "configured_opt_out": sum(
                    edge.attributes.get("escape_hatch") == "configured-opt-out"
                    for edge in python_secure_network_controls
                ),
                "redirects_validated": sum(
                    edge.attributes.get("redirect_scope") == "each-hop-validated"
                    for edge in python_secure_network_controls
                ),
                "redirects_disabled": sum(
                    edge.attributes.get("redirect_scope") == "disabled"
                    for edge in python_secure_network_controls
                ),
                "dns_connection_pinned": sum(
                    edge.attributes.get("dns_scope") == "connection-pinned"
                    for edge in python_secure_network_controls
                ),
                "dns_connection_pinned_unless_proxied": sum(
                    edge.attributes.get("dns_scope")
                    == "connection-pinned-unless-proxied"
                    for edge in python_secure_network_controls
                ),
                "dns_connection_pinned_when_enforced": sum(
                    edge.attributes.get("dns_scope") == "connection-pinned-when-enforced"
                    for edge in python_secure_network_controls
                ),
                "proxies_disabled": sum(
                    edge.attributes.get("proxy_scope") == "disabled"
                    for edge in python_secure_network_controls
                ),
                "proxies_environment_or_caller_dependent": sum(
                    edge.attributes.get("proxy_scope")
                    == "environment-or-caller-dependent"
                    for edge in python_secure_network_controls
                ),
                "proxies_disabled_when_enforced": sum(
                    edge.attributes.get("proxy_scope") == "disabled-when-enforced"
                    for edge in python_secure_network_controls
                ),
                "redirects_disabled_default_validated_when_enabled": sum(
                    edge.attributes.get("redirect_scope")
                    == "disabled-default-each-hop-validated-when-enabled"
                    for edge in python_secure_network_controls
                ),
                "configured_allowlist_and_loopback_exemption": sum(
                    edge.attributes.get("initial_origin_scope")
                    == "public-addresses-with-configured-allowlist-and-loopback-exemption"
                    for edge in python_secure_network_controls
                ),
                "no_escape_hatch": sum(
                    edge.attributes.get("escape_hatch") == "none"
                    for edge in python_secure_network_controls
                ),
            },
            "typescript_axios_instance_network": {
                "capabilities": len(typescript_axios_instance_network),
                "dynamic_origins": sum(
                    bool(item.attributes.get("dynamic_origin"))
                    for item in typescript_axios_instance_network
                ),
                "absolute_override_allowed": sum(
                    item.attributes.get("absolute_url_override") == "allowed"
                    for item in typescript_axios_instance_network
                ),
                "absolute_override_disabled": sum(
                    item.attributes.get("absolute_url_override") == "disabled"
                    for item in typescript_axios_instance_network
                ),
                "capability_edges": sum(
                    edge.target_kind == "capability"
                    and edge.target_name == "network"
                    and (edge.evidence.path, edge.evidence.line)
                    in typescript_axios_instance_locations
                    for edge in ir.relationships
                ),
            },
            "typescript_composio_cli_upload": {
                "capabilities": len(typescript_composio_cli_upload),
                "dynamic_origins": sum(
                    bool(item.attributes.get("dynamic_origin"))
                    for item in typescript_composio_cli_upload
                ),
                "capability_edges": sum(
                    edge.target_kind == "capability"
                    and edge.target_name == "network"
                    and (edge.evidence.path, edge.evidence.line)
                    in typescript_composio_cli_upload_locations
                    for edge in ir.relationships
                ),
                "raw_global_fetch": sum(
                    item.attributes.get("transport_scope") == "raw-global-fetch"
                    for item in typescript_composio_cli_upload
                ),
                "destination_policy_absent": sum(
                    item.attributes.get("destination_policy") == "absent-on-proven-path"
                    for item in typescript_composio_cli_upload
                ),
            },
            "typescript_google_adk_openapi_rest_tool": {
                "capabilities": len(typescript_google_adk_openapi_rest_tool),
                "configured_origins": sum(
                    item.attributes.get("configured_origin") is True
                    and item.attributes.get("dynamic_origin") is False
                    for item in typescript_google_adk_openapi_rest_tool
                ),
                "tool_edges": sum(
                    edge.source_kind == "tool"
                    and edge.target_kind == "capability"
                    and edge.target_name == "network"
                    and (edge.evidence.path, edge.evidence.line)
                    in typescript_google_adk_openapi_rest_tool_locations
                    for edge in ir.relationships
                ),
                "origin_policy_edges": sum(
                    edge.source_kind == "capability"
                    and edge.source_name == "network"
                    and edge.relation == "governed-by"
                    and edge.target_kind == "control"
                    and edge.target_name == "network-origin-policy"
                    and edge.attributes.get("analysis")
                    == "typescript-google-adk-openapi-rest-tool"
                    for edge in ir.relationships
                ),
                "segment_encoded": sum(
                    edge.attributes.get("model_path_scope") == "segment-encoded"
                    for edge in ir.relationships
                    if edge.attributes.get("analysis")
                    == "typescript-google-adk-openapi-rest-tool"
                ),
            },
            "python_openai_mcp_approval_default": {
                "settings": len(python_openai_mcp_approval_default),
                "disabled_default": sum(
                    item.attributes.get("approval_policy") == "disabled-default"
                    and item.attributes.get("enabled") is False
                    for item in python_openai_mcp_approval_default
                ),
                "agent_server_edges": sum(
                    edge.source_kind == "agent"
                    and edge.relation == "uses"
                    and edge.target_kind == "mcp-server"
                    and edge.attributes.get("analysis")
                    == "python-openai-agents-mcp-approval-default"
                    for edge in ir.relationships
                ),
                "configured_by_edges": sum(
                    edge.source_kind == "mcp-server"
                    and edge.relation == "configured-by"
                    and edge.target_kind == "control-setting"
                    and edge.target_name == "mcp-tool-approval"
                    and edge.attributes.get("analysis")
                    == "python-openai-agents-mcp-approval-default"
                    for edge in ir.relationships
                ),
            },
            "python_google_adk_bigquery_audit": {
                "available_controls": sum(
                    item.attributes.get("deployment_state") == "framework-available"
                    for item in python_google_adk_bigquery_audit_controls
                ),
                "deployed_controls": sum(
                    item.attributes.get("deployment_state") == "enabled"
                    for item in python_google_adk_bigquery_audit_controls
                ),
                "production_deployments": sum(
                    item.attributes.get("deployment_state") == "enabled"
                    and item.attributes.get("scope") == "production"
                    for item in python_google_adk_bigquery_audit_controls
                ),
                "test_deployments": sum(
                    item.attributes.get("deployment_state") == "enabled"
                    and item.attributes.get("scope") == "test"
                    for item in python_google_adk_bigquery_audit_controls
                ),
                "storage_capabilities": len(python_google_adk_bigquery_audit_storage),
                "disabled_settings": sum(
                    item.attributes.get("state") == "disabled-explicit"
                    for item in python_google_adk_bigquery_audit_settings
                ),
                "agent_control_edges": sum(
                    edge.source_kind == "agent"
                    and edge.relation == "governed-by"
                    and edge.target_name == "durable-action-audit"
                    and edge.attributes.get("analysis")
                    == "python-google-adk-bigquery-action-audit"
                    for edge in ir.relationships
                ),
                "external_action_control_edges": sum(
                    edge.source_kind == "capability"
                    and edge.source_name == "external-action"
                    and edge.relation == "governed-by"
                    and edge.target_name == "durable-action-audit"
                    and edge.attributes.get("analysis")
                    == "python-google-adk-bigquery-action-audit"
                    for edge in ir.relationships
                ),
                "storage_edges": sum(
                    edge.source_kind == "control"
                    and edge.source_name == "durable-action-audit"
                    and edge.relation == "exports-to"
                    and edge.target_name == "audit-storage"
                    and edge.attributes.get("analysis")
                    == "python-google-adk-bigquery-action-audit"
                    for edge in ir.relationships
                ),
            },
            "typescript_network_origin_controls": {
                "total": len(typescript_network_origin_controls),
                "configured_optional": sum(
                    edge.attributes.get("hostname_scope") == "configured-optional"
                    for edge in typescript_network_origin_controls
                ),
                "default_open": sum(
                    edge.attributes.get("hostname_default") == "open"
                    for edge in typescript_network_origin_controls
                ),
                "dns_unresolved": sum(
                    edge.attributes.get("dns_scope") == "unresolved"
                    for edge in typescript_network_origin_controls
                ),
            },
            "typescript_secure_network_controls": {
                "total": len(typescript_secure_network_controls),
                "enabled_default": sum(
                    edge.attributes.get("enforcement_default") == "enabled"
                    for edge in typescript_secure_network_controls
                ),
                "disabled_default": sum(
                    edge.attributes.get("enforcement_default") == "disabled"
                    for edge in typescript_secure_network_controls
                ),
                "configured_opt_in": sum(
                    edge.attributes.get("enforcement_mode") == "configured-opt-in"
                    for edge in typescript_secure_network_controls
                ),
                "configured_opt_out": sum(
                    edge.attributes.get("enforcement_mode") == "configured-opt-out"
                    for edge in typescript_secure_network_controls
                ),
                "runtime_conditional": sum(
                    edge.attributes.get("enforcement_default") == "runtime-conditional"
                    for edge in typescript_secure_network_controls
                ),
                "bounded_redirect_hooks": sum(
                    edge.attributes.get("redirect_scope")
                    == "bounded-each-hop-hooks-when-enforced"
                    for edge in typescript_secure_network_controls
                ),
                "redirects_validated": sum(
                    edge.attributes.get("redirect_scope") == "each-hop-validated"
                    for edge in typescript_secure_network_controls
                ),
                "redirects_disabled": sum(
                    edge.attributes.get("redirect_scope") == "disabled"
                    for edge in typescript_secure_network_controls
                ),
                "redirects_direct_connection_filtered": sum(
                    edge.attributes.get("redirect_scope")
                    == "each-direct-connection-filtered"
                    for edge in typescript_secure_network_controls
                ),
                "secure_lookup_configured": sum(
                    edge.attributes.get("dns_scope")
                    == "secure-lookup-configured-when-enforced"
                    for edge in typescript_secure_network_controls
                ),
                "dns_connection_pinned_unless_proxied": sum(
                    edge.attributes.get("dns_scope")
                    == "connection-pinned-unless-proxied"
                    for edge in typescript_secure_network_controls
                ),
                "dns_connection_pinned": sum(
                    edge.attributes.get("dns_scope") == "connection-pinned"
                    for edge in typescript_secure_network_controls
                ),
                "dns_preflight_only_rebinding_residual": sum(
                    edge.attributes.get("dns_scope")
                    == "preflight-only-rebinding-residual"
                    for edge in typescript_secure_network_controls
                ),
                "dns_connection_time_filtered_unless_proxied": sum(
                    edge.attributes.get("dns_scope")
                    == "connection-time-filtered-unless-proxied"
                    for edge in typescript_secure_network_controls
                ),
                "dns_connection_pinned_unless_configured_route": sum(
                    edge.attributes.get("dns_scope")
                    == "connection-pinned-unless-configured-route"
                    for edge in typescript_secure_network_controls
                ),
                "proxy_unresolved": sum(
                    edge.attributes.get("proxy_scope") == "unresolved"
                    for edge in typescript_secure_network_controls
                ),
                "proxy_environment_dependent": sum(
                    edge.attributes.get("proxy_scope") == "environment-dependent"
                    for edge in typescript_secure_network_controls
                ),
                "proxy_pinned_agent": sum(
                    edge.attributes.get("proxy_scope") == "pinned-agent"
                    for edge in typescript_secure_network_controls
                ),
                "proxy_caller_global_or_environment_dependent": sum(
                    edge.attributes.get("proxy_scope")
                    == "caller-global-or-environment-dependent"
                    for edge in typescript_secure_network_controls
                ),
                "fixed_caller_config": sum(
                    edge.attributes.get("transport_scope") == "fixed-caller-config"
                    for edge in typescript_secure_network_controls
                ),
                "caller_agent_overridden": sum(
                    edge.attributes.get("transport_scope") == "caller-agent-overridden"
                    for edge in typescript_secure_network_controls
                ),
                "global_fetch_unpinned": sum(
                    edge.attributes.get("transport_scope") == "global-fetch-unpinned"
                    for edge in typescript_secure_network_controls
                ),
                "imported_axios_client_instance": sum(
                    edge.attributes.get("transport_scope")
                    == "imported-axios-client-instance"
                    for edge in typescript_secure_network_controls
                ),
                "configured_address_allowlist": sum(
                    edge.attributes.get("escape_hatch")
                    == "configured-address-allowlist"
                    for edge in typescript_secure_network_controls
                ),
                "undici_pinned_dispatcher_unless_configured_route": sum(
                    edge.attributes.get("transport_scope")
                    == "undici-pinned-dispatcher-unless-configured-route"
                    for edge in typescript_secure_network_controls
                ),
                "edge_runtime_fail_closed": sum(
                    edge.attributes.get("edge_runtime_scope") == "fail-closed"
                    for edge in typescript_secure_network_controls
                ),
                "edge_runtime_unguarded_fetch": sum(
                    edge.attributes.get("edge_runtime_scope") == "unguarded-fetch"
                    for edge in typescript_secure_network_controls
                ),
                "configured_route_residual": sum(
                    edge.attributes.get("configured_route_residual") is True
                    for edge in typescript_secure_network_controls
                ),
                "ipv4_mapped_ipv6_normalized": sum(
                    edge.attributes.get("ipv4_mapped_ipv6") == "normalized"
                    for edge in typescript_secure_network_controls
                ),
                "domain_hitl_independent": sum(
                    edge.attributes.get("approval_scope") == "domain-hitl-independent"
                    for edge in typescript_secure_network_controls
                ),
                "no_escape_hatch": sum(
                    edge.attributes.get("escape_hatch") == "none"
                    for edge in typescript_secure_network_controls
                ),
            },
            "a2a_endpoint_provenance": {
                "total": len(a2a_rpc_capabilities),
                "remote_card_unconstrained": sum(
                    item.attributes.get("remote_card_endpoint_scope") == "unconstrained"
                    for item in a2a_rpc_capabilities
                ),
                "same_origin_constrained": sum(
                    item.attributes.get("remote_card_endpoint_scope")
                    == "same-origin-constrained"
                    for item in a2a_rpc_capabilities
                ),
                "typescript": sum(
                    item.attributes.get("frontend") == "typescript"
                    for item in a2a_rpc_capabilities
                ),
                "python": sum(
                    item.attributes.get("frontend") == "python"
                    for item in a2a_rpc_capabilities
                ),
                "undici_agent_or_proxy": sum(
                    item.attributes.get("transport_scope") == "undici-agent-or-proxy"
                    for item in a2a_rpc_capabilities
                ),
                "all_interfaces_validated": sum(
                    edge.attributes.get("advertised_interface_scope") == "all-rpc-urls"
                    for edge in a2a_card_origin_controls
                ),
                "origin_control_edges": len(a2a_card_origin_controls),
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
        "schema_version": 45,
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
            "python_registry_tools": {
                name: sum(result["python_registry_tools"][name] for result in successful)
                for name in (
                    "total",
                    "functions",
                    "classes",
                    "resolved_entrypoints",
                    "metagpt",
                    "qwen_agent",
                    "capability_edges",
                )
            },
            "python_browser_evaluate": {
                name: sum(result["python_browser_evaluate"][name] for result in successful)
                for name in ("total", "dynamic", "receiver_proven")
            },
            "python_browser_receiver_proofs": dict(
                sorted(
                    sum(
                        (
                            Counter(result["python_browser_evaluate"]["receiver_proofs"])
                            for result in successful
                        ),
                        Counter(),
                    ).items()
                )
            ),
            "python_imported_network_helpers": {
                name: sum(result["python_imported_network_helpers"][name] for result in successful)
                for name in ("capabilities", "dynamic_origins", "helpers", "capability_edges")
            },
            "python_imported_class_network_helpers": {
                name: sum(
                    result["python_imported_class_network_helpers"][name]
                    for result in successful
                )
                for name in ("capabilities", "dynamic_origins", "callees", "capability_edges")
            },
            "python_urllib_network": {
                name: sum(result["python_urllib_network"][name] for result in successful)
                for name in ("capabilities", "dynamic_origins", "capability_edges")
            },
            "python_network_origin_controls": {
                name: sum(
                    result["python_network_origin_controls"][name]
                    for result in successful
                )
                for name in (
                    "total",
                    "redirects_disabled",
                    "redirects_unresolved",
                    "dns_unresolved",
                )
            },
            "python_secure_network_controls": {
                name: sum(
                    result["python_secure_network_controls"][name]
                    for result in successful
                )
                for name in (
                    "total",
                    "enabled_default",
                    "configured_opt_out",
                    "redirects_validated",
                    "redirects_disabled",
                    "dns_connection_pinned",
                    "dns_connection_pinned_unless_proxied",
                    "dns_connection_pinned_when_enforced",
                    "proxies_disabled",
                    "proxies_environment_or_caller_dependent",
                    "proxies_disabled_when_enforced",
                    "redirects_disabled_default_validated_when_enabled",
                    "configured_allowlist_and_loopback_exemption",
                    "no_escape_hatch",
                )
            },
            "typescript_axios_instance_network": {
                name: sum(
                    result["typescript_axios_instance_network"][name]
                    for result in successful
                )
                for name in (
                    "capabilities",
                    "dynamic_origins",
                    "absolute_override_allowed",
                    "absolute_override_disabled",
                    "capability_edges",
                )
            },
            "typescript_composio_cli_upload": {
                name: sum(
                    result["typescript_composio_cli_upload"][name]
                    for result in successful
                )
                for name in (
                    "capabilities",
                    "dynamic_origins",
                    "capability_edges",
                    "raw_global_fetch",
                    "destination_policy_absent",
                )
            },
            "typescript_google_adk_openapi_rest_tool": {
                name: sum(
                    result["typescript_google_adk_openapi_rest_tool"][name]
                    for result in successful
                )
                for name in (
                    "capabilities",
                    "configured_origins",
                    "tool_edges",
                    "origin_policy_edges",
                    "segment_encoded",
                )
            },
            "python_openai_mcp_approval_default": {
                name: sum(
                    result["python_openai_mcp_approval_default"][name]
                    for result in successful
                )
                for name in (
                    "settings",
                    "disabled_default",
                    "agent_server_edges",
                    "configured_by_edges",
                )
            },
            "python_google_adk_bigquery_audit": {
                name: sum(
                    result["python_google_adk_bigquery_audit"][name]
                    for result in successful
                )
                for name in (
                    "available_controls",
                    "deployed_controls",
                    "production_deployments",
                    "test_deployments",
                    "storage_capabilities",
                    "disabled_settings",
                    "agent_control_edges",
                    "external_action_control_edges",
                    "storage_edges",
                )
            },
            "typescript_network_origin_controls": {
                name: sum(
                    result["typescript_network_origin_controls"][name]
                    for result in successful
                )
                for name in (
                    "total",
                    "configured_optional",
                    "default_open",
                    "dns_unresolved",
                )
            },
            "typescript_secure_network_controls": {
                name: sum(
                    result["typescript_secure_network_controls"][name]
                    for result in successful
                )
                for name in (
                    "total",
                    "enabled_default",
                    "disabled_default",
                    "configured_opt_in",
                    "configured_opt_out",
                    "runtime_conditional",
                    "bounded_redirect_hooks",
                    "redirects_validated",
                    "redirects_disabled",
                    "redirects_direct_connection_filtered",
                    "secure_lookup_configured",
                    "dns_connection_pinned_unless_proxied",
                    "dns_connection_pinned",
                    "dns_preflight_only_rebinding_residual",
                    "dns_connection_time_filtered_unless_proxied",
                    "dns_connection_pinned_unless_configured_route",
                    "proxy_unresolved",
                    "proxy_environment_dependent",
                    "proxy_pinned_agent",
                    "proxy_caller_global_or_environment_dependent",
                    "fixed_caller_config",
                    "caller_agent_overridden",
                    "global_fetch_unpinned",
                    "imported_axios_client_instance",
                    "configured_address_allowlist",
                    "undici_pinned_dispatcher_unless_configured_route",
                    "edge_runtime_fail_closed",
                    "edge_runtime_unguarded_fetch",
                    "configured_route_residual",
                    "ipv4_mapped_ipv6_normalized",
                    "domain_hitl_independent",
                    "no_escape_hatch",
                )
            },
            "a2a_endpoint_provenance": {
                name: sum(result["a2a_endpoint_provenance"][name] for result in successful)
                for name in (
                    "total",
                    "remote_card_unconstrained",
                    "same_origin_constrained",
                    "typescript",
                    "python",
                    "undici_agent_or_proxy",
                    "all_interfaces_validated",
                    "origin_control_edges",
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

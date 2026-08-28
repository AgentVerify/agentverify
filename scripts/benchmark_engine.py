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

PYTHON_PROVIDER_METRICS = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
    "aws_bedrock": "AWS Bedrock",
    "mistral": "Mistral",
    "groq": "Groq",
    "cohere": "Cohere",
    "ollama": "Ollama",
    "alibaba_dashscope": "Alibaba DashScope",
    "deepseek": "DeepSeek",
    "moonshot_ai": "Moonshot AI",
    "xai": "xAI",
}
TYPESCRIPT_PROVIDER_METRICS = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
    "xai": "xAI",
    "mistral": "Mistral",
    "groq": "Groq",
    "cohere": "Cohere",
}


def is_test_path(path: str) -> bool:
    lowered = path.lower()
    parts = set(Path(lowered).parts)
    filename = Path(lowered).name
    return bool(
        parts & {"test", "tests", "__tests__", "fixtures"}
        or any(marker in filename for marker in (".test.", ".spec."))
        or filename.startswith("test_")
    )


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
            in {
                "block-dominating-definition",
                "lexical-single-definition",
                "module-single-definition",
                "same-class-helper-return",
                "same-block-function-factory-return",
                "imported-class-factory-return",
                "contextual-imported-class-factory-return",
                "literal-tools-list-context-manager",
                "literal-tools-list-import-binding",
                "literal-tools-list-inline-constructor",
                "imported-callable-single-export",
                "contextual-imported-callable-single-export",
                "agent-as-tool-adapter",
                "typed-parameter-callsite-consensus",
                "contextual-absolute-import-single-export",
            }
        )
        if any(
            edge.target_id is None
            for edge in ir.relationships
            if edge.attributes.get("target_identity") in resolved_binding_targets
        ):
            raise RuntimeError(f"{repository}: resolved binding target lacks a symbol ID")
        python_agent_helper_return_edges = [
            edge
            for edge in ir.relationships
            if edge.attributes.get("target_identity") == "same-class-helper-return"
        ]
        if any(
            edge.source_kind != "agent" or edge.target_kind != "agent" or edge.target_id is None
            for edge in python_agent_helper_return_edges
        ):
            raise RuntimeError(
                f"{repository}: same-class Agent helper return lacks an exact Agent edge"
            )
        python_local_agent_factory_return_edges = [
            edge
            for edge in ir.relationships
            if edge.attributes.get("target_identity") == "same-block-function-factory-return"
        ]
        if any(
            edge.source_kind != "agent" or edge.target_kind != "agent" or edge.target_id is None
            for edge in python_local_agent_factory_return_edges
        ):
            raise RuntimeError(
                f"{repository}: local Agent factory return lacks an exact Agent edge"
            )
        python_typed_tool_parameter_edges = [
            edge
            for edge in ir.relationships
            if edge.attributes.get("target_identity") == "typed-parameter-callsite-consensus"
        ]
        python_typed_tool_parameters = [
            component
            for component in ir.components
            if component.kind == "tool" and component.attributes.get("binding") == "typed-parameter"
        ]
        if any(
            edge.source_kind != "agent" or edge.target_kind != "tool" or edge.target_id is None
            for edge in python_typed_tool_parameter_edges
        ):
            raise RuntimeError(
                f"{repository}: typed tool parameter lacks an exact Agent-to-tool edge"
            )
        typed_tool_parameter_ids = {
            component.symbol_id
            for component in python_typed_tool_parameters
            if component.symbol_id is not None
        }
        if any(
            edge.target_id not in typed_tool_parameter_ids
            for edge in python_typed_tool_parameter_edges
        ):
            raise RuntimeError(
                f"{repository}: typed tool parameter edge lacks a parameter component"
            )
        component_symbol_ids = {item.symbol_id for item in ir.components if item.symbol_id}
        python_contextual_tool_import_edges = [
            edge
            for edge in ir.relationships
            if edge.attributes.get("target_identity") == "contextual-absolute-import-single-export"
        ]
        if any(
            edge.source_kind != "agent"
            or edge.target_kind != "tool"
            or edge.source_id not in component_symbol_ids
            or edge.target_id not in component_symbol_ids
            or not edge.attributes.get("target_path")
            for edge in python_contextual_tool_import_edges
        ):
            raise RuntimeError(
                f"{repository}: contextual Python tool import lacks an exact graph edge"
            )
        python_contextual_tool_target_ids = {
            edge.target_id for edge in python_contextual_tool_import_edges
        }
        python_imported_agent_factory_edges = [
            edge
            for edge in ir.relationships
            if edge.attributes.get("target_identity")
            in {
                "imported-class-factory-return",
                "contextual-imported-class-factory-return",
            }
        ]
        if any(
            edge.source_kind != "agent"
            or edge.target_kind != "agent"
            or edge.source_id not in component_symbol_ids
            or edge.target_id not in component_symbol_ids
            or not edge.attributes.get("target_path")
            for edge in python_imported_agent_factory_edges
        ):
            raise RuntimeError(f"{repository}: imported Agent factory lacks an exact graph edge")
        typed_tool_concrete_ids = {
            target_id
            for component in python_typed_tool_parameters
            for target_id in component.attributes.get("callsite_target_ids", [])
        }
        if not typed_tool_concrete_ids <= component_symbol_ids:
            raise RuntimeError(
                f"{repository}: typed tool parameter records a missing concrete target"
            )
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
            if item.kind == "tool" and item.attributes.get("registration") == "registry-decorator"
        ]
        python_registry_tool_ids = {
            item.symbol_id for item in python_registry_tools if item.symbol_id
        }
        python_computer_tools = [
            item
            for item in ir.components
            if item.kind == "tool"
            and item.evidence.path.endswith(".py")
            and str(item.attributes.get("constructor", "")).rsplit(".", 1)[-1] == "ComputerTool"
        ]
        python_computer_tool_ids = {
            item.symbol_id for item in python_computer_tools if item.symbol_id
        }
        if len(python_computer_tool_ids) != len(python_computer_tools):
            raise RuntimeError(f"{repository}: Python ComputerTool lacks a unique symbol ID")
        python_computer_capability_edges = [
            edge
            for edge in ir.relationships
            if edge.source_id in python_computer_tool_ids
            and edge.target_kind == "capability"
            and edge.target_name == "computer-control"
        ]
        if len(python_computer_capability_edges) != len(python_computer_tools):
            raise RuntimeError(
                f"{repository}: Python ComputerTool lacks an exact computer-control edge"
            )
        python_computer_agent_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "agent" and edge.target_id in python_computer_tool_ids
        ]
        python_local_shell_tools = [
            item
            for item in ir.components
            if item.kind == "tool"
            and item.name.startswith("LocalShellTool@")
            and item.attributes.get("approval_source") == "sdk-no-approval-parameter"
            and item.attributes.get("execution_environment") == "local"
        ]
        python_local_shell_tool_ids = {
            item.symbol_id for item in python_local_shell_tools if item.symbol_id
        }
        if len(python_local_shell_tool_ids) != len(python_local_shell_tools):
            raise RuntimeError(f"{repository}: Python LocalShellTool lacks a unique symbol ID")
        python_local_shell_capability_edges = [
            edge
            for edge in ir.relationships
            if edge.source_id in python_local_shell_tool_ids
            and edge.target_kind == "capability"
            and edge.target_name == "shell-execution"
        ]
        if len(python_local_shell_capability_edges) != len(python_local_shell_tools):
            raise RuntimeError(f"{repository}: Python LocalShellTool lacks an exact shell edge")
        python_code_interpreter_tools = [
            item
            for item in ir.components
            if item.kind == "tool"
            and item.name.startswith("CodeInterpreterTool@")
            and item.attributes.get("sandbox_policy") == "sdk-hosted"
            and item.attributes.get("execution_environment") == "hosted-sandbox"
        ]
        python_code_interpreter_tool_ids = {
            item.symbol_id for item in python_code_interpreter_tools if item.symbol_id
        }
        if len(python_code_interpreter_tool_ids) != len(python_code_interpreter_tools):
            raise RuntimeError(f"{repository}: Python CodeInterpreterTool lacks a unique symbol ID")
        python_code_interpreter_capability_edges = [
            edge
            for edge in ir.relationships
            if edge.source_id in python_code_interpreter_tool_ids
            and edge.target_kind == "capability"
            and edge.target_name == "code-execution"
        ]
        if len(python_code_interpreter_capability_edges) != len(python_code_interpreter_tools):
            raise RuntimeError(f"{repository}: Python CodeInterpreterTool lacks an exact code edge")
        python_openai_hosted_tools = [
            item
            for item in ir.components
            if item.kind == "tool"
            and item.attributes.get("hosting_policy") == "sdk-provider-hosted"
            and item.attributes.get("execution_environment") == "hosted"
        ]
        python_openai_hosted_tool_ids = {
            item.symbol_id for item in python_openai_hosted_tools if item.symbol_id
        }
        if len(python_openai_hosted_tool_ids) != len(python_openai_hosted_tools):
            raise RuntimeError(f"{repository}: Python OpenAI hosted tool lacks a unique symbol ID")
        python_openai_hosted_capability_edges = [
            edge
            for edge in ir.relationships
            if edge.source_id in python_openai_hosted_tool_ids and edge.target_kind == "capability"
        ]
        if len(python_openai_hosted_capability_edges) != len(python_openai_hosted_tools):
            raise RuntimeError(
                f"{repository}: Python OpenAI hosted tool lacks an exact capability edge"
            )
        python_sandbox_agents = [
            item
            for item in ir.components
            if item.kind == "agent"
            and item.evidence.path.endswith(".py")
            and item.attributes.get("constructor") == "SandboxAgent"
        ]
        python_sandbox_agent_ids = {
            item.symbol_id for item in python_sandbox_agents if item.symbol_id
        }
        python_agent_referenced_tools = [
            item
            for item in ir.components
            if item.kind == "tool" and item.attributes.get("registration") == "agent-tool-reference"
        ]
        python_agent_tool_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "agent"
            and edge.target_kind == "tool"
            and edge.evidence.path.endswith(".py")
        ]
        python_non_test_agent_tool_edges = [
            edge for edge in python_agent_tool_edges if not is_test_path(edge.evidence.path)
        ]
        python_agent_mcp_server_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "agent"
            and edge.target_kind == "mcp-server"
            and edge.attributes.get("target_identity")
            in {
                "literal-mcp-servers-list-binding",
                "literal-mcp-servers-list-module-binding",
                "literal-mcp-servers-list-context-manager",
            }
            and edge.evidence.path.endswith(".py")
        ]
        python_fastmcp_server_tool_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "mcp-server"
            and edge.target_kind == "tool"
            and edge.attributes.get("target_identity") == "exact-fastmcp-registrar"
            and edge.evidence.path.endswith(".py")
        ]
        agent_reachable_fastmcp_server_ids = {
            edge.target_id for edge in python_agent_mcp_server_edges if edge.target_id is not None
        }
        agent_reachable_fastmcp_tool_ids = {
            edge.target_id
            for edge in python_fastmcp_server_tool_edges
            if edge.source_id in agent_reachable_fastmcp_server_ids and edge.target_id is not None
        }
        python_fastmcp_agent_capability_edges = [
            edge
            for edge in ir.relationships
            if edge.source_id in agent_reachable_fastmcp_tool_ids
            and edge.target_kind == "capability"
        ]
        python_agent_referenced_tool_ids = {
            item.symbol_id for item in python_agent_referenced_tools if item.symbol_id
        }
        if len(python_agent_referenced_tool_ids) != len(python_agent_referenced_tools):
            raise RuntimeError(
                f"{repository}: Agent-referenced Python callable lacks a unique symbol ID"
            )
        python_agent_referenced_capability_edges = [
            edge
            for edge in ir.relationships
            if edge.source_id in python_agent_referenced_tool_ids
            and edge.target_kind == "capability"
        ]
        python_agent_referenced_agent_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "agent" and edge.target_id in python_agent_referenced_tool_ids
        ]
        referenced_tool_agent_targets = {
            edge.target_id for edge in python_agent_referenced_agent_edges
        }
        if referenced_tool_agent_targets != python_agent_referenced_tool_ids:
            raise RuntimeError(
                f"{repository}: Agent-referenced Python callable lacks an exact Agent edge"
            )
        python_agent_as_tool_adapter_ids = {
            item.symbol_id
            for item in python_agent_referenced_tools
            if item.symbol_id and item.attributes.get("binding") == "agent-as-tool-adapter"
        }
        python_agent_as_tool_delegations = [
            edge
            for edge in ir.relationships
            if edge.source_id in python_agent_as_tool_adapter_ids
            and edge.source_kind == "tool"
            and edge.target_kind == "agent"
            and edge.relation == "delegates-to"
            and edge.target_id is not None
        ]
        if {
            edge.source_id for edge in python_agent_as_tool_delegations
        } != python_agent_as_tool_adapter_ids:
            raise RuntimeError(
                f"{repository}: Agent.as_tool adapter lacks an exact delegation edge"
            )
        python_function_tool_wrappers = [
            item
            for item in ir.components
            if item.kind == "tool"
            and item.attributes.get("registration") == "function-tool-wrapper"
        ]
        python_function_tool_wrapper_ids = {
            item.symbol_id for item in python_function_tool_wrappers if item.symbol_id
        }
        if len(python_function_tool_wrapper_ids) != len(python_function_tool_wrappers):
            raise RuntimeError(
                f"{repository}: Python function-tool wrapper lacks a unique symbol ID"
            )
        python_function_tool_wrapper_capability_edges = [
            edge
            for edge in ir.relationships
            if edge.source_id in python_function_tool_wrapper_ids
            and edge.target_kind == "capability"
        ]
        python_function_tool_wrapper_agent_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "agent" and edge.target_id in python_function_tool_wrapper_ids
        ]
        function_tool_wrapper_agent_targets = {
            edge.target_id for edge in python_function_tool_wrapper_agent_edges
        }
        if function_tool_wrapper_agent_targets != python_function_tool_wrapper_ids:
            raise RuntimeError(
                f"{repository}: Python function-tool wrapper lacks an exact Agent edge"
            )
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
        python_contextual_network_helpers = [
            item
            for item in python_imported_network_helpers
            if item.attributes.get("import_resolution") == "contextual-absolute-import-single-path"
        ]
        python_imported_literal_origins = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "network"
            and item.attributes.get("origin_resolution") == "imported-module-literal"
        ]
        python_imported_literal_origin_locations = {
            (item.evidence.path, item.evidence.line) for item in python_imported_literal_origins
        }
        python_imported_network_locations = {
            (item.evidence.path, item.evidence.line) for item in python_imported_network_helpers
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
            (item.evidence.path, item.evidence.line) for item in typescript_axios_instance_network
        }
        typescript_composio_cli_upload = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "network"
            and item.attributes.get("analysis") == "typescript-composio-cli-file-upload-flow"
        ]
        typescript_composio_cli_upload_locations = {
            (item.evidence.path, item.evidence.line) for item in typescript_composio_cli_upload
        }
        typescript_google_adk_openapi_rest_tool = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "network"
            and item.attributes.get("analysis") == "typescript-google-adk-openapi-rest-tool"
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
            and item.attributes.get("analysis") == "python-openai-agents-mcp-approval-default"
        ]
        python_openhands_components = [
            item
            for item in ir.components
            if item.attributes.get("analysis") == "python-openhands-conversation-security"
        ]
        python_openhands_tools = [
            item for item in python_openhands_components if item.kind == "tool"
        ]
        python_openhands_capabilities = [
            item for item in python_openhands_components if item.kind == "capability"
        ]
        python_trae_agent_components = [
            item
            for item in ir.components
            if item.attributes.get("analysis") == "python-trae-agent-default-tools"
        ]
        python_trae_agent_tools = [
            item for item in python_trae_agent_components if item.kind == "tool"
        ]
        python_trae_agent_capabilities = [
            item for item in python_trae_agent_components if item.kind == "capability"
        ]
        typescript_roo_command_components = [
            item
            for item in ir.components
            if item.attributes.get("analysis") == "typescript-roo-command-auto-approval"
        ]
        typescript_continue_plan_components = [
            item
            for item in ir.components
            if item.attributes.get("analysis") == "typescript-continue-plan-mode-approval"
        ]
        typescript_continue_plan_mcp_components = [
            item
            for item in ir.components
            if item.attributes.get("analysis") == "typescript-continue-plan-mode-mcp-approval"
        ]
        typescript_cline_subagent_analyses = {
            "typescript-cline-subagent-approval-propagation",
            "typescript-cline-cli-subagent-approval-propagation",
        }
        typescript_cline_subagent_components = [
            item
            for item in ir.components
            if item.attributes.get("analysis") in typescript_cline_subagent_analyses
        ]
        typescript_letta_default_components = [
            item
            for item in ir.components
            if item.attributes.get("analysis") == "typescript-letta-default-tools"
        ]
        typescript_openai_mcp_approval_servers = [
            item
            for item in ir.components
            if item.kind == "mcp-server"
            and item.attributes.get("analysis") == "typescript-openai-agents-mcp-approval-default"
        ]
        typescript_openai_mcp_approval_capabilities = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "filesystem"
            and item.attributes.get("analysis") == "typescript-openai-agents-mcp-approval-default"
        ]
        python_agno_mcp_confirmation_servers = [
            item
            for item in ir.components
            if item.kind == "mcp-server"
            and item.attributes.get("analysis") == "python-agno-mcp-confirmation-default"
        ]
        python_agno_mcp_confirmation_capabilities = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "filesystem"
            and item.attributes.get("analysis") == "python-agno-mcp-confirmation-default"
        ]
        python_semantic_kernel_mcp_sampling_servers = [
            item
            for item in ir.components
            if item.kind == "mcp-server"
            and item.attributes.get("analysis") == "python-semantic-kernel-mcp-sampling-approval"
        ]
        python_semantic_kernel_mcp_sampling_capabilities = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "model-sampling"
            and item.attributes.get("analysis") == "python-semantic-kernel-mcp-sampling-approval"
        ]
        mcp_sampling_consent_capabilities = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "model-sampling"
            and item.attributes.get("analysis")
            in {
                "python-mcp-sampling-callback-consent",
                "python-pydantic-ai-mcp-sampling-model",
                "typescript-mcp-sampling-handler-consent",
            }
        ]
        mcp_elicitation_consent_capabilities = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "user-elicitation"
            and item.attributes.get("analysis")
            in {
                "python-fastmcp-elicitation-handler-consent",
                "python-mcp-elicitation-callback-consent",
                "typescript-mcp-elicitation-handler-consent",
            }
        ]
        approval_callback_bypass_tools = [
            item
            for item in ir.components
            if item.kind == "tool"
            and item.attributes.get("approval_bypass_resolution") == "same-file-transitive-callback"
        ]
        mcp_package_launchers = [
            item
            for item in ir.components
            if item.kind == "mcp-server" and item.attributes.get("package")
        ]
        python_import_bound_mcp_stdio_servers = [
            item
            for item in ir.components
            if item.kind == "mcp-server"
            and item.attributes.get("frontend") == "python"
            and item.attributes.get("transport") == "stdio"
            and item.attributes.get("constructor")
            in {"MCPServer", "MCPServerStdio", "MCPTools", "StdioServerParameters"}
        ]
        python_import_bound_mcp_in_process_servers = [
            item
            for item in ir.components
            if item.kind == "mcp-server"
            and item.attributes.get("analysis") == "python-import-bound-mcp-server-constructor"
            and item.attributes.get("transport") == "in-process"
        ]
        python_imported_mcp_server_subclasses = [
            item
            for item in ir.components
            if item.kind == "mcp-server"
            and item.attributes.get("analysis") == "python-imported-mcp-server-subclass"
        ]
        python_imported_mcp_server_subclass_ids = {
            item.symbol_id for item in python_imported_mcp_server_subclasses if item.symbol_id
        }
        python_provider_call_attributions = [
            item
            for item in ir.components
            if item.kind == "provider"
            and item.attributes.get("resolution") == "exact-provider-sdk-import"
        ]
        python_provider_call_models = [
            item
            for item in ir.components
            if item.kind == "model"
            and item.attributes.get("resolution") == "exact-provider-sdk-import"
        ]
        typescript_provider_call_attributions = [
            item
            for item in ir.components
            if item.kind == "provider"
            and item.attributes.get("resolution") == "exact-typescript-provider-import"
        ]
        typescript_provider_call_models = [
            item
            for item in ir.components
            if item.kind == "model"
            and item.attributes.get("resolution") == "exact-typescript-provider-import"
        ]
        python_google_adk_bigquery_audit_controls = [
            item
            for item in ir.components
            if item.kind == "control"
            and item.name == "durable-action-audit"
            and item.attributes.get("analysis") == "python-google-adk-bigquery-action-audit"
        ]
        python_google_adk_bigquery_audit_storage = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "audit-storage"
            and item.attributes.get("analysis") == "python-google-adk-bigquery-action-audit"
        ]
        python_google_adk_bigquery_audit_settings = [
            item
            for item in ir.components
            if item.kind == "control-setting"
            and item.name == "action-audit"
            and item.attributes.get("analysis") == "python-google-adk-bigquery-action-audit"
        ]
        python_skyvern_action_history_controls = [
            item
            for item in ir.components
            if item.kind == "control"
            and item.name == "durable-action-record"
            and item.attributes.get("analysis") == "python-skyvern-taskv3-action-history"
        ]
        python_skyvern_action_history_storage = [
            item
            for item in ir.components
            if item.kind == "capability"
            and item.name == "audit-storage"
            and item.attributes.get("analysis") == "python-skyvern-taskv3-action-history"
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
        python_path_segment_sanitizer_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "capability"
            and edge.source_name == "filesystem"
            and edge.relation == "governed-by"
            and edge.target_kind == "control"
            and edge.target_name == "path-segment-sanitizer"
            and edge.evidence.path.endswith(".py")
        ]
        python_dify_agent_shell_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "tool"
            and edge.source_name == "dify.shell"
            and edge.relation == "uses"
            and edge.target_kind == "capability"
            and edge.target_name == "shell-execution"
            and edge.attributes.get("analysis") == "python-dify-agent-shell-layer"
        ]
        python_dify_agent_runtime_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "capability"
            and edge.source_name == "shell-execution"
            and edge.relation == "governed-by"
            and edge.target_kind == "control"
            and edge.target_name == "sandbox-runtime"
            and edge.attributes.get("analysis") == "python-dify-agent-shell-layer"
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
            "python_provider_call_attribution": {
                "calls": len(python_provider_call_attributions),
                "production_calls": sum(
                    not is_test_path(item.evidence.path)
                    for item in python_provider_call_attributions
                ),
                "test_calls": sum(
                    is_test_path(item.evidence.path) for item in python_provider_call_attributions
                ),
                "repositories": bool(python_provider_call_attributions),
                "production_repositories": any(
                    not is_test_path(item.evidence.path)
                    for item in python_provider_call_attributions
                ),
                "sdk_calls": sum(
                    item.attributes.get("call_kind") != "wrapper-constructor"
                    for item in python_provider_call_attributions
                ),
                "wrapper_calls": sum(
                    item.attributes.get("call_kind") == "wrapper-constructor"
                    for item in python_provider_call_attributions
                ),
                "langchain_wrapper_calls": sum(
                    str(item.attributes.get("module", "")).startswith("langchain_")
                    for item in python_provider_call_attributions
                ),
                "pydantic_ai_wrapper_calls": sum(
                    str(item.attributes.get("module", "")).startswith("pydantic_ai.")
                    for item in python_provider_call_attributions
                ),
                "agentscope_wrapper_calls": sum(
                    str(item.attributes.get("module", "")).startswith("agentscope.")
                    for item in python_provider_call_attributions
                ),
                "agno_wrapper_calls": sum(
                    str(item.attributes.get("module", "")).startswith("agno.models.")
                    for item in python_provider_call_attributions
                ),
                "autogen_wrapper_calls": sum(
                    str(item.attributes.get("module", "")).startswith("autogen_ext.models.")
                    for item in python_provider_call_attributions
                ),
                "literal_models": len(python_provider_call_models),
                **{
                    metric: sum(item.name == provider for item in python_provider_call_attributions)
                    for metric, provider in PYTHON_PROVIDER_METRICS.items()
                },
            },
            "typescript_provider_call_attribution": {
                "calls": len(typescript_provider_call_attributions),
                "production_calls": sum(
                    not is_test_path(item.evidence.path)
                    for item in typescript_provider_call_attributions
                ),
                "test_calls": sum(
                    is_test_path(item.evidence.path)
                    for item in typescript_provider_call_attributions
                ),
                "repositories": bool(typescript_provider_call_attributions),
                "production_repositories": any(
                    not is_test_path(item.evidence.path)
                    for item in typescript_provider_call_attributions
                ),
                "native_sdk_calls": sum(
                    str(item.attributes.get("call_kind", "")).startswith("provider-sdk-")
                    for item in typescript_provider_call_attributions
                ),
                "ai_sdk_calls": sum(
                    str(item.attributes.get("call_kind", "")).startswith("ai-sdk-provider-")
                    for item in typescript_provider_call_attributions
                ),
                "factory_calls": sum(
                    item.attributes.get("call_kind") == "ai-sdk-provider-factory"
                    for item in typescript_provider_call_attributions
                ),
                "model_calls": sum(
                    item.attributes.get("call_kind")
                    in {"ai-sdk-provider-model", "provider-sdk-model"}
                    for item in typescript_provider_call_attributions
                ),
                "configured_instance_calls": sum(
                    bool(item.attributes.get("configured_by"))
                    for item in typescript_provider_call_attributions
                ),
                "typed_parameter_model_calls": sum(
                    item.attributes.get("resolution_basis")
                    == "same-file-typed-parameter-callsite-consensus"
                    for item in typescript_provider_call_attributions
                ),
                "class_field_model_calls": sum(
                    item.attributes.get("resolution_basis") == "immutable-class-field-constructor"
                    for item in typescript_provider_call_attributions
                ),
                "class_accessor_model_calls": sum(
                    item.attributes.get("resolution_basis") == "same-class-lazy-getter-constructor"
                    for item in typescript_provider_call_attributions
                ),
                "literal_binding_models": sum(
                    item.attributes.get("model_resolution_basis")
                    == "immutable-module-literal-binding"
                    for item in typescript_provider_call_models
                ),
                "literal_models": len(typescript_provider_call_models),
                **{
                    metric: sum(
                        item.name == provider for item in typescript_provider_call_attributions
                    )
                    for metric, provider in TYPESCRIPT_PROVIDER_METRICS.items()
                },
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
                    bool(item.attributes.get("wrappers")) for item in python_post_registered_tools
                ),
                "wrapper_layers": sum(
                    len(item.attributes.get("wrappers", []))
                    for item in python_post_registered_tools
                ),
                "relative_import": sum(
                    item.attributes.get("resolution") == "relative-import-single-definition"
                    for item in python_post_registered_tools
                ),
                "same_module": sum(
                    item.attributes.get("resolution") == "same-module-single-definition"
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
                    item.attributes.get("framework") == "MetaGPT" for item in python_registry_tools
                ),
                "qwen_agent": sum(
                    item.attributes.get("framework") == "Qwen-Agent"
                    for item in python_registry_tools
                ),
                "capability_edges": sum(
                    edge.source_id in python_registry_tool_ids and edge.target_kind == "capability"
                    for edge in ir.relationships
                ),
            },
            "python_computer_tools": {
                "instances": len(python_computer_tools),
                "non_test_instances": sum(
                    not is_test_path(item.evidence.path) for item in python_computer_tools
                ),
                "local_execution": sum(
                    item.attributes.get("execution_environment") == "local"
                    for item in python_computer_tools
                ),
                "safety_check_handlers_configured": sum(
                    item.attributes.get("safety_check_handler") == "configured"
                    for item in python_computer_tools
                ),
                "safety_check_auto_acknowledge_all": sum(
                    item.attributes.get("safety_check_policy") == "auto-acknowledge-all"
                    for item in python_computer_tools
                ),
                "safety_check_inline_lambda_auto_ack": sum(
                    item.attributes.get("safety_check_resolution") == "inline-lambda"
                    for item in python_computer_tools
                ),
                "safety_check_same_file_callback_auto_ack": sum(
                    item.attributes.get("safety_check_resolution") == "same-file-callback"
                    for item in python_computer_tools
                ),
                "safety_check_unresolved": sum(
                    item.attributes.get("safety_check_policy") == "unresolved"
                    for item in python_computer_tools
                ),
                "capability_edges": len(python_computer_capability_edges),
                "resolved_agent_edges": len(python_computer_agent_edges),
            },
            "python_local_shell_tools": {
                "instances": len(python_local_shell_tools),
                "non_test_instances": sum(
                    not is_test_path(item.evidence.path) for item in python_local_shell_tools
                ),
                "approval_unavailable": sum(
                    item.attributes.get("approval_policy") == "unavailable"
                    for item in python_local_shell_tools
                ),
                "capability_edges": len(python_local_shell_capability_edges),
                "resolved_agent_edges": sum(
                    edge.target_id in python_local_shell_tool_ids
                    for edge in ir.relationships
                    if edge.source_kind == "agent" and edge.target_kind == "tool"
                ),
                "repositories": bool(python_local_shell_tools),
            },
            "python_code_interpreter_tools": {
                "instances": len(python_code_interpreter_tools),
                "non_test_instances": sum(
                    not is_test_path(item.evidence.path) for item in python_code_interpreter_tools
                ),
                "approval_unavailable": sum(
                    item.attributes.get("approval_policy") == "unavailable"
                    for item in python_code_interpreter_tools
                ),
                "auto_containers": sum(
                    item.attributes.get("container_policy") == "auto"
                    for item in python_code_interpreter_tools
                ),
                "capability_edges": len(python_code_interpreter_capability_edges),
                "resolved_agent_edges": sum(
                    edge.target_id in python_code_interpreter_tool_ids
                    for edge in ir.relationships
                    if edge.source_kind == "agent" and edge.target_kind == "tool"
                ),
                "repositories": bool(python_code_interpreter_tools),
            },
            "python_openai_hosted_tools": {
                "instances": len(python_openai_hosted_tools),
                "non_test_instances": sum(
                    not is_test_path(item.evidence.path) for item in python_openai_hosted_tools
                ),
                "approval_unavailable": sum(
                    item.attributes.get("approval_policy") == "unavailable"
                    for item in python_openai_hosted_tools
                ),
                "web_search": sum(
                    item.name.startswith("WebSearchTool@") for item in python_openai_hosted_tools
                ),
                "web_external_access_sdk_default": sum(
                    item.attributes.get("external_web_access") == "sdk-default"
                    for item in python_openai_hosted_tools
                ),
                "file_search": sum(
                    item.name.startswith("FileSearchTool@") for item in python_openai_hosted_tools
                ),
                "literal_vector_store_scope": sum(
                    item.attributes.get("vector_store_scope") in {"literal-empty", "literal-ids"}
                    for item in python_openai_hosted_tools
                ),
                "image_generation": sum(
                    item.name.startswith("ImageGenerationTool@")
                    for item in python_openai_hosted_tools
                ),
                "capability_edges": len(python_openai_hosted_capability_edges),
                "resolved_agent_edges": sum(
                    edge.target_id in python_openai_hosted_tool_ids
                    for edge in ir.relationships
                    if edge.source_kind == "agent" and edge.target_kind == "tool"
                ),
                "repositories": bool(python_openai_hosted_tools),
            },
            "python_sandbox_agents": {
                "total": len(python_sandbox_agents),
                "non_test": sum(
                    not is_test_path(item.evidence.path) for item in python_sandbox_agents
                ),
                "mcp_server_edges": sum(
                    edge.source_id in python_sandbox_agent_ids
                    for edge in python_agent_mcp_server_edges
                ),
                "repositories": bool(python_sandbox_agents),
            },
            "python_agent_referenced_tools": {
                "instances": len(python_agent_referenced_tools),
                "callables": sum(
                    item.attributes.get("binding") is None for item in python_agent_referenced_tools
                ),
                "constructor_bindings": sum(
                    item.attributes.get("binding") == "literal-tools-list-constructor"
                    for item in python_agent_referenced_tools
                ),
                "inline_constructors": sum(
                    item.attributes.get("binding") == "literal-tools-list-inline-constructor"
                    for item in python_agent_referenced_tools
                ),
                "context_manager_bindings": sum(
                    item.attributes.get("binding") == "literal-tools-list-context-manager"
                    for item in python_agent_referenced_tools
                ),
                "agent_as_tool_adapters": len(python_agent_as_tool_adapter_ids),
                "agent_as_tool_delegations": len(python_agent_as_tool_delegations),
                "import_bindings": sum(
                    item.attributes.get("binding") == "literal-tools-list-import"
                    for item in python_agent_referenced_tools
                ),
                "imported_callable_exports": sum(
                    item.attributes.get("resolution")
                    in {
                        "imported-callable-single-export",
                        "contextual-imported-callable-single-export",
                    }
                    for item in python_agent_referenced_tools
                ),
                "module_single_definitions": sum(
                    item.attributes.get("resolution") == "module-single-definition"
                    for item in python_agent_referenced_tools
                ),
                "non_test_instances": sum(
                    not is_test_path(item.evidence.path) for item in python_agent_referenced_tools
                ),
                "capability_edges": len(python_agent_referenced_capability_edges),
                "resolved_agent_edges": len(python_agent_referenced_agent_edges),
            },
            "python_agent_tool_edges": {
                "total": len(python_agent_tool_edges),
                "resolved": sum(edge.target_id is not None for edge in python_agent_tool_edges),
                "unresolved": sum(edge.target_id is None for edge in python_agent_tool_edges),
                "non_test": len(python_non_test_agent_tool_edges),
                "unresolved_non_test": sum(
                    edge.target_id is None for edge in python_non_test_agent_tool_edges
                ),
            },
            "python_agent_mcp_server_edges": {
                "total": len(python_agent_mcp_server_edges),
                "resolved": sum(
                    edge.target_id is not None for edge in python_agent_mcp_server_edges
                ),
                "non_test": sum(
                    not is_test_path(edge.evidence.path) for edge in python_agent_mcp_server_edges
                ),
                "same_block": sum(
                    edge.attributes.get("target_identity") == "literal-mcp-servers-list-binding"
                    for edge in python_agent_mcp_server_edges
                ),
                "immutable_module": sum(
                    edge.attributes.get("target_identity")
                    == "literal-mcp-servers-list-module-binding"
                    for edge in python_agent_mcp_server_edges
                ),
                "context_managed": sum(
                    edge.attributes.get("target_identity")
                    == "literal-mcp-servers-list-context-manager"
                    for edge in python_agent_mcp_server_edges
                ),
                "repositories": bool(python_agent_mcp_server_edges),
            },
            "python_fastmcp_server_tool_edges": {
                "total": len(python_fastmcp_server_tool_edges),
                "resolved": sum(
                    edge.source_id is not None and edge.target_id is not None
                    for edge in python_fastmcp_server_tool_edges
                ),
                "non_test": sum(
                    not is_test_path(edge.evidence.path)
                    for edge in python_fastmcp_server_tool_edges
                ),
                "agent_reachable_tools": len(agent_reachable_fastmcp_tool_ids),
                "agent_reachable_capabilities": len(python_fastmcp_agent_capability_edges),
                "non_test_agent_reachable_capabilities": sum(
                    not is_test_path(edge.evidence.path)
                    for edge in python_fastmcp_agent_capability_edges
                ),
                "repositories": bool(python_fastmcp_server_tool_edges),
            },
            "python_function_tool_wrappers": {
                "instances": len(python_function_tool_wrappers),
                "non_test_instances": sum(
                    not is_test_path(item.evidence.path) for item in python_function_tool_wrappers
                ),
                "approval_enabled": sum(
                    item.attributes.get("needs_approval") is True
                    for item in python_function_tool_wrappers
                ),
                "capability_edges": len(python_function_tool_wrapper_capability_edges),
                "resolved_agent_edges": len(python_function_tool_wrapper_agent_edges),
            },
            "python_agent_helper_returns": {
                "resolved_edges": len(python_agent_helper_return_edges),
                "unique_agent_targets": len(
                    {edge.target_id for edge in python_agent_helper_return_edges}
                ),
                "non_test_edges": sum(
                    not is_test_path(edge.evidence.path)
                    for edge in python_agent_helper_return_edges
                ),
            },
            "python_local_agent_factory_returns": {
                "resolved_edges": len(python_local_agent_factory_return_edges),
                "unique_agent_targets": len(
                    {edge.target_id for edge in python_local_agent_factory_return_edges}
                ),
                "non_test_edges": sum(
                    not is_test_path(edge.evidence.path)
                    for edge in python_local_agent_factory_return_edges
                ),
                "repositories": bool(python_local_agent_factory_return_edges),
            },
            "python_typed_tool_parameters": {
                "parameter_bindings": len(python_typed_tool_parameters),
                "resolved_edges": len(python_typed_tool_parameter_edges),
                "verified_call_sites": sum(
                    int(component.attributes.get("verified_call_sites", 0))
                    for component in python_typed_tool_parameters
                ),
                "concrete_targets": len(
                    {
                        target_id
                        for component in python_typed_tool_parameters
                        for target_id in component.attributes.get("callsite_target_ids", [])
                    }
                ),
                "non_test_edges": sum(
                    not is_test_path(edge.evidence.path)
                    for edge in python_typed_tool_parameter_edges
                ),
            },
            "python_contextual_imports": {
                "resolved_tool_edges": len(python_contextual_tool_import_edges),
                "unique_tool_targets": len(python_contextual_tool_target_ids),
                "tool_capability_targets": len(
                    {
                        edge.source_id
                        for edge in ir.relationships
                        if edge.source_id in python_contextual_tool_target_ids
                        and edge.target_kind == "capability"
                    }
                ),
                "non_test_tool_edges": sum(
                    not is_test_path(edge.evidence.path)
                    for edge in python_contextual_tool_import_edges
                ),
                "network_helper_capabilities": len(python_contextual_network_helpers),
                "dynamic_network_helper_capabilities": sum(
                    bool(item.attributes.get("dynamic_origin"))
                    for item in python_contextual_network_helpers
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
                "apis": dict(
                    sorted(
                        Counter(
                            str(item.attributes.get("api", "unknown")).rsplit(".", 1)[-1]
                            for item in python_browser_evaluations
                        ).items()
                    )
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
            "python_imported_literal_origins": {
                "capabilities": len(python_imported_literal_origins),
                "source_bindings": len(
                    {
                        (item.attributes.get("origin_path"), item.attributes.get("origin_line"))
                        for item in python_imported_literal_origins
                    }
                ),
                "contextual_helper_capabilities": sum(
                    item.attributes.get("summary") == "imported-function"
                    and item.attributes.get("import_resolution")
                    == "contextual-absolute-import-single-path"
                    for item in python_imported_literal_origins
                ),
                "capability_edges": sum(
                    edge.target_kind == "capability"
                    and edge.target_name == "network"
                    and (edge.evidence.path, edge.evidence.line)
                    in python_imported_literal_origin_locations
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
                    bool(item.attributes.get("dynamic_origin")) for item in python_urllib_network
                ),
                "capability_edges": sum(
                    edge.target_kind == "capability"
                    and edge.target_name == "network"
                    and (edge.evidence.path, edge.evidence.line) in python_urllib_network_locations
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
                    edge.attributes.get("dns_scope") == "connection-pinned-unless-proxied"
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
                    edge.attributes.get("proxy_scope") == "environment-or-caller-dependent"
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
                    and edge.attributes.get("analysis") == "typescript-google-adk-openapi-rest-tool"
                    for edge in ir.relationships
                ),
                "segment_encoded": sum(
                    edge.attributes.get("model_path_scope") == "segment-encoded"
                    for edge in ir.relationships
                    if edge.attributes.get("analysis") == "typescript-google-adk-openapi-rest-tool"
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
            "python_openhands_conversation_security": {
                "tools": len(python_openhands_tools),
                "terminal_tools": sum(
                    item.attributes.get("builtin_tool") == "TerminalTool"
                    for item in python_openhands_tools
                ),
                "file_editor_tools": sum(
                    item.attributes.get("builtin_tool") == "FileEditorTool"
                    for item in python_openhands_tools
                ),
                "capabilities": len(python_openhands_capabilities),
                "analyzer_controls": sum(
                    item.kind == "control" and item.name == "action-risk-analysis"
                    for item in python_openhands_components
                ),
                "confirmation_controls": sum(
                    item.kind == "control" and item.name == "human-approval"
                    for item in python_openhands_components
                ),
                "disabled_default_settings": sum(
                    item.kind == "control-setting"
                    and item.name == "agent-action-confirmation"
                    and item.attributes.get("enabled") is False
                    for item in python_openhands_components
                ),
                "agent_tool_edges": sum(
                    edge.source_kind == "agent"
                    and edge.relation == "uses"
                    and edge.target_kind == "tool"
                    and edge.attributes.get("analysis") == "python-openhands-conversation-security"
                    for edge in ir.relationships
                ),
                "risk_analysis_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "governed-by"
                    and edge.target_name == "action-risk-analysis"
                    and edge.attributes.get("analysis") == "python-openhands-conversation-security"
                    for edge in ir.relationships
                ),
                "human_approval_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "governed-by"
                    and edge.target_name == "human-approval"
                    and edge.attributes.get("analysis") == "python-openhands-conversation-security"
                    for edge in ir.relationships
                ),
                "approval_findings": sum(
                    finding.rule_id == "AV-APPROVAL006" for finding in ir.findings
                ),
                "filesystem_findings": sum(
                    finding.rule_id == "AV-FS001"
                    and finding.analysis.get("tool", "").startswith("FileEditorTool@")
                    for finding in ir.findings
                ),
            },
            "python_trae_agent_default_tools": {
                "tools": len(python_trae_agent_tools),
                "bash_tools": sum(
                    item.attributes.get("builtin_tool_name") == "BashTool"
                    for item in python_trae_agent_tools
                ),
                "editor_tools": sum(
                    item.attributes.get("builtin_tool_name") == "TextEditorTool"
                    for item in python_trae_agent_tools
                ),
                "capabilities": len(python_trae_agent_capabilities),
                "approval_settings": sum(
                    item.kind == "control-setting"
                    and item.name == "agent-action-confirmation"
                    and item.attributes.get("enabled") is False
                    for item in python_trae_agent_components
                ),
                "isolation_settings": sum(
                    item.kind == "control-setting"
                    and item.name == "tool-execution-isolation"
                    and item.attributes.get("enabled") is False
                    for item in python_trae_agent_components
                ),
                "agent_tool_edges": sum(
                    edge.source_kind == "agent"
                    and edge.relation == "uses"
                    and edge.target_kind == "tool"
                    and edge.attributes.get("analysis") == "python-trae-agent-default-tools"
                    for edge in ir.relationships
                ),
                "configured_by_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "configured-by"
                    and edge.target_kind == "control-setting"
                    and edge.attributes.get("analysis") == "python-trae-agent-default-tools"
                    for edge in ir.relationships
                ),
                "execution_findings": sum(
                    finding.rule_id == "AV-EXEC001"
                    and finding.analysis.get("tool") == "Trae BashTool"
                    for finding in ir.findings
                ),
                "approval_findings": sum(
                    finding.rule_id == "AV-APPROVAL002"
                    and finding.analysis.get("tool") == "Trae BashTool"
                    for finding in ir.findings
                ),
                "filesystem_findings": sum(
                    finding.rule_id == "AV-FS001"
                    and finding.analysis.get("tool") == "Trae TextEditorTool"
                    for finding in ir.findings
                ),
            },
            "typescript_roo_command_auto_approval": {
                "agents": sum(item.kind == "agent" for item in typescript_roo_command_components),
                "tools": sum(item.kind == "tool" for item in typescript_roo_command_components),
                "capabilities": sum(
                    item.kind == "capability" for item in typescript_roo_command_components
                ),
                "controls": sum(
                    item.kind == "control" for item in typescript_roo_command_components
                ),
                "settings": sum(
                    item.kind == "control-setting" for item in typescript_roo_command_components
                ),
                "agent_tool_edges": sum(
                    edge.source_kind == "agent"
                    and edge.relation == "uses"
                    and edge.target_kind == "tool"
                    and edge.attributes.get("analysis") == "typescript-roo-command-auto-approval"
                    for edge in ir.relationships
                ),
                "capability_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "uses"
                    and edge.target_kind == "capability"
                    and edge.attributes.get("analysis") == "typescript-roo-command-auto-approval"
                    for edge in ir.relationships
                ),
                "setting_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "configured-by"
                    and edge.target_kind == "control-setting"
                    and edge.attributes.get("analysis") == "typescript-roo-command-auto-approval"
                    for edge in ir.relationships
                ),
                "control_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "governed-by"
                    and edge.target_kind == "control"
                    and edge.attributes.get("analysis") == "typescript-roo-command-auto-approval"
                    for edge in ir.relationships
                ),
                "execution_findings": sum(
                    finding.rule_id == "AV-EXEC001"
                    and finding.analysis.get("tool") == "Roo ExecuteCommandTool"
                    for finding in ir.findings
                ),
                "approval_findings": sum(
                    finding.rule_id == "AV-APPROVAL007"
                    and finding.analysis.get("tool") == "Roo ExecuteCommandTool"
                    for finding in ir.findings
                ),
            },
            "typescript_continue_plan_mode_approval": {
                "frameworks": sum(
                    item.kind == "framework" for item in typescript_continue_plan_components
                ),
                "agents": sum(item.kind == "agent" for item in typescript_continue_plan_components),
                "tools": sum(item.kind == "tool" for item in typescript_continue_plan_components),
                "capabilities": sum(
                    item.kind == "capability" for item in typescript_continue_plan_components
                ),
                "controls": sum(
                    item.kind == "control" for item in typescript_continue_plan_components
                ),
                "settings": sum(
                    item.kind == "control-setting" for item in typescript_continue_plan_components
                ),
                "agent_tool_edges": sum(
                    edge.source_kind == "agent"
                    and edge.relation == "uses"
                    and edge.target_kind == "tool"
                    and edge.attributes.get("analysis") == "typescript-continue-plan-mode-approval"
                    for edge in ir.relationships
                ),
                "capability_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "uses"
                    and edge.target_kind == "capability"
                    and edge.attributes.get("analysis") == "typescript-continue-plan-mode-approval"
                    for edge in ir.relationships
                ),
                "setting_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "configured-by"
                    and edge.target_kind == "control-setting"
                    and edge.attributes.get("analysis") == "typescript-continue-plan-mode-approval"
                    for edge in ir.relationships
                ),
                "control_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "governed-by"
                    and edge.target_kind == "control"
                    and edge.attributes.get("analysis") == "typescript-continue-plan-mode-approval"
                    for edge in ir.relationships
                ),
                "execution_findings": sum(
                    finding.rule_id == "AV-EXEC001"
                    and finding.analysis.get("tool") == "Continue Bash tool"
                    for finding in ir.findings
                ),
                "approval_findings": sum(
                    finding.rule_id == "AV-APPROVAL008"
                    and finding.analysis.get("tool") == "Continue Bash tool"
                    for finding in ir.findings
                ),
            },
            "typescript_continue_plan_mode_mcp_approval": {
                "agents": sum(
                    item.kind == "agent" for item in typescript_continue_plan_mcp_components
                ),
                "tools": sum(
                    item.kind == "tool" for item in typescript_continue_plan_mcp_components
                ),
                "capabilities": sum(
                    item.kind == "capability" for item in typescript_continue_plan_mcp_components
                ),
                "servers": sum(
                    item.kind == "mcp-server" for item in typescript_continue_plan_mcp_components
                ),
                "controls": sum(
                    item.kind == "control" for item in typescript_continue_plan_mcp_components
                ),
                "settings": sum(
                    item.kind == "control-setting"
                    for item in typescript_continue_plan_mcp_components
                ),
                "agent_tool_edges": sum(
                    edge.source_kind == "agent"
                    and edge.relation == "uses"
                    and edge.target_kind == "tool"
                    and edge.attributes.get("analysis")
                    == "typescript-continue-plan-mode-mcp-approval"
                    for edge in ir.relationships
                ),
                "capability_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "uses"
                    and edge.target_kind == "capability"
                    and edge.attributes.get("analysis")
                    == "typescript-continue-plan-mode-mcp-approval"
                    for edge in ir.relationships
                ),
                "server_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "invokes"
                    and edge.target_kind == "mcp-server"
                    and edge.attributes.get("analysis")
                    == "typescript-continue-plan-mode-mcp-approval"
                    for edge in ir.relationships
                ),
                "setting_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "configured-by"
                    and edge.target_kind == "control-setting"
                    and edge.attributes.get("analysis")
                    == "typescript-continue-plan-mode-mcp-approval"
                    for edge in ir.relationships
                ),
                "control_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "governed-by"
                    and edge.target_kind == "control"
                    and edge.attributes.get("analysis")
                    == "typescript-continue-plan-mode-mcp-approval"
                    for edge in ir.relationships
                ),
                "approval_findings": sum(
                    finding.rule_id == "AV-APPROVAL009"
                    and finding.analysis.get("tool") == "Continue MCP tool adapter"
                    for finding in ir.findings
                ),
            },
            "typescript_cline_subagent_approval": {
                "frameworks": sum(
                    item.kind == "framework" for item in typescript_cline_subagent_components
                ),
                "agents": sum(
                    item.kind == "agent" for item in typescript_cline_subagent_components
                ),
                "tools": sum(item.kind == "tool" for item in typescript_cline_subagent_components),
                "capabilities": sum(
                    item.kind == "capability" for item in typescript_cline_subagent_components
                ),
                "controls": sum(
                    item.kind == "control" for item in typescript_cline_subagent_components
                ),
                "settings": sum(
                    item.kind == "control-setting" for item in typescript_cline_subagent_components
                ),
                "parent_tool_edges": sum(
                    edge.source_kind == "agent"
                    and edge.relation == "uses"
                    and edge.target_kind == "tool"
                    and edge.attributes.get("analysis") in typescript_cline_subagent_analyses
                    for edge in ir.relationships
                ),
                "delegation_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "delegates-to"
                    and edge.target_kind == "agent"
                    and edge.attributes.get("analysis") in typescript_cline_subagent_analyses
                    for edge in ir.relationships
                ),
                "child_capability_edges": sum(
                    edge.source_kind == "agent"
                    and edge.relation == "uses"
                    and edge.target_kind == "capability"
                    and edge.attributes.get("analysis") in typescript_cline_subagent_analyses
                    for edge in ir.relationships
                ),
                "setting_edges": sum(
                    edge.source_kind == "agent"
                    and edge.relation == "configured-by"
                    and edge.target_kind == "control-setting"
                    and edge.attributes.get("analysis") in typescript_cline_subagent_analyses
                    for edge in ir.relationships
                ),
                "control_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "governed-by"
                    and edge.target_kind == "control"
                    and edge.attributes.get("analysis") in typescript_cline_subagent_analyses
                    for edge in ir.relationships
                ),
                "approval_findings": sum(
                    finding.rule_id == "AV-APPROVAL010"
                    and finding.analysis.get("tool")
                    in {"Cline spawn_agent tool", "Cline CLI spawn_agent tool"}
                    for finding in ir.findings
                ),
            },
            "typescript_letta_default_tools": {
                "agents": sum(item.kind == "agent" for item in typescript_letta_default_components),
                "tools": sum(item.kind == "tool" for item in typescript_letta_default_components),
                "bash_tools": sum(
                    item.kind == "tool" and item.attributes.get("builtin_tool_name") == "bash"
                    for item in typescript_letta_default_components
                ),
                "write_tools": sum(
                    item.kind == "tool" and item.attributes.get("builtin_tool_name") == "write"
                    for item in typescript_letta_default_components
                ),
                "capabilities": sum(
                    item.kind == "capability" for item in typescript_letta_default_components
                ),
                "approval_settings": sum(
                    item.kind == "control-setting"
                    and item.name == "agent-action-confirmation"
                    and item.attributes.get("enabled") is False
                    for item in typescript_letta_default_components
                ),
                "isolation_settings": sum(
                    item.kind == "control-setting"
                    and item.name == "tool-execution-isolation"
                    and item.attributes.get("enabled") is False
                    for item in typescript_letta_default_components
                ),
                "agent_tool_edges": sum(
                    edge.source_kind == "agent"
                    and edge.relation == "uses"
                    and edge.target_kind == "tool"
                    and edge.attributes.get("analysis") == "typescript-letta-default-tools"
                    for edge in ir.relationships
                ),
                "configured_by_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "configured-by"
                    and edge.target_kind == "control-setting"
                    and edge.attributes.get("analysis") == "typescript-letta-default-tools"
                    for edge in ir.relationships
                ),
                "capability_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "uses"
                    and edge.target_kind == "capability"
                    and edge.attributes.get("analysis") == "typescript-letta-default-tools"
                    for edge in ir.relationships
                ),
                "execution_findings": sum(
                    finding.rule_id == "AV-EXEC001"
                    and finding.analysis.get("tool") == "Letta Bash tool"
                    for finding in ir.findings
                ),
                "approval_findings": sum(
                    finding.rule_id == "AV-APPROVAL002"
                    and finding.analysis.get("tool") == "Letta Bash tool"
                    for finding in ir.findings
                ),
                "filesystem_findings": sum(
                    finding.rule_id == "AV-FS001"
                    and finding.analysis.get("tool") == "Letta Write tool"
                    for finding in ir.findings
                ),
            },
            "typescript_openai_mcp_approval_default": {
                "servers": len(typescript_openai_mcp_approval_servers),
                "writable_servers": sum(
                    item.attributes.get("write_access") is True
                    for item in typescript_openai_mcp_approval_capabilities
                ),
                "read_only_filtered": sum(
                    item.attributes.get("write_access") is False
                    and item.attributes.get("tool_filter") == "read-only-static"
                    for item in typescript_openai_mcp_approval_capabilities
                ),
                "agent_server_edges": sum(
                    edge.source_kind == "agent"
                    and edge.relation == "uses"
                    and edge.target_kind == "mcp-server"
                    and edge.attributes.get("analysis")
                    == "typescript-openai-agents-mcp-approval-default"
                    for edge in ir.relationships
                ),
                "configured_by_edges": sum(
                    edge.source_kind == "mcp-server"
                    and edge.relation == "configured-by"
                    and edge.target_kind == "control-setting"
                    and edge.target_name == "mcp-tool-approval"
                    and edge.attributes.get("analysis")
                    == "typescript-openai-agents-mcp-approval-default"
                    for edge in ir.relationships
                ),
                "findings": sum(finding.rule_id == "AV-APPROVAL004" for finding in ir.findings),
            },
            "python_agno_mcp_confirmation": {
                "servers": len(python_agno_mcp_confirmation_servers),
                "writable_servers": sum(
                    item.attributes.get("write_access") is True
                    for item in python_agno_mcp_confirmation_capabilities
                ),
                "read_only_filtered": sum(
                    item.attributes.get("write_access") is False
                    and item.attributes.get("tool_filter") == "read-only-static"
                    for item in python_agno_mcp_confirmation_capabilities
                ),
                "fully_confirmed": sum(
                    item.attributes.get("approval_policy") == "enabled-static-mutations"
                    for item in python_agno_mcp_confirmation_capabilities
                ),
                "agent_server_edges": sum(
                    edge.source_kind == "agent"
                    and edge.relation == "uses"
                    and edge.target_kind == "mcp-server"
                    and edge.attributes.get("analysis") == "python-agno-mcp-confirmation-default"
                    for edge in ir.relationships
                ),
                "configured_by_edges": sum(
                    edge.source_kind == "mcp-server"
                    and edge.relation == "configured-by"
                    and edge.target_kind == "control-setting"
                    and edge.target_name == "mcp-tool-confirmation"
                    and edge.attributes.get("analysis") == "python-agno-mcp-confirmation-default"
                    for edge in ir.relationships
                ),
                "findings": sum(finding.rule_id == "AV-APPROVAL005" for finding in ir.findings),
            },
            "python_semantic_kernel_mcp_sampling": {
                "servers": len(python_semantic_kernel_mcp_sampling_servers),
                "capabilities": len(python_semantic_kernel_mcp_sampling_capabilities),
                "auto_approved": sum(
                    item.attributes.get("approval_policy") == "auto-approved-explicit"
                    for item in python_semantic_kernel_mcp_sampling_capabilities
                ),
                "denied_default": sum(
                    item.attributes.get("approval_policy") == "denied-default"
                    for item in python_semantic_kernel_mcp_sampling_capabilities
                ),
                "denied_explicit": sum(
                    item.attributes.get("approval_policy") == "denied-explicit"
                    for item in python_semantic_kernel_mcp_sampling_capabilities
                ),
                "callback_controlled": sum(
                    item.attributes.get("approval_policy") == "callback-controlled"
                    for item in python_semantic_kernel_mcp_sampling_capabilities
                ),
                "unresolved_explicit": sum(
                    item.attributes.get("approval_policy") == "unresolved-explicit"
                    for item in python_semantic_kernel_mcp_sampling_capabilities
                ),
                "agent_server_edges": sum(
                    edge.source_kind == "agent"
                    and edge.relation == "uses"
                    and edge.target_kind == "mcp-server"
                    and edge.attributes.get("analysis")
                    == "python-semantic-kernel-mcp-sampling-approval"
                    for edge in ir.relationships
                ),
                "configured_by_edges": sum(
                    edge.source_kind == "mcp-server"
                    and edge.relation == "configured-by"
                    and edge.target_kind == "control-setting"
                    and edge.target_name == "mcp-sampling-approval"
                    and edge.attributes.get("analysis")
                    == "python-semantic-kernel-mcp-sampling-approval"
                    for edge in ir.relationships
                ),
                "deny_control_edges": sum(
                    edge.source_kind == "capability"
                    and edge.source_name == "model-sampling"
                    and edge.relation == "governed-by"
                    and edge.target_kind == "control"
                    and edge.target_name == "mcp-sampling-consent"
                    and edge.attributes.get("analysis")
                    == "python-semantic-kernel-mcp-sampling-approval"
                    for edge in ir.relationships
                ),
                "findings": sum(finding.rule_id == "AV-MCP004" for finding in ir.findings),
            },
            "mcp_sampling_consent": {
                "handlers": len(mcp_sampling_consent_capabilities),
                "default_scope_handlers": sum(
                    item.attributes.get("scope") != "test"
                    for item in mcp_sampling_consent_capabilities
                ),
                "automatic_fulfilment": sum(
                    item.attributes.get("approval_policy") == "automatic-fulfilment"
                    for item in mcp_sampling_consent_capabilities
                ),
                "default_scope_automatic_fulfilment": sum(
                    item.attributes.get("scope") != "test"
                    and item.attributes.get("approval_policy") == "automatic-fulfilment"
                    for item in mcp_sampling_consent_capabilities
                ),
                "human_confirmed": sum(
                    item.attributes.get("approval_policy") == "human-confirmed"
                    for item in mcp_sampling_consent_capabilities
                ),
                "denied_handler": sum(
                    item.attributes.get("approval_policy") == "denied-handler"
                    for item in mcp_sampling_consent_capabilities
                ),
                "unresolved_handler": sum(
                    item.attributes.get("approval_policy") == "unresolved-handler"
                    for item in mcp_sampling_consent_capabilities
                ),
                "python": sum(
                    item.attributes.get("frontend") == "python"
                    for item in mcp_sampling_consent_capabilities
                ),
                "typescript": sum(
                    item.attributes.get("frontend") == "typescript"
                    for item in mcp_sampling_consent_capabilities
                ),
                "model_provider": sum(
                    item.attributes.get("fulfilment_target") == "model-provider"
                    for item in mcp_sampling_consent_capabilities
                ),
                "protocol_edges": sum(
                    edge.source_kind == "protocol"
                    and edge.source_name == "MCP"
                    and edge.relation == "uses"
                    and edge.target_kind == "capability"
                    and edge.target_name == "model-sampling"
                    and edge.attributes.get("analysis")
                    in {
                        "python-mcp-sampling-callback-consent",
                        "python-pydantic-ai-mcp-sampling-model",
                        "typescript-mcp-sampling-handler-consent",
                    }
                    for edge in ir.relationships
                ),
                "configured_by_edges": sum(
                    edge.source_kind == "protocol"
                    and edge.source_name == "MCP"
                    and edge.relation == "configured-by"
                    and edge.target_kind == "control-setting"
                    and edge.target_name == "mcp-sampling-fulfilment"
                    and edge.attributes.get("analysis")
                    in {
                        "python-mcp-sampling-callback-consent",
                        "python-pydantic-ai-mcp-sampling-model",
                        "typescript-mcp-sampling-handler-consent",
                    }
                    for edge in ir.relationships
                ),
                "consent_control_edges": sum(
                    edge.source_kind == "capability"
                    and edge.source_name == "model-sampling"
                    and edge.relation == "governed-by"
                    and edge.target_kind == "control"
                    and edge.target_name == "mcp-sampling-consent"
                    and edge.attributes.get("analysis")
                    in {
                        "python-mcp-sampling-callback-consent",
                        "python-pydantic-ai-mcp-sampling-model",
                        "typescript-mcp-sampling-handler-consent",
                    }
                    for edge in ir.relationships
                ),
                "token_budget_edges": sum(
                    edge.source_kind == "capability"
                    and edge.source_name == "model-sampling"
                    and edge.relation == "governed-by"
                    and edge.target_kind == "control"
                    and edge.target_name == "mcp-sampling-token-budget"
                    and edge.attributes.get("analysis") == "typescript-mcp-sampling-handler-consent"
                    for edge in ir.relationships
                ),
                "findings": sum(finding.rule_id == "AV-MCP005" for finding in ir.findings),
            },
            "mcp_elicitation_consent": {
                "handlers": len(mcp_elicitation_consent_capabilities),
                "default_scope_handlers": sum(
                    item.attributes.get("scope") != "test"
                    for item in mcp_elicitation_consent_capabilities
                ),
                "automatic_acceptance": sum(
                    item.attributes.get("approval_policy") == "automatic-accept"
                    for item in mcp_elicitation_consent_capabilities
                ),
                "default_scope_automatic_acceptance": sum(
                    item.attributes.get("scope") != "test"
                    and item.attributes.get("approval_policy") == "automatic-accept"
                    for item in mcp_elicitation_consent_capabilities
                ),
                "human_confirmed": sum(
                    item.attributes.get("approval_policy") == "human-confirmed"
                    for item in mcp_elicitation_consent_capabilities
                ),
                "declined_handler": sum(
                    item.attributes.get("approval_policy") == "declined-handler"
                    for item in mcp_elicitation_consent_capabilities
                ),
                "unresolved_handler": sum(
                    item.attributes.get("approval_policy") == "unresolved-handler"
                    for item in mcp_elicitation_consent_capabilities
                ),
                "python": sum(
                    item.attributes.get("frontend") == "python"
                    for item in mcp_elicitation_consent_capabilities
                ),
                "typescript": sum(
                    item.attributes.get("frontend") == "typescript"
                    for item in mcp_elicitation_consent_capabilities
                ),
                "form_capable": sum(
                    "form" in item.attributes.get("elicitation_modes", ())
                    for item in mcp_elicitation_consent_capabilities
                ),
                "url_capable": sum(
                    "url" in item.attributes.get("elicitation_modes", ())
                    for item in mcp_elicitation_consent_capabilities
                ),
                "human_confirmed_url_acceptance": sum(
                    "url" in item.attributes.get("elicitation_modes", ())
                    and item.attributes.get("approval_policy") == "human-confirmed"
                    for item in mcp_elicitation_consent_capabilities
                ),
                "full_url_disclosure": sum(
                    item.attributes.get("url_disclosure") == "full-url"
                    for item in mcp_elicitation_consent_capabilities
                ),
                "missing_full_url_disclosure": sum(
                    "url" in item.attributes.get("elicitation_modes", ())
                    and item.attributes.get("approval_policy") == "human-confirmed"
                    and item.attributes.get("url_disclosure") != "full-url"
                    for item in mcp_elicitation_consent_capabilities
                ),
                "protocol_edges": sum(
                    edge.source_kind == "protocol"
                    and edge.source_name == "MCP"
                    and edge.relation == "uses"
                    and edge.target_kind == "capability"
                    and edge.target_name == "user-elicitation"
                    and edge.attributes.get("analysis")
                    in {
                        "python-fastmcp-elicitation-handler-consent",
                        "python-mcp-elicitation-callback-consent",
                        "typescript-mcp-elicitation-handler-consent",
                    }
                    for edge in ir.relationships
                ),
                "configured_by_edges": sum(
                    edge.source_kind == "protocol"
                    and edge.source_name == "MCP"
                    and edge.relation == "configured-by"
                    and edge.target_kind == "control-setting"
                    and edge.target_name == "mcp-elicitation-acceptance"
                    and edge.attributes.get("analysis")
                    in {
                        "python-fastmcp-elicitation-handler-consent",
                        "python-mcp-elicitation-callback-consent",
                        "typescript-mcp-elicitation-handler-consent",
                    }
                    for edge in ir.relationships
                ),
                "consent_control_edges": sum(
                    edge.source_kind == "capability"
                    and edge.source_name == "user-elicitation"
                    and edge.relation == "governed-by"
                    and edge.target_kind == "control"
                    and edge.target_name == "mcp-elicitation-consent"
                    and edge.attributes.get("analysis")
                    in {
                        "python-fastmcp-elicitation-handler-consent",
                        "python-mcp-elicitation-callback-consent",
                        "typescript-mcp-elicitation-handler-consent",
                    }
                    for edge in ir.relationships
                ),
                "findings": sum(finding.rule_id == "AV-MCP006" for finding in ir.findings),
                "url_disclosure_findings": sum(
                    finding.rule_id == "AV-MCP007" for finding in ir.findings
                ),
            },
            "approval_callback_bypass": {
                "tools": len(approval_callback_bypass_tools),
                "python_tools": sum(
                    item.evidence.path.endswith(".py") for item in approval_callback_bypass_tools
                ),
                "typescript_tools": sum(
                    item.evidence.path.endswith((".ts", ".tsx", ".js", ".jsx"))
                    for item in approval_callback_bypass_tools
                ),
                "configured_by_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "configured-by"
                    and edge.target_kind == "control-setting"
                    and edge.target_name == "auto-approval"
                    and edge.attributes.get("resolution") == "same-file-transitive-callback"
                    for edge in ir.relationships
                ),
                "findings": sum(finding.rule_id == "AV-APPROVAL003" for finding in ir.findings),
            },
            "mcp_package_launchers": {
                "total": len(mcp_package_launchers),
                "non_test": sum(
                    item.attributes.get("scope") != "test" for item in mcp_package_launchers
                ),
                "auto_install": sum(
                    item.attributes.get("auto_install") is True for item in mcp_package_launchers
                ),
                "unpinned": sum(
                    item.attributes.get("version_scope") == "unpinned"
                    for item in mcp_package_launchers
                ),
                "floating": sum(
                    item.attributes.get("version_scope") == "floating"
                    for item in mcp_package_launchers
                ),
                "exact": sum(
                    item.attributes.get("version_scope") == "exact"
                    for item in mcp_package_launchers
                ),
                "python": sum(
                    item.attributes.get("frontend") == "python" for item in mcp_package_launchers
                ),
                "json": sum(
                    item.attributes.get("frontend") == "json" for item in mcp_package_launchers
                ),
                "typescript": sum(
                    item.attributes.get("frontend") == "typescript"
                    for item in mcp_package_launchers
                ),
                "findings": sum(finding.rule_id == "AV-MCP003" for finding in ir.findings),
            },
            "python_import_bound_mcp_stdio_servers": {
                "total": len(python_import_bound_mcp_stdio_servers),
                "non_test": sum(
                    item.attributes.get("scope") != "test"
                    for item in python_import_bound_mcp_stdio_servers
                ),
                "symbolized_assigned": sum(
                    item.attributes.get("binding_resolution") == "assignment"
                    for item in python_import_bound_mcp_stdio_servers
                ),
                "symbolized_context_managed": sum(
                    item.attributes.get("binding_resolution") == "context-manager-binding"
                    for item in python_import_bound_mcp_stdio_servers
                ),
                "symbolized_bound": sum(
                    item.symbol_id is not None for item in python_import_bound_mcp_stdio_servers
                ),
                "package_backed": sum(
                    bool(item.attributes.get("package"))
                    for item in python_import_bound_mcp_stdio_servers
                ),
                "non_package": sum(
                    not item.attributes.get("package")
                    for item in python_import_bound_mcp_stdio_servers
                ),
                "repositories": bool(python_import_bound_mcp_stdio_servers),
            },
            "python_import_bound_mcp_in_process_servers": {
                "total": len(python_import_bound_mcp_in_process_servers),
                "non_test": sum(
                    item.attributes.get("scope") != "test"
                    for item in python_import_bound_mcp_in_process_servers
                ),
                "symbolized_assigned": sum(
                    item.attributes.get("binding_resolution") == "assignment"
                    for item in python_import_bound_mcp_in_process_servers
                ),
                "symbolized_context_managed": sum(
                    item.attributes.get("binding_resolution") == "context-manager-binding"
                    for item in python_import_bound_mcp_in_process_servers
                ),
                "symbolized_bound": sum(
                    item.symbol_id is not None
                    for item in python_import_bound_mcp_in_process_servers
                ),
                "repositories": bool(python_import_bound_mcp_in_process_servers),
            },
            "python_imported_mcp_server_subclasses": {
                "instances": len(python_imported_mcp_server_subclasses),
                "non_test_instances": sum(
                    not is_test_path(item.evidence.path)
                    for item in python_imported_mcp_server_subclasses
                ),
                "resolved_agent_edges": sum(
                    edge.target_id in python_imported_mcp_server_subclass_ids
                    for edge in python_agent_mcp_server_edges
                ),
                "repositories": bool(python_imported_mcp_server_subclasses),
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
                    and edge.attributes.get("analysis") == "python-google-adk-bigquery-action-audit"
                    for edge in ir.relationships
                ),
                "external_action_control_edges": sum(
                    edge.source_kind == "capability"
                    and edge.source_name == "external-action"
                    and edge.relation == "governed-by"
                    and edge.target_name == "durable-action-audit"
                    and edge.attributes.get("analysis") == "python-google-adk-bigquery-action-audit"
                    for edge in ir.relationships
                ),
                "storage_edges": sum(
                    edge.source_kind == "control"
                    and edge.source_name == "durable-action-audit"
                    and edge.relation == "exports-to"
                    and edge.target_name == "audit-storage"
                    and edge.attributes.get("analysis") == "python-google-adk-bigquery-action-audit"
                    for edge in ir.relationships
                ),
            },
            "python_skyvern_action_history": {
                "deployed_controls": len(python_skyvern_action_history_controls),
                "production_deployments": sum(
                    item.attributes.get("scope") == "production"
                    for item in python_skyvern_action_history_controls
                ),
                "best_effort_controls": sum(
                    item.attributes.get("delivery") == "best-effort-post-action"
                    for item in python_skyvern_action_history_controls
                ),
                "actor_attribution_unresolved": sum(
                    item.attributes.get("actor_attribution")
                    == "unresolved-created-by-nullable-and-unset"
                    for item in python_skyvern_action_history_controls
                ),
                "storage_capabilities": len(python_skyvern_action_history_storage),
                "agent_control_edges": sum(
                    edge.source_kind == "agent"
                    and edge.relation == "governed-by"
                    and edge.target_name == "durable-action-record"
                    and edge.attributes.get("analysis") == "python-skyvern-taskv3-action-history"
                    for edge in ir.relationships
                ),
                "tool_control_edges": sum(
                    edge.source_kind == "tool"
                    and edge.relation == "governed-by"
                    and edge.target_name == "durable-action-record"
                    and edge.attributes.get("analysis") == "python-skyvern-taskv3-action-history"
                    for edge in ir.relationships
                ),
                "external_action_control_edges": sum(
                    edge.source_kind == "capability"
                    and edge.source_name == "external-action"
                    and edge.relation == "governed-by"
                    and edge.target_name == "durable-action-record"
                    and edge.attributes.get("analysis") == "python-skyvern-taskv3-action-history"
                    for edge in ir.relationships
                ),
                "storage_edges": sum(
                    edge.source_kind == "control"
                    and edge.source_name == "durable-action-record"
                    and edge.relation == "exports-to"
                    and edge.target_name == "audit-storage"
                    and edge.attributes.get("analysis") == "python-skyvern-taskv3-action-history"
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
                    edge.attributes.get("redirect_scope") == "bounded-each-hop-hooks-when-enforced"
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
                    edge.attributes.get("redirect_scope") == "each-direct-connection-filtered"
                    for edge in typescript_secure_network_controls
                ),
                "secure_lookup_configured": sum(
                    edge.attributes.get("dns_scope") == "secure-lookup-configured-when-enforced"
                    for edge in typescript_secure_network_controls
                ),
                "dns_connection_pinned_unless_proxied": sum(
                    edge.attributes.get("dns_scope") == "connection-pinned-unless-proxied"
                    for edge in typescript_secure_network_controls
                ),
                "dns_connection_pinned": sum(
                    edge.attributes.get("dns_scope") == "connection-pinned"
                    for edge in typescript_secure_network_controls
                ),
                "dns_preflight_only_rebinding_residual": sum(
                    edge.attributes.get("dns_scope") == "preflight-only-rebinding-residual"
                    for edge in typescript_secure_network_controls
                ),
                "dns_connection_time_filtered_unless_proxied": sum(
                    edge.attributes.get("dns_scope") == "connection-time-filtered-unless-proxied"
                    for edge in typescript_secure_network_controls
                ),
                "dns_connection_pinned_unless_configured_route": sum(
                    edge.attributes.get("dns_scope") == "connection-pinned-unless-configured-route"
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
                    edge.attributes.get("proxy_scope") == "caller-global-or-environment-dependent"
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
                    edge.attributes.get("transport_scope") == "imported-axios-client-instance"
                    for edge in typescript_secure_network_controls
                ),
                "configured_address_allowlist": sum(
                    edge.attributes.get("escape_hatch") == "configured-address-allowlist"
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
                    item.attributes.get("remote_card_endpoint_scope") == "same-origin-constrained"
                    for item in a2a_rpc_capabilities
                ),
                "typescript": sum(
                    item.attributes.get("frontend") == "typescript" for item in a2a_rpc_capabilities
                ),
                "python": sum(
                    item.attributes.get("frontend") == "python" for item in a2a_rpc_capabilities
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
            "python_path_segment_sanitizers": {
                "total": len(python_path_segment_sanitizer_edges),
                "sha256": sum(
                    edge.attributes.get("algorithm") == "sha256"
                    for edge in python_path_segment_sanitizer_edges
                ),
                "hexadecimal": sum(
                    edge.attributes.get("output_encoding") == "hexadecimal"
                    for edge in python_path_segment_sanitizer_edges
                ),
                "capability_edges": len(python_path_segment_sanitizer_edges),
            },
            "python_dify_agent_shell_layers": {
                "total": len(python_dify_agent_shell_edges),
                "runtime_edges": len(python_dify_agent_runtime_edges),
                "default_disabled": sum(
                    edge.attributes.get("enabled_default") is False
                    for edge in python_dify_agent_runtime_edges
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
        "schema_version": 125,
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
            "python_provider_call_attribution": {
                name: sum(result["python_provider_call_attribution"][name] for result in successful)
                for name in (
                    "calls",
                    "production_calls",
                    "test_calls",
                    "repositories",
                    "production_repositories",
                    "sdk_calls",
                    "wrapper_calls",
                    "langchain_wrapper_calls",
                    "pydantic_ai_wrapper_calls",
                    "agentscope_wrapper_calls",
                    "agno_wrapper_calls",
                    "autogen_wrapper_calls",
                    "literal_models",
                    *PYTHON_PROVIDER_METRICS,
                )
            },
            "typescript_provider_call_attribution": {
                name: sum(
                    result["typescript_provider_call_attribution"][name] for result in successful
                )
                for name in (
                    "calls",
                    "production_calls",
                    "test_calls",
                    "repositories",
                    "production_repositories",
                    "native_sdk_calls",
                    "ai_sdk_calls",
                    "factory_calls",
                    "model_calls",
                    "configured_instance_calls",
                    "typed_parameter_model_calls",
                    "class_field_model_calls",
                    "class_accessor_model_calls",
                    "literal_binding_models",
                    "literal_models",
                    *TYPESCRIPT_PROVIDER_METRICS,
                )
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
            "python_computer_tools": {
                name: sum(result["python_computer_tools"][name] for result in successful)
                for name in (
                    "instances",
                    "non_test_instances",
                    "local_execution",
                    "safety_check_handlers_configured",
                    "safety_check_auto_acknowledge_all",
                    "safety_check_inline_lambda_auto_ack",
                    "safety_check_same_file_callback_auto_ack",
                    "safety_check_unresolved",
                    "capability_edges",
                    "resolved_agent_edges",
                )
            },
            "python_local_shell_tools": {
                name: sum(result["python_local_shell_tools"][name] for result in successful)
                for name in (
                    "instances",
                    "non_test_instances",
                    "approval_unavailable",
                    "capability_edges",
                    "resolved_agent_edges",
                    "repositories",
                )
            },
            "python_code_interpreter_tools": {
                name: sum(result["python_code_interpreter_tools"][name] for result in successful)
                for name in (
                    "instances",
                    "non_test_instances",
                    "approval_unavailable",
                    "auto_containers",
                    "capability_edges",
                    "resolved_agent_edges",
                    "repositories",
                )
            },
            "python_openai_hosted_tools": {
                name: sum(result["python_openai_hosted_tools"][name] for result in successful)
                for name in (
                    "instances",
                    "non_test_instances",
                    "approval_unavailable",
                    "web_search",
                    "web_external_access_sdk_default",
                    "file_search",
                    "literal_vector_store_scope",
                    "image_generation",
                    "capability_edges",
                    "resolved_agent_edges",
                    "repositories",
                )
            },
            "python_sandbox_agents": {
                name: sum(result["python_sandbox_agents"][name] for result in successful)
                for name in (
                    "total",
                    "non_test",
                    "mcp_server_edges",
                    "repositories",
                )
            },
            "python_agent_referenced_tools": {
                name: sum(result["python_agent_referenced_tools"][name] for result in successful)
                for name in (
                    "instances",
                    "callables",
                    "constructor_bindings",
                    "inline_constructors",
                    "context_manager_bindings",
                    "agent_as_tool_adapters",
                    "agent_as_tool_delegations",
                    "import_bindings",
                    "imported_callable_exports",
                    "module_single_definitions",
                    "non_test_instances",
                    "capability_edges",
                    "resolved_agent_edges",
                )
            },
            "python_agent_tool_edges": {
                name: sum(result["python_agent_tool_edges"][name] for result in successful)
                for name in (
                    "total",
                    "resolved",
                    "unresolved",
                    "non_test",
                    "unresolved_non_test",
                )
            },
            "python_agent_mcp_server_edges": {
                name: sum(result["python_agent_mcp_server_edges"][name] for result in successful)
                for name in (
                    "total",
                    "resolved",
                    "non_test",
                    "same_block",
                    "immutable_module",
                    "context_managed",
                    "repositories",
                )
            },
            "python_fastmcp_server_tool_edges": {
                name: sum(result["python_fastmcp_server_tool_edges"][name] for result in successful)
                for name in (
                    "total",
                    "resolved",
                    "non_test",
                    "agent_reachable_tools",
                    "agent_reachable_capabilities",
                    "non_test_agent_reachable_capabilities",
                    "repositories",
                )
            },
            "python_function_tool_wrappers": {
                name: sum(result["python_function_tool_wrappers"][name] for result in successful)
                for name in (
                    "instances",
                    "non_test_instances",
                    "approval_enabled",
                    "capability_edges",
                    "resolved_agent_edges",
                )
            },
            "python_agent_helper_returns": {
                name: sum(result["python_agent_helper_returns"][name] for result in successful)
                for name in (
                    "resolved_edges",
                    "unique_agent_targets",
                    "non_test_edges",
                )
            },
            "python_local_agent_factory_returns": {
                name: sum(
                    result["python_local_agent_factory_returns"][name] for result in successful
                )
                for name in (
                    "resolved_edges",
                    "unique_agent_targets",
                    "non_test_edges",
                    "repositories",
                )
            },
            "python_typed_tool_parameters": {
                name: sum(result["python_typed_tool_parameters"][name] for result in successful)
                for name in (
                    "parameter_bindings",
                    "resolved_edges",
                    "verified_call_sites",
                    "concrete_targets",
                    "non_test_edges",
                )
            },
            "python_contextual_imports": {
                name: sum(result["python_contextual_imports"][name] for result in successful)
                for name in (
                    "resolved_tool_edges",
                    "unique_tool_targets",
                    "tool_capability_targets",
                    "non_test_tool_edges",
                    "network_helper_capabilities",
                    "dynamic_network_helper_capabilities",
                )
            },
            "python_browser_evaluate": {
                name: sum(result["python_browser_evaluate"][name] for result in successful)
                for name in ("total", "dynamic", "receiver_proven")
            },
            "python_browser_evaluator_apis": dict(
                sorted(
                    sum(
                        (
                            Counter(result["python_browser_evaluate"]["apis"])
                            for result in successful
                        ),
                        Counter(),
                    ).items()
                )
            ),
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
            "python_imported_literal_origins": {
                name: sum(result["python_imported_literal_origins"][name] for result in successful)
                for name in (
                    "capabilities",
                    "source_bindings",
                    "contextual_helper_capabilities",
                    "capability_edges",
                )
            },
            "python_imported_class_network_helpers": {
                name: sum(
                    result["python_imported_class_network_helpers"][name] for result in successful
                )
                for name in ("capabilities", "dynamic_origins", "callees", "capability_edges")
            },
            "python_urllib_network": {
                name: sum(result["python_urllib_network"][name] for result in successful)
                for name in ("capabilities", "dynamic_origins", "capability_edges")
            },
            "python_network_origin_controls": {
                name: sum(result["python_network_origin_controls"][name] for result in successful)
                for name in (
                    "total",
                    "redirects_disabled",
                    "redirects_unresolved",
                    "dns_unresolved",
                )
            },
            "python_secure_network_controls": {
                name: sum(result["python_secure_network_controls"][name] for result in successful)
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
                    result["typescript_axios_instance_network"][name] for result in successful
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
                name: sum(result["typescript_composio_cli_upload"][name] for result in successful)
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
                    result["typescript_google_adk_openapi_rest_tool"][name] for result in successful
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
                    result["python_openai_mcp_approval_default"][name] for result in successful
                )
                for name in (
                    "settings",
                    "disabled_default",
                    "agent_server_edges",
                    "configured_by_edges",
                )
            },
            "python_openhands_conversation_security": {
                name: sum(
                    result["python_openhands_conversation_security"][name] for result in successful
                )
                for name in (
                    "tools",
                    "terminal_tools",
                    "file_editor_tools",
                    "capabilities",
                    "analyzer_controls",
                    "confirmation_controls",
                    "disabled_default_settings",
                    "agent_tool_edges",
                    "risk_analysis_edges",
                    "human_approval_edges",
                    "approval_findings",
                    "filesystem_findings",
                )
            }
            | {
                "repositories": sum(
                    result["python_openhands_conversation_security"]["tools"] > 0
                    for result in successful
                )
            },
            "python_trae_agent_default_tools": {
                name: sum(result["python_trae_agent_default_tools"][name] for result in successful)
                for name in (
                    "tools",
                    "bash_tools",
                    "editor_tools",
                    "capabilities",
                    "approval_settings",
                    "isolation_settings",
                    "agent_tool_edges",
                    "configured_by_edges",
                    "execution_findings",
                    "approval_findings",
                    "filesystem_findings",
                )
            }
            | {
                "repositories": sum(
                    result["python_trae_agent_default_tools"]["tools"] > 0 for result in successful
                )
            },
            "typescript_roo_command_auto_approval": {
                name: sum(
                    result["typescript_roo_command_auto_approval"][name] for result in successful
                )
                for name in (
                    "agents",
                    "tools",
                    "capabilities",
                    "controls",
                    "settings",
                    "agent_tool_edges",
                    "capability_edges",
                    "setting_edges",
                    "control_edges",
                    "execution_findings",
                    "approval_findings",
                )
            }
            | {
                "repositories": sum(
                    result["typescript_roo_command_auto_approval"]["tools"] > 0
                    for result in successful
                )
            },
            "typescript_continue_plan_mode_approval": {
                name: sum(
                    result["typescript_continue_plan_mode_approval"][name] for result in successful
                )
                for name in (
                    "frameworks",
                    "agents",
                    "tools",
                    "capabilities",
                    "controls",
                    "settings",
                    "agent_tool_edges",
                    "capability_edges",
                    "setting_edges",
                    "control_edges",
                    "execution_findings",
                    "approval_findings",
                )
            }
            | {
                "repositories": sum(
                    result["typescript_continue_plan_mode_approval"]["tools"] > 0
                    for result in successful
                )
            },
            "typescript_continue_plan_mode_mcp_approval": {
                name: sum(
                    result["typescript_continue_plan_mode_mcp_approval"][name]
                    for result in successful
                )
                for name in (
                    "agents",
                    "tools",
                    "capabilities",
                    "servers",
                    "controls",
                    "settings",
                    "agent_tool_edges",
                    "capability_edges",
                    "server_edges",
                    "setting_edges",
                    "control_edges",
                    "approval_findings",
                )
            }
            | {
                "repositories": sum(
                    result["typescript_continue_plan_mode_mcp_approval"]["tools"] > 0
                    for result in successful
                )
            },
            "typescript_cline_subagent_approval": {
                name: sum(
                    result["typescript_cline_subagent_approval"][name] for result in successful
                )
                for name in (
                    "frameworks",
                    "agents",
                    "tools",
                    "capabilities",
                    "controls",
                    "settings",
                    "parent_tool_edges",
                    "delegation_edges",
                    "child_capability_edges",
                    "setting_edges",
                    "control_edges",
                    "approval_findings",
                )
            }
            | {
                "repositories": sum(
                    result["typescript_cline_subagent_approval"]["tools"] > 0
                    for result in successful
                )
            },
            "typescript_letta_default_tools": {
                name: sum(result["typescript_letta_default_tools"][name] for result in successful)
                for name in (
                    "agents",
                    "tools",
                    "bash_tools",
                    "write_tools",
                    "capabilities",
                    "approval_settings",
                    "isolation_settings",
                    "agent_tool_edges",
                    "configured_by_edges",
                    "capability_edges",
                    "execution_findings",
                    "approval_findings",
                    "filesystem_findings",
                )
            }
            | {
                "repositories": sum(
                    result["typescript_letta_default_tools"]["tools"] > 0 for result in successful
                )
            },
            "typescript_openai_mcp_approval_default": {
                name: sum(
                    result["typescript_openai_mcp_approval_default"][name] for result in successful
                )
                for name in (
                    "servers",
                    "writable_servers",
                    "read_only_filtered",
                    "agent_server_edges",
                    "configured_by_edges",
                    "findings",
                )
            },
            "python_agno_mcp_confirmation": {
                name: sum(result["python_agno_mcp_confirmation"][name] for result in successful)
                for name in (
                    "servers",
                    "writable_servers",
                    "read_only_filtered",
                    "fully_confirmed",
                    "agent_server_edges",
                    "configured_by_edges",
                    "findings",
                )
            },
            "python_semantic_kernel_mcp_sampling": {
                name: sum(
                    result["python_semantic_kernel_mcp_sampling"][name] for result in successful
                )
                for name in (
                    "servers",
                    "capabilities",
                    "auto_approved",
                    "denied_default",
                    "denied_explicit",
                    "callback_controlled",
                    "unresolved_explicit",
                    "agent_server_edges",
                    "configured_by_edges",
                    "deny_control_edges",
                    "findings",
                )
            },
            "mcp_sampling_consent": {
                name: sum(result["mcp_sampling_consent"][name] for result in successful)
                for name in (
                    "handlers",
                    "default_scope_handlers",
                    "automatic_fulfilment",
                    "default_scope_automatic_fulfilment",
                    "human_confirmed",
                    "denied_handler",
                    "unresolved_handler",
                    "python",
                    "typescript",
                    "model_provider",
                    "protocol_edges",
                    "configured_by_edges",
                    "consent_control_edges",
                    "token_budget_edges",
                    "findings",
                )
            },
            "mcp_elicitation_consent": {
                name: sum(result["mcp_elicitation_consent"][name] for result in successful)
                for name in (
                    "handlers",
                    "default_scope_handlers",
                    "automatic_acceptance",
                    "default_scope_automatic_acceptance",
                    "human_confirmed",
                    "declined_handler",
                    "unresolved_handler",
                    "python",
                    "typescript",
                    "form_capable",
                    "url_capable",
                    "human_confirmed_url_acceptance",
                    "full_url_disclosure",
                    "missing_full_url_disclosure",
                    "protocol_edges",
                    "configured_by_edges",
                    "consent_control_edges",
                    "findings",
                    "url_disclosure_findings",
                )
            },
            "approval_callback_bypass": {
                name: sum(result["approval_callback_bypass"][name] for result in successful)
                for name in (
                    "tools",
                    "python_tools",
                    "typescript_tools",
                    "configured_by_edges",
                    "findings",
                )
            },
            "mcp_package_launchers": {
                name: sum(result["mcp_package_launchers"][name] for result in successful)
                for name in (
                    "total",
                    "non_test",
                    "auto_install",
                    "unpinned",
                    "floating",
                    "exact",
                    "python",
                    "json",
                    "typescript",
                    "findings",
                )
            },
            "python_import_bound_mcp_stdio_servers": {
                name: sum(
                    result["python_import_bound_mcp_stdio_servers"][name] for result in successful
                )
                for name in (
                    "total",
                    "non_test",
                    "symbolized_assigned",
                    "symbolized_context_managed",
                    "symbolized_bound",
                    "package_backed",
                    "non_package",
                    "repositories",
                )
            },
            "python_import_bound_mcp_in_process_servers": {
                name: sum(
                    result["python_import_bound_mcp_in_process_servers"][name]
                    for result in successful
                )
                for name in (
                    "total",
                    "non_test",
                    "symbolized_assigned",
                    "symbolized_context_managed",
                    "symbolized_bound",
                    "repositories",
                )
            },
            "python_imported_mcp_server_subclasses": {
                name: sum(
                    result["python_imported_mcp_server_subclasses"][name] for result in successful
                )
                for name in (
                    "instances",
                    "non_test_instances",
                    "resolved_agent_edges",
                    "repositories",
                )
            },
            "python_google_adk_bigquery_audit": {
                name: sum(result["python_google_adk_bigquery_audit"][name] for result in successful)
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
            "python_skyvern_action_history": {
                name: sum(result["python_skyvern_action_history"][name] for result in successful)
                for name in (
                    "deployed_controls",
                    "production_deployments",
                    "best_effort_controls",
                    "actor_attribution_unresolved",
                    "storage_capabilities",
                    "agent_control_edges",
                    "tool_control_edges",
                    "external_action_control_edges",
                    "storage_edges",
                )
            },
            "typescript_network_origin_controls": {
                name: sum(
                    result["typescript_network_origin_controls"][name] for result in successful
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
                    result["typescript_secure_network_controls"][name] for result in successful
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
            "python_path_segment_sanitizers": {
                name: sum(result["python_path_segment_sanitizers"][name] for result in successful)
                for name in ("total", "sha256", "hexadecimal", "capability_edges")
            }
            | {
                "repositories": sum(
                    result["python_path_segment_sanitizers"]["total"] > 0 for result in successful
                )
            },
            "python_dify_agent_shell_layers": {
                name: sum(result["python_dify_agent_shell_layers"][name] for result in successful)
                for name in ("total", "runtime_edges", "default_disabled")
            }
            | {
                "repositories": sum(
                    result["python_dify_agent_shell_layers"]["total"] > 0 for result in successful
                )
            },
            "python_filesystem_mutations": {
                "total": sum(
                    result["python_filesystem_mutations"]["total"] for result in successful
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
                    result["python_filesystem_mutations"]["dynamic_paths"] for result in successful
                ),
                "guarded": sum(
                    result["python_filesystem_mutations"]["guarded"] for result in successful
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

"""Rule engine operating on framework-neutral Agent IR observations."""

from __future__ import annotations

import hashlib

from .analysis import component_context
from .ir import Finding, RepositoryIR


def fingerprint(rule_id: str, path: str, line: int, message: str) -> str:
    material = f"{rule_id}\0{path}\0{line}\0{message}".encode()
    return hashlib.sha256(material).hexdigest()[:20]


def make_finding(
    ir: RepositoryIR,
    component,
    rule_id: str,
    severity: str,
    confidence: str,
    message: str,
    remediation: str,
    result_kind: str = "finding",
) -> Finding:
    evidence = component.evidence
    ir_path, analysis = component_context(ir, component)
    return Finding(
        rule_id,
        severity,
        confidence,
        message,
        evidence,
        remediation,
        fingerprint(rule_id, evidence.path, evidence.line, message),
        result_kind,
        ir_path,
        analysis,
    )


def run_rules(ir: RepositoryIR, *, include_tests: bool = False) -> None:
    """Evaluate deterministic local rules after parsing has completed."""
    ir.findings.clear()
    specialized_mcp_sampling_calls = {
        (component.evidence.path, component.attributes.get("configuration_call_line"))
        for component in ir.components
        if component.kind == "capability"
        and component.name == "model-sampling"
        and component.attributes.get("analysis")
        == "python-semantic-kernel-mcp-sampling-approval"
    }
    for component in ir.components:
        if component.attributes.get("scope") == "test" and not include_tests:
            continue
        if (
            component.kind == "capability"
            and component.name == "shell-execution"
            and component.attributes.get("shell")
            and component.attributes.get("dynamic_command")
        ):
            ir.findings.append(
                make_finding(
                    ir,
                    component,
                    "AV-EXEC001",
                    "high",
                    "high",
                    "A dynamic command is executed through a system shell",
                    "Pass a fixed argv list with shell=False, or strictly validate and allowlist the command.",
                )
            )
        if component.kind == "sandbox-boundary":
            messages = {
                "docker-socket": "A container mounts the host Docker socket",
                "privileged-container": "A container runs in privileged mode",
                "host-network": "A container shares the host network namespace",
                "host-pid": "A container shares the host process namespace",
                "host-ipc": "A container shares the host IPC namespace",
                "service-account-token": "A workload automatically mounts a Kubernetes service-account token",
                "privilege-escalation": "A container explicitly allows privilege escalation",
                "root-host-mount": "A container mounts the host filesystem root",
                "host-path-mount": "A Kubernetes workload mounts a host path",
                "host-credential-mount": "A container mounts host credential material",
            }
            remediations = {
                "host-credential-mount": (
                    "Remove the host credential bind mount; use narrowly scoped, short-lived "
                    "credentials or a mediated credential agent instead."
                )
            }
            ir.findings.append(
                make_finding(
                    ir,
                    component,
                    "AV-SANDBOX001",
                    "high",
                    "high",
                    messages.get(component.name, "A container crosses a host isolation boundary"),
                    remediations.get(
                        component.name,
                        "Remove the host boundary, or replace it with a narrowly scoped least-privilege interface.",
                    ),
                    "review",
                )
            )
        if (
            component.kind == "capability"
            and component.name == "code-execution"
            and component.attributes.get("dynamic_input")
            and (
                component.attributes.get("execution_context") != "browser-page"
                or component.attributes.get("receiver_proof")
                not in {None, "unresolved-browser-import-context"}
            )
        ):
            api = component.attributes.get("api", "dynamic evaluator")
            ir.findings.append(
                make_finding(
                    ir,
                    component,
                    "AV-EXEC002",
                    "high",
                    "medium",
                    f"Dynamic input reaches {api}()",
                    "Replace dynamic evaluation with a typed parser or execute inside a least-privilege sandbox.",
                )
            )
        if (
            component.kind == "control-setting"
            and component.name == "auto-approval"
            and (component.evidence.path, component.evidence.line)
            not in specialized_mcp_sampling_calls
        ):
            ir.findings.append(
                make_finding(
                    ir,
                    component,
                    "AV-APPROVAL001",
                    "high",
                    "medium",
                    "Configuration or code exposes an approval-bypass path",
                    "Disable auto-approval for privileged tools or scope it to an explicit low-risk allowlist.",
                    "review",
                )
            )
        if (
            component.kind == "capability"
            and component.name == "model-sampling"
            and component.attributes.get("analysis")
            == "python-semantic-kernel-mcp-sampling-approval"
            and component.attributes.get("input_authority") == "mcp-server"
            and component.attributes.get("auto_approved") is True
            and component.attributes.get("approval_policy") == "auto-approved-explicit"
        ):
            _, context = component_context(ir, component)
            if context.get("direct_agents"):
                ir.findings.append(
                    make_finding(
                        ir,
                        component,
                        "AV-MCP004",
                        "high",
                        "high",
                        "A reachable Semantic Kernel MCP server can auto-approve its own model-sampling requests",
                        "Keep sampling_auto_approve disabled and use a fail-closed sampling_consent_callback with user review, model allowlists, and spending limits.",
                        "review",
                    )
                )
        if (
            component.kind == "capability"
            and component.name == "model-sampling"
            and component.attributes.get("analysis")
            in {
                "python-mcp-sampling-callback-consent",
                "python-pydantic-ai-mcp-sampling-model",
                "typescript-mcp-sampling-handler-consent",
            }
            and component.attributes.get("input_authority") == "mcp-server"
            and component.attributes.get("response_created") is True
            and component.attributes.get("approval_policy") == "automatic-fulfilment"
        ):
            ir.findings.append(
                make_finding(
                    ir,
                    component,
                    "AV-MCP005",
                    "high",
                    "high",
                    "An MCP client automatically fulfills server sampling requests without a proven user decision",
                    "Show the complete sampling request, require a fail-closed user decision, and enforce model and token-spend limits before invoking a provider or returning the sampling result.",
                    "review",
                )
            )
        if (
            component.kind == "capability"
            and component.name == "user-elicitation"
            and component.attributes.get("analysis")
            in {
                "python-fastmcp-elicitation-handler-consent",
                "python-mcp-elicitation-callback-consent",
                "typescript-mcp-elicitation-handler-consent",
            }
            and component.attributes.get("input_authority") == "mcp-server"
            and component.attributes.get("acceptance_created") is True
            and component.attributes.get("approval_policy") == "automatic-accept"
        ):
            ir.findings.append(
                make_finding(
                    ir,
                    component,
                    "AV-MCP006",
                    "high",
                    "high",
                    "An MCP client accepts server elicitation without a proven user decision",
                    "Show the requesting server and complete elicitation request, collect or confirm the user's response, offer decline and cancel, and validate form data or URL destinations before returning acceptance.",
                    "review",
                )
            )
        if (
            component.kind == "capability"
            and component.name == "user-elicitation"
            and component.attributes.get("analysis")
            in {
                "python-fastmcp-elicitation-handler-consent",
                "python-mcp-elicitation-callback-consent",
                "typescript-mcp-elicitation-handler-consent",
            }
            and "url" in component.attributes.get("elicitation_modes", ())
            and component.attributes.get("acceptance_created") is True
            and component.attributes.get("approval_policy") == "human-confirmed"
            and component.attributes.get("url_disclosure") != "full-url"
        ):
            ir.findings.append(
                make_finding(
                    ir,
                    component,
                    "AV-MCP007",
                    "high",
                    "high",
                    "An MCP client asks the user to accept URL elicitation without showing the full target URL",
                    "Display the complete server-provided URL before consent, highlight its host, reject unsafe schemes or origins, and open it only after an explicit user decision.",
                    "review",
                )
            )
        if (
            component.kind == "capability"
            and component.name == "mcp-tool-forwarding"
            and not component.attributes.get("allowlist_guard")
        ):
            ir.findings.append(
                make_finding(
                    ir,
                    component,
                    "AV-MCP002",
                    "high",
                    "medium",
                    "A dynamic MCP tool name and arguments are forwarded to a server",
                    "Apply an explicit tool allowlist and argument policy before forwarding the call.",
                    "review",
                )
            )
        if (
            component.kind == "capability"
            and component.name == "filesystem"
            and component.attributes.get("analysis")
            == "typescript-openai-agents-mcp-approval-default"
            and component.attributes.get("write_access") is True
            and component.attributes.get("approval_policy") == "disabled-default"
        ):
            _, context = component_context(ir, component)
            if context.get("direct_agents"):
                ir.findings.append(
                    make_finding(
                        ir,
                        component,
                        "AV-APPROVAL004",
                        "high",
                        "high",
                        "A reachable writable local MCP filesystem server has SDK approval disabled by default",
                        "Expose only a reviewed read-only MCP tool allowlist, or add an authenticated per-action approval mediator before forwarding mutating MCP calls.",
                        "review",
                    )
                )
        if (
            component.kind == "capability"
            and component.name == "filesystem"
            and component.attributes.get("analysis")
            == "python-agno-mcp-confirmation-default"
            and component.attributes.get("write_access") is True
            and component.attributes.get("unprotected_mutations")
            and component.attributes.get("approval_policy")
            in {"disabled-default", "disabled-explicit", "partial-static"}
        ):
            _, context = component_context(ir, component)
            if context.get("direct_agents"):
                ir.findings.append(
                    make_finding(
                        ir,
                        component,
                        "AV-APPROVAL005",
                        "high",
                        "high",
                        "A reachable Agno filesystem MCP toolkit leaves mutating tools outside its confirmation policy",
                        "Set requires_confirmation_tools for every exposed mutating filesystem tool, or restrict include_tools to a reviewed read-only allowlist.",
                        "review",
                    )
                )
        if (
            component.kind == "mcp-server"
            and component.attributes.get("auto_install") is True
            and component.attributes.get("version_scope") in {"unpinned", "floating"}
        ):
            package = component.attributes.get("package", "MCP server package")
            version_scope = component.attributes["version_scope"]
            ir.findings.append(
                make_finding(
                    ir,
                    component,
                    "AV-MCP003",
                    "high",
                    "high",
                    f"MCP server auto-installs {version_scope} package {package}",
                    "Pin the MCP server package to an exact reviewed version and update it through a controlled dependency-review process.",
                    "review",
                )
            )
        if (
            component.kind == "capability"
            and component.name == "filesystem"
            and component.attributes.get("write_access")
            and component.attributes.get("dynamic_path")
        ):
            _, context = component_context(ir, component)
            if context.get("tool"):
                if component.attributes.get("path_prefix_check"):
                    ir.findings.append(
                        make_finding(
                            ir,
                            component,
                            "AV-FS002",
                            "high",
                            "high",
                            "An agent tool relies on a string-prefix filesystem boundary check",
                            "Compare resolved path components with Path.is_relative_to(), Path.relative_to(), or os.path.commonpath() instead of string prefixes.",
                            "review",
                        )
                    )
                elif (
                    component.attributes.get("tool_input_path", True)
                    and component.attributes.get("path_boundary_scope") != "constrained"
                ):
                    ir.findings.append(
                        make_finding(
                            ir,
                            component,
                            "AV-FS001",
                            "high",
                            "medium",
                            "An agent tool writes to a dynamic filesystem path",
                            "Constrain writes to a resolved workspace root and reject traversal outside it.",
                            "review",
                        )
                    )
        if (
            component.kind == "capability"
            and component.name == "network"
            and component.attributes.get("dynamic_origin")
        ):
            _, context = component_context(ir, component)
            if context.get("tool"):
                ir.findings.append(
                    make_finding(
                        ir,
                        component,
                        "AV-NET001",
                        "high",
                        "medium",
                        "An agent tool can send an HTTP request to a parameter-controlled origin",
                        "Allowlist schemes and hosts, block local and reserved destinations, re-check resolved addresses, and restrict tool egress.",
                        "review",
                    )
                )
        if component.kind == "capability" and component.name in {
            "shell-execution",
            "filesystem",
        }:
            _, context = component_context(ir, component)
            tool_name = context.get("tool")
            tool = next(
                (
                    candidate
                    for candidate in ir.components
                    if candidate.kind == "tool"
                    and candidate.name == tool_name
                    and candidate.evidence.path == component.evidence.path
                    and candidate.evidence.line == component.evidence.line
                ),
                None,
            )
            constructor = str(tool.attributes.get("constructor", "")) if tool else ""
            exact_privileged_tool = (
                component.name == "shell-execution"
                and component.attributes.get("execution_environment") == "local"
                and constructor.rsplit(".", 1)[-1] in {"ShellTool", "shellTool"}
            ) or (
                component.name == "filesystem"
                and component.attributes.get("write_access")
                and constructor.rsplit(".", 1)[-1]
                in {"ApplyPatchTool", "applyPatchTool"}
            )
            environment_names = (
                tool.attributes.get("approval_bypass_environment_names", []) if tool else []
            )
            if (
                exact_privileged_tool
                and context.get("direct_agents")
                and environment_names
                and tool.attributes.get("approval_bypass_resolution")
                == "same-file-transitive-callback"
            ):
                capability_label = (
                    "local shell" if component.name == "shell-execution" else "filesystem-write"
                )
                finding = make_finding(
                    ir,
                    component,
                    "AV-APPROVAL003",
                    "high",
                    "high",
                    f"An environment variable can auto-approve a reachable {capability_label} tool",
                    "Remove the environment-driven approval shortcut and require an authenticated, per-action decision before executing the tool.",
                )
                finding.analysis.update(
                    {
                        "approval_bypass_environment_names": environment_names,
                        "approval_bypass_resolution": "same-file-transitive-callback",
                    }
                )
                ir.findings.append(finding)
        if component.kind == "capability" and component.name == "external-action":
            actor_gap_edges = [
                edge
                for edge in ir.relationships
                if edge.source_kind == "capability"
                and edge.source_name == component.name
                and edge.relation == "governed-by"
                and edge.target_kind == "control"
                and edge.target_name == "durable-action-record"
                and edge.evidence.path == component.evidence.path
                and edge.evidence.line == component.evidence.line
                and edge.attributes.get("scope") == "production"
                and edge.attributes.get("durability")
                in {"durable-relational-database", "durable-remote-database"}
                and str(edge.attributes.get("actor_attribution", "")).startswith(
                    "unresolved-"
                )
            ]
            if actor_gap_edges:
                ir.findings.append(
                    make_finding(
                        ir,
                        component,
                        "AV-AUDIT001",
                        "medium",
                        "high",
                        "A durable production action record leaves actor attribution unresolved",
                        "Populate and require a non-null authenticated actor identifier before committing the action record; retain execution correlation fields and surface failed writes through metrics or alerts.",
                        "review",
                    )
                )
        if (
            component.kind == "capability"
            and component.name == "a2a-rpc"
            and component.attributes.get("remote_card_endpoint_scope") == "unconstrained"
        ):
            ir.findings.append(
                make_finding(
                    ir,
                    component,
                    "AV-A2A001",
                    "high",
                    "medium",
                    "A remotely fetched A2A AgentCard can select a downstream RPC origin",
                    "Before constructing the A2A client, require every advertised RPC interface to use HTTPS (except an explicit loopback development policy) and the same origin as the card source; also constrain redirects and egress.",
                    "review",
                )
            )
        if (
            component.kind == "capability"
            and component.name == "shell-execution"
            and component.attributes.get("builtin_tool")
            and component.attributes.get("execution_environment") == "local"
        ):
            _, context = component_context(ir, component)
            tool_name = context.get("tool")
            tool = next(
                (
                    candidate
                    for candidate in ir.components
                    if candidate.kind == "tool"
                    and candidate.name == tool_name
                    and candidate.evidence.path == component.evidence.path
                    and candidate.evidence.line == component.evidence.line
                ),
                None,
            )
            if (
                tool
                and context.get("direct_agents")
                and tool.attributes.get("approval_policy")
                in {"disabled-default", "disabled-explicit"}
            ):
                policy = tool.attributes["approval_policy"]
                qualifier = "by default" if policy == "disabled-default" else "explicitly"
                ir.findings.append(
                    make_finding(
                        ir,
                        component,
                        "AV-APPROVAL002",
                        "high",
                        "high",
                        f"A reachable local shell tool has SDK approval disabled {qualifier}",
                        "Enable needs_approval/needsApproval and handle interruptions, or document and enforce an equivalent approval control inside the executor.",
                        "review",
                    )
                )

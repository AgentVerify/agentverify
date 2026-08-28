"""Rule engine operating on framework-neutral Agent IR observations."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from types import MappingProxyType

from .analysis import component_context
from .ir import Finding, RepositoryIR


@dataclass(frozen=True)
class RuleMetadata:
    """Stable user-facing metadata for one enabled reporting rule."""

    rule_id: str
    result_kind: str
    severity: str
    confidence: str
    summary: str
    remediation: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


RULE_DEFINITIONS = tuple(
    sorted(
        (
            RuleMetadata(
                "AV-A2A001",
                "review",
                "high",
                "medium",
                "A remotely fetched A2A AgentCard can select an unconstrained downstream RPC origin",
                "Require HTTPS and same-origin binding for every advertised RPC interface, then constrain redirects and egress.",
            ),
            RuleMetadata(
                "AV-APPROVAL001",
                "review",
                "high",
                "medium",
                "Configuration or code exposes an approval-bypass path",
                "Disable auto-approval for privileged tools or scope it to an explicit low-risk allowlist.",
            ),
            RuleMetadata(
                "AV-APPROVAL002",
                "review",
                "high",
                "high",
                "A reachable local shell tool has approval disabled or exposes no per-action decision hook",
                "Enable the SDK approval mechanism or enforce an equivalent authenticated per-action decision inside the executor.",
            ),
            RuleMetadata(
                "AV-APPROVAL003",
                "finding",
                "high",
                "high",
                "An environment variable can auto-approve a reachable privileged local tool",
                "Remove the environment-driven shortcut and require an authenticated per-action decision.",
            ),
            RuleMetadata(
                "AV-APPROVAL004",
                "review",
                "high",
                "high",
                "A reachable writable local MCP filesystem server has SDK approval disabled by default",
                "Expose a reviewed read-only allowlist or add authenticated per-action approval before mutating calls.",
            ),
            RuleMetadata(
                "AV-APPROVAL005",
                "review",
                "high",
                "high",
                "A reachable Agno filesystem MCP toolkit leaves mutating tools unconfirmed",
                "Require confirmation for every exposed mutation or restrict the toolkit to a reviewed read-only allowlist.",
            ),
            RuleMetadata(
                "AV-APPROVAL006",
                "review",
                "high",
                "high",
                "An OpenHands conversation analyzes privileged actions but leaves confirmation disabled by default",
                "Install ConfirmRisky (or a stricter confirmation policy) on the same conversation and handle rejected pending actions fail closed.",
            ),
            RuleMetadata(
                "AV-APPROVAL007",
                "review",
                "high",
                "high",
                "A command auto-approval allowlist uses a raw string-prefix match without a token boundary",
                "Match the parsed executable and arguments on token boundaries; do not approve a command merely because its raw text starts with an allowed string.",
            ),
            RuleMetadata(
                "AV-APPROVAL008",
                "review",
                "high",
                "high",
                "A selected plan mode discards shell risk escalation short of a hard block",
                "Keep high-risk and unknown shell commands approval-gated in plan mode, or expose only a parsed read-only command allowlist.",
            ),
            RuleMetadata(
                "AV-APPROVAL009",
                "review",
                "high",
                "high",
                "A selected read-oriented mode wildcard-allows unclassified MCP tools",
                "Ask before unclassified MCP calls and auto-allow only a locally reviewed read-only tool allowlist.",
            ),
            RuleMetadata(
                "AV-APPROVAL010",
                "review",
                "high",
                "high",
                "A spawned sub-agent loses the parent tool policy and approval callback",
                "Forward the effective tool policies and approval callback into every spawned agent, and fail closed when either is unavailable.",
            ),
            RuleMetadata(
                "AV-APPROVAL011",
                "review",
                "high",
                "high",
                "A computer-use safety-check callback acknowledges every pending safety check",
                "Review each pending computer safety check before acknowledging it; fail closed for unknown or unsupported checks.",
            ),
            RuleMetadata(
                "AV-AUDIT001",
                "review",
                "medium",
                "high",
                "A durable production action record leaves actor attribution unresolved",
                "Require an authenticated actor identifier and retain execution correlation plus failed-write telemetry.",
            ),
            RuleMetadata(
                "AV-EXEC001",
                "finding",
                "high",
                "high",
                "A dynamic command is executed through a system shell",
                "Pass a fixed argv list with shell disabled, or strictly validate and allowlist the command.",
            ),
            RuleMetadata(
                "AV-EXEC002",
                "finding",
                "high",
                "medium",
                "Dynamic input reaches a proven evaluator or interpreter",
                "Replace dynamic evaluation with a typed parser or use a least-privilege sandbox.",
            ),
            RuleMetadata(
                "AV-FS001",
                "review",
                "high",
                "medium",
                "An agent tool mutates a tool-input-controlled path without a proven narrow boundary",
                "Resolve the path beneath a fixed workspace root and reject traversal outside it.",
            ),
            RuleMetadata(
                "AV-FS002",
                "review",
                "high",
                "high",
                "An agent tool relies on a string-prefix filesystem boundary check",
                "Compare resolved path components with a component-aware containment API.",
            ),
            RuleMetadata(
                "AV-MCP002",
                "review",
                "high",
                "medium",
                "A dynamic MCP tool name and arguments are forwarded without a proven allowlist",
                "Apply an explicit tool allowlist and argument policy before forwarding.",
            ),
            RuleMetadata(
                "AV-MCP003",
                "review",
                "high",
                "high",
                "An MCP server is automatically installed from an unpinned or floating package reference",
                "Pin the package to an exact reviewed version and update it through dependency review.",
            ),
            RuleMetadata(
                "AV-MCP004",
                "review",
                "high",
                "high",
                "A reachable Semantic Kernel MCP server can auto-approve its own sampling requests",
                "Use a fail-closed user decision with model allowlists and token-spend limits.",
            ),
            RuleMetadata(
                "AV-MCP005",
                "review",
                "high",
                "high",
                "An MCP client automatically fulfills server sampling without a proven user decision",
                "Show the complete request and require a fail-closed user decision before provider invocation.",
            ),
            RuleMetadata(
                "AV-MCP006",
                "review",
                "high",
                "high",
                "An MCP client accepts server elicitation without a proven user decision",
                "Show the complete request, offer decline and cancel, and validate submitted data or destinations.",
            ),
            RuleMetadata(
                "AV-MCP007",
                "review",
                "high",
                "high",
                "An MCP client asks for URL consent without showing the full target URL",
                "Display and validate the complete URL before an explicit user decision.",
            ),
            RuleMetadata(
                "AV-NET001",
                "review",
                "high",
                "medium",
                "An agent tool can send an HTTP request to a parameter-controlled origin",
                "Allowlist destinations, block local or reserved addresses, re-check DNS, and restrict egress.",
            ),
            RuleMetadata(
                "AV-SANDBOX001",
                "review",
                "high",
                "high",
                "A container or workload crosses a host isolation boundary",
                "Remove the host boundary or replace it with a narrowly scoped least-privilege interface.",
            ),
        ),
        key=lambda item: item.rule_id,
    )
)
RULE_CATALOG: Mapping[str, RuleMetadata] = MappingProxyType(
    {definition.rule_id: definition for definition in RULE_DEFINITIONS}
)
REPORTING_RULE_IDS = frozenset(RULE_CATALOG)


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
    definition = RULE_CATALOG.get(rule_id)
    if definition is None:
        raise ValueError(f"unknown reporting rule: {rule_id}")
    emitted_metadata = (result_kind, severity, confidence)
    catalog_metadata = (
        definition.result_kind,
        definition.severity,
        definition.confidence,
    )
    if emitted_metadata != catalog_metadata:
        raise ValueError(
            f"reporting metadata for {rule_id} does not match the rule catalog: "
            f"{emitted_metadata!r} != {catalog_metadata!r}"
        )
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
        and component.attributes.get("analysis") == "python-semantic-kernel-mcp-sampling-approval"
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
            and component.attributes.get("analysis") == "python-agno-mcp-confirmation-default"
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
            component.kind == "capability"
            and component.attributes.get("analysis") == "python-openhands-conversation-security"
            and component.attributes.get("approval_gap_anchor") is True
            and component.attributes.get("security_analyzer") != "none"
            and component.attributes.get("approval_policy") == "disabled-default"
        ):
            _, context = component_context(ir, component)
            if context.get("direct_agents"):
                ir.findings.append(
                    make_finding(
                        ir,
                        component,
                        "AV-APPROVAL006",
                        "high",
                        "high",
                        "An OpenHands conversation analyzes privileged actions but leaves confirmation at the NeverConfirm SDK default",
                        "Call set_confirmation_policy(ConfirmRisky(...)) on the same conversation and handle rejected pending actions fail closed before running privileged tools.",
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
                    and not component.attributes.get("tool_input_path_sanitized")
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
                and constructor.rsplit(".", 1)[-1] in {"ApplyPatchTool", "applyPatchTool"}
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
                and str(edge.attributes.get("actor_attribution", "")).startswith("unresolved-")
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
            component.kind == "control"
            and component.name == "command-allowlist"
            and component.attributes.get("agent_reachable") is True
            and component.attributes.get("auto_approval_decision") == "approve"
            and component.attributes.get("match_semantics") == "raw-string-prefix"
            and component.attributes.get("token_boundary") is False
        ):
            ir.findings.append(
                make_finding(
                    ir,
                    component,
                    "AV-APPROVAL007",
                    "high",
                    "high",
                    "A reachable command auto-approval allowlist accepts raw string prefixes without a token boundary",
                    "Parse the command first and compare the executable and argument prefixes on token boundaries; retain explicit user approval for unmatched or ambiguous commands.",
                    "review",
                )
            )
        if (
            component.kind == "control"
            and component.name == "terminal-command-risk-policy"
            and component.attributes.get("agent_reachable") is True
            and component.attributes.get("mode") == "plan"
            and component.attributes.get("mode_default") is False
            and component.attributes.get("static_shell_permission") == "allow"
            and component.attributes.get("high_risk_evaluation") == "allowedWithPermission"
            and component.attributes.get("high_risk_effective_permission") == "allow"
            and component.attributes.get("unknown_evaluation") == "allowedWithPermission"
            and component.attributes.get("unknown_effective_permission") == "allow"
            and component.attributes.get("critical_evaluation") == "disabled"
            and component.attributes.get("critical_effective_permission") == "exclude"
        ):
            ir.findings.append(
                make_finding(
                    ir,
                    component,
                    "AV-APPROVAL008",
                    "high",
                    "high",
                    "Continue CLI plan mode auto-allows high-risk and unknown shell commands after its risk evaluator requests approval",
                    "Return the dynamically evaluated policy whenever it is more restrictive than the static mode policy; for a read-oriented plan mode, keep Bash at ask or use a parsed read-only command allowlist.",
                    "review",
                )
            )
        if (
            component.kind == "control"
            and component.name == "mcp-tool-classification"
            and component.attributes.get("agent_reachable") is True
            and component.attributes.get("mode") == "plan"
            and component.attributes.get("mode_default") is False
            and component.attributes.get("normal_mode_external_tool_permission") == "ask"
            and component.attributes.get("plan_mode_external_tool_permission") == "allow"
            and component.attributes.get("approval_prompt_on_allow") is False
            and component.attributes.get("readonly_metadata") == "discarded"
            and component.attributes.get("risk_classification") == "absent-on-proven-path"
            and component.attributes.get("tool_schema_source") == "mcp-server-discovery"
        ):
            ir.findings.append(
                make_finding(
                    ir,
                    component,
                    "AV-APPROVAL009",
                    "high",
                    "high",
                    "Continue CLI plan mode auto-allows every discovered MCP tool without a read-only or risk classification",
                    "Replace the plan-mode wildcard allow with ask; auto-allow only locally reviewed read-only MCP tools, independent of server-supplied names or descriptions.",
                    "review",
                )
            )
        spawn_agent_policy = component.attributes.get("spawn_agent_policy")
        if (
            component.kind == "control"
            and component.name == "subagent-tool-approval-propagation"
            and component.attributes.get("agent_reachable") is True
            and component.attributes.get("parent_approval_callback") == "configured"
            and component.attributes.get("parent_privileged_tools_gated") is True
            and component.attributes.get("spawn_agent_default_enabled") is True
            and spawn_agent_policy in {"unlisted-auto-approved", "parent-approval-required"}
            and component.attributes.get("child_tool_policies") == "not-forwarded"
            and component.attributes.get("child_approval_callback") == "not-forwarded"
            and component.attributes.get("factory_supports_propagation") is True
        ):
            message = (
                "Cline VS Code auto-approves spawn_agent, then drops its tool policy and approval callback before the child receives local shell and editing tools"
                if spawn_agent_policy == "unlisted-auto-approved"
                else "Cline CLI can approve spawn_agent in sandbox-local mode, then drops its tool policy and approval callback before the child receives local shell and editing tools"
            )
            ir.findings.append(
                make_finding(
                    ir,
                    component,
                    "AV-APPROVAL010",
                    "high",
                    "high",
                    message,
                    "Add spawn_agent to the parent approval policy and forward the effective toolPolicies plus requestToolApproval callback through createSessionSpawnTool into createSpawnAgentTool; fail closed if propagation is unavailable.",
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
                in {"disabled-default", "disabled-explicit", "unavailable"}
            ):
                policy = tool.attributes["approval_policy"]
                title = (
                    "A reachable local shell tool exposes no per-action decision hook"
                    if policy == "unavailable"
                    else "A reachable local shell tool has SDK approval disabled "
                    + ("by default" if policy == "disabled-default" else "explicitly")
                )
                remediation = (
                    "Enforce and document an equivalent human-approval interruption inside the executor, or use an approval-capable local shell tool."
                    if policy == "unavailable"
                    else "Enable needs_approval/needsApproval and handle interruptions, or document and enforce an equivalent approval control inside the executor."
                )
                ir.findings.append(
                    make_finding(
                        ir,
                        component,
                        "AV-APPROVAL002",
                        "high",
                        "high",
                        title,
                        remediation,
                        "review",
                    )
                )
        if (
            component.kind == "capability"
            and component.name == "computer-control"
            and (
                component.attributes.get("builtin_tool") == "computerTool"
                or component.attributes.get("api") == "ComputerTool"
            )
            and component.attributes.get("safety_check_policy") == "auto-acknowledge-all"
        ):
            _, context = component_context(ir, component)
            if context.get("direct_agents"):
                finding = make_finding(
                    ir,
                    component,
                    "AV-APPROVAL011",
                    "high",
                    "high",
                    "A reachable OpenAI computer tool auto-acknowledges every pending safety check",
                    "Handle each pending safety check through an explicit user or policy decision, and fail closed for unknown checks instead of returning every pending check as acknowledged.",
                    "review",
                )
                finding.analysis.update(
                    {
                        "safety_check_handler": component.attributes.get(
                            "safety_check_handler"
                        ),
                        "safety_check_policy": component.attributes.get(
                            "safety_check_policy"
                        ),
                        "safety_check_decision": component.attributes.get(
                            "safety_check_decision"
                        ),
                        "safety_check_acknowledgement_field": component.attributes.get(
                            "safety_check_acknowledgement_field"
                        ),
                        "safety_check_resolution": component.attributes.get(
                            "safety_check_resolution"
                        ),
                    }
                )
                ir.findings.append(finding)

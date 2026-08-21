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
            }
            ir.findings.append(
                make_finding(
                    ir,
                    component,
                    "AV-SANDBOX001",
                    "high",
                    "high",
                    messages.get(component.name, "A container crosses a host isolation boundary"),
                    "Remove the host boundary, or replace it with a narrowly scoped least-privilege interface.",
                    "review",
                )
            )
        if (
            component.kind == "capability"
            and component.name == "code-execution"
            and component.attributes.get("dynamic_input")
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
        if component.kind == "control-setting" and component.name == "auto-approval":
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
            and component.attributes.get("write_access")
            and component.attributes.get("dynamic_path")
        ):
            _, context = component_context(ir, component)
            if context.get("tool"):
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
                        f"A reachable local ShellTool has SDK approval disabled {qualifier}",
                        "Set needs_approval=True and handle interruptions, or document and enforce an equivalent approval control inside the executor.",
                        "review",
                    )
                )

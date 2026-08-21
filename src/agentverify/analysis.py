"""Relationship queries that attach control and reachability context to rule results."""

from __future__ import annotations

from .ir import Component, RepositoryIR


def component_context(ir: RepositoryIR, component: Component) -> tuple[tuple[str, ...], dict]:
    """Resolve direct agent/tool/control context for a capability observation.

    Name-only cross-file resolution would overstate certainty, so a capability edge must share the
    component's source location. Tool and agent references are then resolved by their explicit names.
    """
    if component.kind != "capability":
        return (), {}
    tool_edges = [
        edge
        for edge in ir.relationships
        if edge.source_kind == "tool"
        and edge.relation == "uses"
        and edge.target_kind == "capability"
        and edge.target_name == component.name
        and edge.evidence.path == component.evidence.path
        and edge.evidence.line == component.evidence.line
    ]
    if not tool_edges:
        return (f"capability:{component.name}",), {"approval_coverage": "unresolved"}
    tool_name = min(edge.source_name for edge in tool_edges)
    agents = sorted(
        {
            edge.source_name
            for edge in ir.relationships
            if edge.source_kind == "agent"
            and edge.relation == "uses"
            and edge.target_kind == "tool"
            and edge.target_name == tool_name
        }
    )
    controls = sorted(
        {
            edge.target_name
            for edge in ir.relationships
            if edge.source_kind == "tool"
            and edge.source_name == tool_name
            and edge.relation == "governed-by"
            and edge.target_kind == "control"
        }
    )
    path = (
        *(f"agent:{name}" for name in agents[:1]),
        f"tool:{tool_name}",
        f"capability:{component.name}",
    )
    return path, {
        "direct_agents": agents,
        "tool": tool_name,
        "governing_controls": controls,
        "approval_coverage": "present" if "human-approval" in controls else "unresolved",
    }

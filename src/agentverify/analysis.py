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
    direct_agents = sorted(
        {
            edge.source_name
            for edge in ir.relationships
            if edge.source_kind == "agent"
            and edge.relation == "uses"
            and edge.target_kind == "tool"
            and (edge.target_name == tool_name or edge.attributes.get("target_name") == tool_name)
            and (
                edge.evidence.path == component.evidence.path
                or edge.attributes.get("target_path") == component.evidence.path
            )
        }
    )
    controls = sorted(
        {
            edge.target_name
            for edge in ir.relationships
            if (
                (
                    edge.source_kind == "tool"
                    and edge.source_name == tool_name
                    and edge.evidence.path == component.evidence.path
                )
                or (
                    edge.source_kind == "capability"
                    and edge.source_name == component.name
                    and edge.evidence.path == component.evidence.path
                    and edge.evidence.line == component.evidence.line
                )
            )
            and edge.relation == "governed-by"
            and edge.target_kind == "control"
        }
    )
    delegation_parents: dict[str, set[str]] = {}
    for edge in ir.relationships:
        if (
            edge.source_kind == "agent"
            and edge.relation == "delegates-to"
            and edge.target_kind == "agent"
        ):
            delegation_parents.setdefault(edge.target_name, set()).add(edge.source_name)

    def expand_to_root(agent: str, seen: frozenset[str]) -> list[list[str]]:
        parents = sorted(delegation_parents.get(agent, set()) - set(seen))
        if not parents:
            return [[agent]]
        paths = []
        for parent in parents:
            for parent_path in expand_to_root(parent, seen | {parent}):
                paths.append([*parent_path, agent])
        return paths

    agent_paths = [
        path for agent in direct_agents for path in expand_to_root(agent, frozenset({agent}))
    ]
    selected_agent_path = (
        min(agent_paths, key=lambda path: (len(path), path)) if agent_paths else []
    )
    reachable_agents = sorted({agent for path in agent_paths for agent in path})
    path = (
        *(f"agent:{name}" for name in selected_agent_path),
        f"tool:{tool_name}",
        f"capability:{component.name}",
    )
    return path, {
        "direct_agents": direct_agents,
        "reachable_agents": reachable_agents,
        "tool": tool_name,
        "governing_controls": controls,
        "approval_coverage": "present" if "human-approval" in controls else "unresolved",
        "audit_coverage": (
            "instrumented; exporter durability unresolved"
            if "action-trace" in controls
            else "unresolved"
        ),
    }

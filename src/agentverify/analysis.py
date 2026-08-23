"""Relationship queries that attach control and reachability context to rule results."""

from __future__ import annotations

from .ir import Component, RepositoryIR


def _audit_coverage(controls: set[str] | list[str]) -> str:
    if "durable-action-audit" in controls:
        return "durable and attributable; delivery best-effort"
    if "durable-action-record" in controls:
        return "durable execution record; actor attribution unresolved; delivery best-effort"
    if "action-trace" in controls:
        return "instrumented; exporter durability unresolved"
    return "unresolved"


def component_context(ir: RepositoryIR, component: Component) -> tuple[tuple[str, ...], dict]:
    """Resolve direct agent/tool/control context for a capability observation.

    Name-only cross-file resolution would overstate certainty, so a capability edge must share the
    component's source location. Tool and agent references prefer module-qualified symbol IDs and
    retain a conservative location-aware fallback for older or partially resolved IR.
    """
    if component.kind != "capability":
        return (), {}
    capability_control_edges = [
        edge
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.source_name == component.name
        and edge.evidence.path == component.evidence.path
        and edge.evidence.line == component.evidence.line
        and edge.relation == "governed-by"
        and edge.target_kind == "control"
    ]
    capability_controls = sorted({edge.target_name for edge in capability_control_edges})
    capability_control_effects = {
        control: sorted(
            {
                str(edge.attributes["policy_effect"])
                for edge in capability_control_edges
                if edge.target_name == control and edge.attributes.get("policy_effect")
            }
        )
        for control in capability_controls
    }
    delegation_parents: dict[str, set[tuple[str, str]]] = {}
    for edge in ir.relationships:
        if (
            edge.source_kind == "agent"
            and edge.relation == "delegates-to"
            and edge.target_kind == "agent"
        ):
            target_key = edge.target_id or f"name:{edge.target_name}"
            source_key = edge.source_id or f"name:{edge.source_name}"
            delegation_parents.setdefault(target_key, set()).add((source_key, edge.source_name))

    def expand_to_root(agent_key: str, agent_name: str, seen: frozenset[str]) -> list[list[str]]:
        parents = sorted(
            (
                parent
                for parent in delegation_parents.get(agent_key, set())
                if parent[0] not in seen
            ),
            key=lambda parent: (parent[1], parent[0]),
        )
        if not parents:
            return [[agent_name]]
        paths = []
        for parent_key, parent_name in parents:
            for parent_path in expand_to_root(parent_key, parent_name, seen | {parent_key}):
                paths.append([*parent_path, agent_name])
        return paths

    mcp_server_edges = [
        edge
        for edge in ir.relationships
        if edge.source_kind == "mcp-server"
        and edge.relation == "uses"
        and edge.target_kind == "capability"
        and edge.target_name == component.name
        and edge.evidence.path == component.evidence.path
        and edge.evidence.line == component.evidence.line
    ]
    if mcp_server_edges:
        server_edge = min(
            mcp_server_edges, key=lambda edge: (edge.source_id or "", edge.source_name)
        )
        server_name = server_edge.source_name
        server_id = server_edge.source_id
        direct_agent_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "agent"
            and edge.relation == "uses"
            and edge.target_kind == "mcp-server"
            and (
                (server_id is not None and edge.target_id == server_id)
                or (
                    (server_id is None or edge.target_id is None)
                    and edge.target_name == server_name
                    and edge.evidence.path == component.evidence.path
                )
            )
        ]
        agent_paths = [
            path
            for edge in direct_agent_edges
            for path in expand_to_root(
                edge.source_id or f"name:{edge.source_name}",
                edge.source_name,
                frozenset({edge.source_id or f"name:{edge.source_name}"}),
            )
        ]
        selected_agent_path = (
            min(agent_paths, key=lambda path: (len(path), path)) if agent_paths else []
        )
        setting_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "mcp-server"
            and edge.source_name == server_name
            and edge.relation == "configured-by"
            and edge.target_kind == "control-setting"
            and (
                (server_id is not None and edge.source_id == server_id)
                or (
                    (server_id is None or edge.source_id is None)
                    and edge.evidence.path == component.evidence.path
                )
            )
        ]
        settings = sorted({edge.target_name for edge in setting_edges})
        approval_policy = component.attributes.get("approval_policy", "unresolved")
        return (
            *(f"agent:{name}" for name in selected_agent_path),
            f"mcp-server:{server_name}",
            f"capability:{component.name}",
        ), {
            "direct_agents": sorted({edge.source_name for edge in direct_agent_edges}),
            "reachable_agents": sorted({agent for path in agent_paths for agent in path}),
            "mcp_server": server_name,
            "control_settings": settings,
            "governing_controls": capability_controls,
            "governing_control_effects": capability_control_effects,
            "approval_coverage": approval_policy,
            "audit_coverage": _audit_coverage(capability_controls),
        }
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
        protocol_edges = [
            edge
            for edge in ir.relationships
            if edge.source_kind == "protocol"
            and edge.relation == "uses"
            and edge.target_kind == "capability"
            and edge.target_name == component.name
            and edge.evidence.path == component.evidence.path
            and edge.evidence.line == component.evidence.line
        ]
        if protocol_edges:
            protocol = min(
                protocol_edges,
                key=lambda edge: (edge.source_id or "", edge.source_name),
            ).source_name
            return (f"protocol:{protocol}", f"capability:{component.name}"), {
                "protocol": protocol,
                "governing_controls": capability_controls,
                "governing_control_effects": capability_control_effects,
                "approval_coverage": component.attributes.get(
                    "approval_policy", "unresolved"
                ),
                "audit_coverage": _audit_coverage(capability_controls),
            }
        return (f"capability:{component.name}",), {
            "governing_controls": capability_controls,
            "governing_control_effects": capability_control_effects,
            "approval_coverage": (
                "present" if "human-approval" in capability_controls else "unresolved"
            ),
            "audit_coverage": _audit_coverage(capability_controls),
        }
    tool_edge = min(tool_edges, key=lambda edge: (edge.source_id or "", edge.source_name))
    tool_name = tool_edge.source_name
    tool_id = tool_edge.source_id
    mcp_tool_edges = [
        edge
        for edge in ir.relationships
        if edge.source_kind == "mcp-server"
        and edge.relation == "uses"
        and edge.target_kind == "tool"
        and (
            (tool_id is not None and edge.target_id == tool_id)
            or (
                (tool_id is None or edge.target_id is None)
                and edge.target_name == tool_name
                and edge.evidence.path == component.evidence.path
            )
        )
    ]
    mcp_agent_routes = [
        (server_edge, agent_edge)
        for server_edge in mcp_tool_edges
        for agent_edge in ir.relationships
        if agent_edge.source_kind == "agent"
        and agent_edge.relation == "uses"
        and agent_edge.target_kind == "mcp-server"
        and (
            (
                server_edge.source_id is not None
                and agent_edge.target_id == server_edge.source_id
            )
            or (
                (server_edge.source_id is None or agent_edge.target_id is None)
                and agent_edge.target_name == server_edge.source_name
                and agent_edge.evidence.path == component.evidence.path
            )
        )
    ]
    direct_agent_edges = [
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.relation == "uses"
        and edge.target_kind == "tool"
        and (
            (tool_id is not None and edge.target_id == tool_id)
            or (
                (tool_id is None or edge.target_id is None)
                and (
                    edge.target_name == tool_name or edge.attributes.get("target_name") == tool_name
                )
                and (
                    edge.evidence.path == component.evidence.path
                    or edge.attributes.get("target_path") == component.evidence.path
                )
            )
        )
    ]
    direct_agents = sorted(
        {edge.source_name for edge in direct_agent_edges}
        | {edge.source_name for _server, edge in mcp_agent_routes}
    )
    governing_control_edges = [
        edge
        for edge in ir.relationships
        if (
            (
                edge.source_kind == "tool"
                and edge.source_name == tool_name
                and (
                    (tool_id is not None and edge.source_id == tool_id)
                    or (
                        (tool_id is None or edge.source_id is None)
                        and edge.evidence.path == component.evidence.path
                    )
                )
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
    ]
    controls = sorted({edge.target_name for edge in governing_control_edges})
    control_effects = {
        control: sorted(
            {
                str(edge.attributes["policy_effect"])
                for edge in governing_control_edges
                if edge.target_name == control and edge.attributes.get("policy_effect")
            }
        )
        for control in controls
    }
    direct_agent_paths = [
        (path, None)
        for edge in direct_agent_edges
        for path in expand_to_root(
            edge.source_id or f"name:{edge.source_name}",
            edge.source_name,
            frozenset({edge.source_id or f"name:{edge.source_name}"}),
        )
    ]
    mcp_agent_paths = [
        (path, server_edge.source_name)
        for server_edge, edge in mcp_agent_routes
        for path in expand_to_root(
            edge.source_id or f"name:{edge.source_name}",
            edge.source_name,
            frozenset({edge.source_id or f"name:{edge.source_name}"}),
        )
    ]
    agent_paths = [*direct_agent_paths, *mcp_agent_paths]
    selected_agent_path, selected_mcp_server = (
        min(
            agent_paths,
            key=lambda item: (
                len(item[0]) + (1 if item[1] else 0),
                item[0],
                item[1] or "",
            ),
        )
        if agent_paths
        else ([], None)
    )
    reachable_agents = sorted(
        {agent for agent_path, _server in agent_paths for agent in agent_path}
    )
    path = (
        *(f"agent:{name}" for name in selected_agent_path),
        *((f"mcp-server:{selected_mcp_server}",) if selected_mcp_server else ()),
        f"tool:{tool_name}",
        f"capability:{component.name}",
    )
    context = {
        "direct_agents": direct_agents,
        "reachable_agents": reachable_agents,
        "tool": tool_name,
        "governing_controls": controls,
        "governing_control_effects": control_effects,
        "approval_coverage": component.attributes.get(
            "approval_policy",
            "present" if "human-approval" in controls else "unresolved",
        ),
        "audit_coverage": _audit_coverage(controls),
    }
    if selected_mcp_server:
        context["mcp_server"] = selected_mcp_server
    return path, context

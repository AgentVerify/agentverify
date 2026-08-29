from agents import Agent
from agents.mcp import MCPServerStdio
from star_barrel import (
    IMPORTED_SELECTIVE as STAR_REEXPORTED_SELECTIVE,
    MUTATED_POLICY as STAR_REEXPORTED_MUTATED_POLICY,
)


def build_star_agent() -> Agent:
    star_reexported_selective_approval = MCPServerStdio(
        params={"command": "python", "args": ["mcp_server.py"]},
        require_approval=STAR_REEXPORTED_SELECTIVE,
    )
    star_reexported_mutated_approval = MCPServerStdio(
        params={"command": "python", "args": ["mcp_server.py"]},
        require_approval=STAR_REEXPORTED_MUTATED_POLICY,
    )
    return Agent(
        name="Python MCP star reexport approval policy agent",
        mcp_servers=[
            star_reexported_selective_approval,
            star_reexported_mutated_approval,
        ],
    )

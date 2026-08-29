from agents import Agent
from agents.mcp import MCPServerStdio
from policies import *


def build_star_import_agent() -> Agent:
    star_import_selective_approval = MCPServerStdio(
        params={"command": "python", "args": ["mcp_server.py"]},
        require_approval=IMPORTED_SELECTIVE,
    )
    star_import_mutated_approval = MCPServerStdio(
        params={"command": "python", "args": ["mcp_server.py"]},
        require_approval=MUTATED_POLICY,
    )
    return Agent(
        name="Python MCP consumer star import approval policy agent",
        mcp_servers=[
            star_import_selective_approval,
            star_import_mutated_approval,
        ],
    )

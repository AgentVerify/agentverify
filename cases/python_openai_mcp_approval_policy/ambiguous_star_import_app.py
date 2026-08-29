from agents import Agent
from agents.mcp import MCPServerStdio
from alternate_policies import *
from policies import *


def build_ambiguous_star_import_agent() -> Agent:
    ambiguous_star_import_approval = MCPServerStdio(
        params={"command": "python", "args": ["mcp_server.py"]},
        require_approval=IMPORTED_SELECTIVE,
    )
    return Agent(
        name="Python MCP ambiguous star import approval policy agent",
        mcp_servers=[ambiguous_star_import_approval],
    )

from agents import Agent, HostedMCPTool
from alternate_policies import *
from policies import *


def build_ambiguous_star_import_agent() -> Agent:
    return Agent(
        name="Python hosted MCP ambiguous star import approval agent",
        tools=[
            HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "ambiguous_star_import_literal",
                    "server_url": "https://mcp.example.com/mcp",
                    "require_approval": IMPORTED_ALWAYS,
                }
            ),
        ],
    )

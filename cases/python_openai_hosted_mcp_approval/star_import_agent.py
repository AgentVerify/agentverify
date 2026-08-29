from agents import Agent, HostedMCPTool
from policies import *


def build_star_import_agent() -> Agent:
    return Agent(
        name="Python hosted MCP consumer star import approval agent",
        tools=[
            HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "star_import_literal",
                    "server_url": "https://mcp.example.com/mcp",
                    "require_approval": IMPORTED_ALWAYS,
                }
            ),
            HostedMCPTool(tool_config=IMPORTED_TOOL_CONFIG),
            HostedMCPTool(tool_config=MUTATED_TOOL_CONFIG),
        ],
    )

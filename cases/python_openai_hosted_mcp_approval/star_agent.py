from agents import Agent, HostedMCPTool
from star_barrel import (
    IMPORTED_ALWAYS as STAR_REEXPORTED_ALWAYS,
    IMPORTED_TOOL_CONFIG as STAR_REEXPORTED_TOOL_CONFIG,
    MUTATED_TOOL_CONFIG as STAR_REEXPORTED_MUTATED_TOOL_CONFIG,
)


def build_star_agent() -> Agent:
    return Agent(
        name="Python hosted MCP star reexport approval agent",
        tools=[
            HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "star_reexported_literal",
                    "server_url": "https://mcp.example.com/mcp",
                    "require_approval": STAR_REEXPORTED_ALWAYS,
                }
            ),
            HostedMCPTool(tool_config=STAR_REEXPORTED_TOOL_CONFIG),
            HostedMCPTool(tool_config=STAR_REEXPORTED_MUTATED_TOOL_CONFIG),
        ],
    )

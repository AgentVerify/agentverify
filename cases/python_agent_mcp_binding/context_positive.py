from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio


async def run_managed_agent() -> None:
    async with MCPServerStdio(
        command="uvx",
        args=["mcp-server-git"],
    ) as managed_server:
        managed_agent = Agent(
            name="managed",
            mcp_servers=[managed_server],
        )
        print(managed_agent)

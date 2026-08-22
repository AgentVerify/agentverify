from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from local_agents import SandboxAgent


async def rebound_context() -> None:
    async with MCPServerStdio(
        command="uvx",
        args=["mcp-server-git"],
    ) as rebound_server:
        rebound_server = replacement
        Agent(name="rebound-context", mcp_servers=[rebound_server])


async def escaped_context() -> None:
    async with MCPServerStdio(
        command="uvx",
        args=["mcp-server-git"],
    ) as escaped_server:
        pass
    Agent(name="escaped-context", mcp_servers=[escaped_server])


near_sandbox_agent = SandboxAgent(name="near-sandbox")


async def duplicate_context_binding() -> None:
    async with (
        MCPServerStdio(command="one", args=[]) as duplicate_server,
        MCPServerStdio(command="two", args=[]) as duplicate_server,
    ):
        Agent(name="duplicate-context", mcp_servers=[duplicate_server])

from local_agent import Agent
from local_mcp import MCPTools


async def run_agent(root):
    async with MCPTools(
        f"npx -y @modelcontextprotocol/server-filesystem {root}"
    ) as filesystem_tools:
        agent = Agent(tools=[filesystem_tools])
        await agent.run()

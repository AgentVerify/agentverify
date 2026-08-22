from agno.agent import Agent
from agno.tools.mcp import MCPTools


async def run_agent(root):
    async with MCPTools(
        f"npx -y @modelcontextprotocol/server-filesystem {root}"
    ) as filesystem_tools:
        agent = Agent(name="Default Writer", tools=[filesystem_tools])
        await agent.aprint_response("Create notes.txt")

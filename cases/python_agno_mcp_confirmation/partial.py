from agno.agent import Agent
from agno.tools.mcp import MCPTools


async def run_agent(root):
    async with MCPTools(
        f"npx -y @modelcontextprotocol/server-filesystem {root}",
        requires_confirmation_tools=["write_file"],
    ) as filesystem_tools:
        agent = Agent(name="Partially Confirmed Writer", tools=[filesystem_tools])
        await agent.aprint_response("Move notes.txt")

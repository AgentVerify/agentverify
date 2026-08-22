from agno.agent import Agent
from agno.tools.mcp import MCPTools


async def run_agent(root, confirmation_tools):
    async with MCPTools(
        f"npx -y @modelcontextprotocol/server-filesystem {root}",
        requires_confirmation_tools=confirmation_tools,
    ) as filesystem_tools:
        agent = Agent(name="Dynamic Policy Writer", tools=[filesystem_tools])
        await agent.aprint_response("Create notes.txt")

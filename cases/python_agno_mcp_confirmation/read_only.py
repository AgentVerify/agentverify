from agno.agent import Agent
from agno.tools.mcp import MCPTools


async def run_agent(root):
    async with MCPTools(
        f"npx -y @modelcontextprotocol/server-filesystem {root}",
        include_tools=["list_allowed_directories", "list_directory", "read_file"],
    ) as filesystem_tools:
        agent = Agent(name="Reader", tools=[filesystem_tools])
        await agent.aprint_response("Read notes.txt")

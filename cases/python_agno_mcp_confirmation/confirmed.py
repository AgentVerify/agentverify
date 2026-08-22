from agno.agent import Agent
from agno.tools.mcp import MCPTools


async def run_agent(root):
    async with MCPTools(
        f"npx -y @modelcontextprotocol/server-filesystem {root}",
        requires_confirmation_tools=[
            "create_directory",
            "edit_file",
            "move_file",
            "write_file",
        ],
    ) as filesystem_tools:
        agent = Agent(name="Confirmed Writer", tools=[filesystem_tools])
        await agent.aprint_response("Create notes.txt")

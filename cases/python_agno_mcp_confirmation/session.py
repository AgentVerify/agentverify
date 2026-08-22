from agno.agent import Agent
from agno.tools.mcp import MCPTools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_agent(root):
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", root],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            filesystem_tools = MCPTools(session=session)
            await filesystem_tools.initialize()
            agent = Agent(name="Session Writer", tools=[filesystem_tools])
            await agent.aprint_response("Move notes.txt")

from agno.agent import Agent
from agno.tools.mcp import MCPTools


async def build_tools(root):
    return MCPTools(f"npx -y @modelcontextprotocol/server-filesystem {root}")

from local_agents.mcp import MCPServer
from agents.mcp.server import MCPServer as ExactMCPServer


class NearProjectMCPServer(MCPServer):
    async def list_tools(self):
        return []

    async def call_tool(self, tool_name, arguments):
        return tool_name, arguments


class IncompleteProjectMCPServer(ExactMCPServer):
    async def list_tools(self):
        return []

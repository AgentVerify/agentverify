from agents.mcp.server import MCPServer


class ProjectMCPServer(MCPServer):
    async def list_tools(self):
        return []

    async def call_tool(self, tool_name, arguments):
        return tool_name, arguments

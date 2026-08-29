from agents.mcp.server import MCPServer


class ProjectMCPServer(MCPServer):
    def __init__(self, require_approval=None):
        super().__init__(require_approval=require_approval)

    async def connect(self):
        pass

    async def cleanup(self):
        pass

    async def list_tools(self, run_context=None, agent=None):
        return []

    async def call_tool(self, tool_name, arguments, meta=None):
        raise NotImplementedError(tool_name)

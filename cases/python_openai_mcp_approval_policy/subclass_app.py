from agents import Agent


def build_agent() -> Agent:
    from mcp_adapter import ProjectMCPServer

    server = ProjectMCPServer(require_approval=True)
    return Agent(name="Python MCP subclass approval", mcp_servers=[server])

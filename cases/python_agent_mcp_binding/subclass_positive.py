from pydantic_ai import Agent


def build_agent():
    from subclass_adapter import ProjectMCPServer

    project_server = ProjectMCPServer()
    return Agent(name="subclass-agent", mcp_servers=[project_server])

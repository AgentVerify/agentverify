from fastmcp.server import FastMCP
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio


module_stdio_server = MCPServerStdio(command="uvx", args=["mcp-server-git"])
module_fastmcp_server = FastMCP("local tools")


def build_agent():
    return Agent(name="module-stdio", mcp_servers=[module_stdio_server])


if __name__ == "__main__":
    in_process_agent = Agent(
        name="module-fastmcp", mcp_servers=[module_fastmcp_server]
    )

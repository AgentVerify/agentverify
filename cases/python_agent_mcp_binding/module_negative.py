from myfastmcp.server import FastMCP as NearFastMCP
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio


rebound_server = MCPServerStdio(command="uvx", args=["mcp-server-git"])
rebound_server = replacement


def rebound_agent():
    return Agent(name="module-rebound", mcp_servers=[rebound_server])


shadowed_server = MCPServerStdio(command="uvx", args=["mcp-server-git"])


def shadowed_agent(shadowed_server):
    return Agent(name="module-shadowed", mcp_servers=[shadowed_server])


def forward_agent():
    return Agent(name="module-forward", mcp_servers=[forward_server])


forward_server = MCPServerStdio(command="uvx", args=["mcp-server-git"])
near_server = NearFastMCP("not an exact FastMCP package")


try:
    from fastmcp import FastMCP as OptionalFastMCP
except ImportError:
    pass

optional_server = OptionalFastMCP("optional server")


@optional_server.tool()
def optional_tool() -> str:
    return "optional"


optional_agent = Agent(name="optional-import", mcp_servers=[optional_server])

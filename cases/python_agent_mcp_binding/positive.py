from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio as StdioServer


python_server = StdioServer(
    command="deno",
    args=["run", "-A", "jsr:@pydantic/mcp-run-python", "stdio"],
)
git_server = StdioServer(command="uvx", args=["mcp-server-git"])

agent = Agent(
    name="operator",
    mcp_servers=[python_server, git_server],
)

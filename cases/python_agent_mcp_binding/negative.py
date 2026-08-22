from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio


forward_agent = Agent(name="forward", mcp_servers=[forward_server])
forward_server = MCPServerStdio(command="uvx", args=["mcp-server-git"])

rebound_server = MCPServerStdio(command="uvx", args=["mcp-server-git"])
rebound_server = replacement
rebound_agent = Agent(name="rebound", mcp_servers=[rebound_server])

indirect_server = MCPServerStdio(command="uvx", args=["mcp-server-git"])
server_list = [indirect_server]
indirect_agent = Agent(name="indirect", mcp_servers=server_list)

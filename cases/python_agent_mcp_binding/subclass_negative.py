from pydantic_ai import Agent
from subclass_adapter import ProjectMCPServer
from subclass_adapter_negative import IncompleteProjectMCPServer, NearProjectMCPServer


near_server = NearProjectMCPServer()
near_agent = Agent(name="near-subclass", mcp_servers=[near_server])

incomplete_server = IncompleteProjectMCPServer()
incomplete_agent = Agent(name="incomplete-subclass", mcp_servers=[incomplete_server])

rebound_server = ProjectMCPServer()
rebound_server = replacement
rebound_agent = Agent(name="rebound-subclass", mcp_servers=[rebound_server])

forward_agent = Agent(name="forward-subclass", mcp_servers=[forward_server])
forward_server = ProjectMCPServer()

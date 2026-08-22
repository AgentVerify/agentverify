from agents import Agent, HostedMCPTool
from autogen_ext.tools.graphrag import GlobalSearchTool
from google.adk.integrations.langchain import LangchainTool


graph_tool = GlobalSearchTool.from_settings(root_dir=".")
mcp_tool = HostedMCPTool(tool_config={"type": "mcp"})
langchain_tool = LangchainTool(tool=object())

worker = Agent(name="worker", tools=[])
worker_tool = worker.as_tool(tool_name="worker")

root = Agent(
    name="root",
    tools=[graph_tool, mcp_tool, langchain_tool, worker_tool],
)

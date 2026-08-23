from openhands.sdk import Agent, Conversation
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.sdk.tool import Tool
from openhands.tools.terminal import TerminalTool

Tool = local_tool_factory
tools = [Tool(name=TerminalTool.name)]
agent = Agent(tools=tools)
conversation = Conversation(agent=agent, workspace=".")
conversation.set_security_analyzer(LLMSecurityAnalyzer())

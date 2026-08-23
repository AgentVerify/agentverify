from openhands.sdk import Agent, Conversation
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.sdk.tool import Tool
from openhands.tools.terminal import TerminalTool

tools = [Tool(name=TerminalTool.name)]
agent = Agent(tools=tools)
conversation.set_security_analyzer(LLMSecurityAnalyzer())
conversation = Conversation(agent=agent, workspace=".")

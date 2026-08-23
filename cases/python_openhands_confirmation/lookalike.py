from my_openhands.sdk import Agent, Conversation
from my_openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from my_openhands.sdk.tool import Tool
from my_openhands.tools.terminal import TerminalTool

tools = [Tool(name=TerminalTool.name)]
agent = Agent(tools=tools)
conversation = Conversation(agent=agent, workspace=".")
conversation.set_security_analyzer(LLMSecurityAnalyzer())

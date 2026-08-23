from openhands.sdk import Agent, Conversation
from openhands.sdk.security import ConfirmRisky, SecurityRisk
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.sdk.tool import Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

tools = [
    Tool(name=TerminalTool.name),
    Tool(name=FileEditorTool.name),
]
agent = Agent(tools=tools)
conversation = Conversation(agent=agent, workspace=".")
conversation.set_security_analyzer(LLMSecurityAnalyzer())
conversation.set_confirmation_policy(
    ConfirmRisky(threshold=SecurityRisk.MEDIUM, confirm_unknown=False)
)

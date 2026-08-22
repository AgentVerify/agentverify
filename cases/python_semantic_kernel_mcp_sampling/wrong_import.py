from local_agents import ChatCompletionAgent
from local_mcp import MCPStdioPlugin


async def run_agent():
    async with MCPStdioPlugin(
        name="WrongImport",
        command="uv",
        sampling_auto_approve=True,
    ) as plugin:
        agent = ChatCompletionAgent(name="Wrong Import", plugins=[plugin])
        await agent.get_response(messages="Summarize issues")

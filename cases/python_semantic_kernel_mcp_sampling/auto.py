from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.mcp import MCPStdioPlugin


async def run_agent():
    async with MCPStdioPlugin(
        name="ReleaseNotes",
        command="uv",
        sampling_auto_approve=True,
    ) as plugin:
        agent = ChatCompletionAgent(name="Sampler", plugins=[plugin])
        await agent.get_response(messages="Summarize issues")

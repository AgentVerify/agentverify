from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.mcp import MCPStdioPlugin


async def run_agent(other_plugin):
    async with MCPStdioPlugin(
        name="Disconnected",
        command="uv",
        sampling_auto_approve=True,
    ) as plugin:
        print(plugin)
        agent = ChatCompletionAgent(name="Other Agent", plugins=[other_plugin])
        await agent.get_response(messages="Summarize issues")

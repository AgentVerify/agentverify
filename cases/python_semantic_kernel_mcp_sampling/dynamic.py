from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.mcp import MCPStdioPlugin


async def run_agent(auto_approve):
    async with MCPStdioPlugin(
        name="Dynamic",
        command="uv",
        sampling_auto_approve=auto_approve,
    ) as plugin:
        agent = ChatCompletionAgent(name="Dynamic Sampler", plugins=[plugin])
        await agent.get_response(messages="Summarize issues")

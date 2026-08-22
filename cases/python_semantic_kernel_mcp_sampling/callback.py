from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.mcp import MCPStdioPlugin


async def review_sampling(plugin_name, params):
    return await request_human_review(plugin_name, params)


async def run_agent():
    async with MCPStdioPlugin(
        name="Reviewed",
        command="uv",
        sampling_consent_callback=review_sampling,
        sampling_auto_approve=True,
    ) as plugin:
        agent = ChatCompletionAgent(name="Reviewed Sampler", plugins=[plugin])
        await agent.get_response(messages="Summarize issues")

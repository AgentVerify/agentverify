from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.mcp import MCPStdioPlugin


async def run_agent():
    async with MCPStdioPlugin(
        name="ExplicitDeny",
        command="uv",
        sampling_auto_approve=False,
    ) as plugin:
        agent = ChatCompletionAgent(name="Explicit Deny", plugins=[plugin])
        await agent.get_response(messages="Summarize issues")

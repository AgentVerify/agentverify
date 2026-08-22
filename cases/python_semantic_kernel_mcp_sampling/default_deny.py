from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.mcp import MCPStdioPlugin


async def run_agent():
    async with MCPStdioPlugin(name="DefaultDeny", command="uv") as plugin:
        agent = ChatCompletionAgent(name="Default Deny", plugins=[plugin])
        await agent.get_response(messages="Summarize issues")

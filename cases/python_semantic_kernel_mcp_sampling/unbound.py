from semantic_kernel.connectors.mcp import MCPStdioPlugin


async def build_plugin():
    return MCPStdioPlugin(
        name="Unbound",
        command="uv",
        sampling_auto_approve=True,
    )

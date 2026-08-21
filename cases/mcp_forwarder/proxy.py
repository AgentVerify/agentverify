from mcp import ClientSession


async def proxy(session: ClientSession, tool_name: str, arguments: dict):
    return await session.call_tool(tool_name, arguments)


async def fixed_read(session: ClientSession):
    return await session.call_tool("read_file", {"path": "README.md"})


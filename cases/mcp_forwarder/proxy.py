from mcp import ClientSession


async def proxy(session: ClientSession, tool_name: str, arguments: dict):
    return await session.call_tool(tool_name, arguments)


async def fixed_read(session: ClientSession):
    return await session.call_tool("read_file", {"path": "README.md"})


ALLOWED_TOOLS = {"read_file"}


async def guarded_proxy(session: ClientSession, tool_name: str, arguments: dict):
    if tool_name not in ALLOWED_TOOLS:
        raise ValueError("tool is not allowed")
    return await session.call_tool(tool_name, arguments)

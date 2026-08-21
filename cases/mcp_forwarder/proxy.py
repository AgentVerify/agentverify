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


async def late_guard_proxy(session: ClientSession, tool_name: str, arguments: dict):
    result = await session.call_tool(tool_name, arguments)
    if tool_name not in ALLOWED_TOOLS:
        raise ValueError("tool is not allowed")
    return result


class SessionGroup:
    def __init__(self, tools: dict, tool_to_session: dict):
        self.tools = tools
        self._tool_to_session = tool_to_session

    async def registry_proxy(self, name: str, arguments: dict):
        session = self._tool_to_session[name]
        session_tool_name = self.tools[name].name
        return await session.call_tool(session_tool_name, arguments)


async def caller_mapping_proxy(session: ClientSession, name: str, arguments: dict, tools: dict):
    server_tool_name = tools[name].name
    return await session.call_tool(server_tool_name, arguments)


class LateRegistryGroup:
    def __init__(self, tools: dict):
        self.tools = tools

    async def proxy(self, session: ClientSession, name: str, arguments: dict):
        result = await session.call_tool(name, arguments)
        registered_tool = self.tools[name]
        return result, registered_tool


class BoundToolProxy:
    def __init__(self, session: ClientSession, tool):
        self.session = session
        self._tool = tool

    @property
    def tool_name(self):
        return self._tool.name

    async def call(self, arguments: dict):
        return await self.session.call_tool(self.tool_name, arguments)


class MutableToolProxy:
    def __init__(self, session: ClientSession, tool):
        self.session = session
        self._tool = tool

    def replace_tool(self, tool):
        self._tool = tool

    async def call(self, arguments: dict):
        return await self.session.call_tool(self._tool.name, arguments)

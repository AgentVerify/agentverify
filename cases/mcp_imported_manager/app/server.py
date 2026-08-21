from mcp.server import FastMCP

from .managers import FallbackManager, RegistryManager


class RoutedServer:
    def __init__(self):
        self._manager = RegistryManager()

    async def dispatch(self, name: str, arguments: dict):
        return await self._manager.call_tool(name, arguments)


class MutableServer:
    def __init__(self):
        self._manager = RegistryManager()

    def replace_manager(self, manager):
        self._manager = manager

    async def dispatch(self, name: str, arguments: dict):
        return await self._manager.call_tool(name, arguments)


class FallbackServer:
    def __init__(self):
        self._manager = FallbackManager()

    async def dispatch(self, name: str, arguments: dict):
        return await self._manager.call_tool(name, arguments)

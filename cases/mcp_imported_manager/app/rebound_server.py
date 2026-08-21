from mcp.server import FastMCP

from .managers import FallbackManager, RegistryManager

RegistryManager = FallbackManager


class ReboundConstructorServer:
    def __init__(self):
        self._manager = RegistryManager()

    async def dispatch(self, name: str, arguments: dict):
        return await self._manager.call_tool(name, arguments)

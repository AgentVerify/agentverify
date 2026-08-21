class RegistryManager:
    async def call_tool(self, name: str, arguments: dict):
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(name)
        return await tool.run(arguments)


class FallbackManager:
    async def call_tool(self, name: str, arguments: dict):
        tool = self._tools.get(name)
        if tool is None:
            tool = self.default_tool
        return await tool.run(arguments)

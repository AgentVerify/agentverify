class PluginManager:
    def __init__(self, plugins):
        self.plugins = plugins

    async def run_before_tool_callback(self, **kwargs):
        for plugin in self.plugins:
            await plugin.before_tool_callback(**kwargs)

    async def run_after_tool_callback(self, **kwargs):
        for plugin in self.plugins:
            await plugin.after_tool_callback(**kwargs)

    async def run_on_tool_error_callback(self, **kwargs):
        for plugin in self.plugins:
            await plugin.on_tool_error_callback(**kwargs)


CALLBACK_NAMES = (
    "before_tool_callback",
    "after_tool_callback",
    "on_tool_error_callback",
)

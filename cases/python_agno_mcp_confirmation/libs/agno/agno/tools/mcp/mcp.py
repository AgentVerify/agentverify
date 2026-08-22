class MCPTools:
    def __init__(self, include_tools=None, **kwargs):
        requires_confirmation_tools = kwargs.pop("requires_confirmation_tools", None)
        self.include_tools = include_tools
        self.requires_confirmation_tools = requires_confirmation_tools or []

    def build_tools(self, available_tools):
        for tool in available_tools.tools:
            if self.include_tools is None or tool.name in self.include_tools:
                f = Function(
                    requires_confirmation=tool_name in self.requires_confirmation_tools
                )
                self.functions[f.name] = f

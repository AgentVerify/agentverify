from typing import TypeAlias, override

ToolCallArguments: TypeAlias = dict[str, object]


class ToolExecutor:
    @override
    async def execute_tool_call(self, tool_call: ToolCall) -> ToolResult:
        normalized_name = tool_call.name
        tool = self.tools[normalized_name]
        tool_exec_result = await tool.execute(tool_call.arguments)
        return ToolResult(result=tool_exec_result.output)

from near_trae_agent.tools.base import Tool, ToolCallArguments, ToolExecResult


class BashTool(Tool):
    async def execute(self, arguments: ToolCallArguments) -> ToolExecResult:
        command = str(arguments["command"]) if "command" in arguments else None
        return await self._session.run(command)


class TextEditorTool(Tool):
    async def execute(self, arguments: ToolCallArguments) -> ToolExecResult:
        path = str(arguments["path"]) if "path" in arguments else None
        return ToolExecResult(output=path)

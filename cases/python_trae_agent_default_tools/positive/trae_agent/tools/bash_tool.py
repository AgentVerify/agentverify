import asyncio

from trae_agent.tools.base import Tool, ToolCallArguments, ToolError, ToolExecResult, ToolParameter


class _BashSession:
    command: str = "/bin/bash"

    async def start(self):
        self._process = await asyncio.create_subprocess_shell(
            self.command,
            shell=True,
            stdin=asyncio.subprocess.PIPE,
        )

    async def run(self, command: str):
        self._process.stdin.write(
            b"(\n"
            + command.encode()
        )


class BashTool(Tool):
    def get_parameters(self):
        return [
            ToolParameter(
                name="command",
                type="string",
                description="command",
                required=True,
            )
        ]

    async def execute(self, arguments: ToolCallArguments) -> ToolExecResult:
        command = str(arguments["command"]) if "command" in arguments else None
        if command is None:
            return ToolExecResult(error="missing")
        return await self._session.run(command)

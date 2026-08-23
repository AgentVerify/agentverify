from pathlib import Path

from trae_agent.tools.base import Tool, ToolCallArguments, ToolError, ToolExecResult, ToolParameter


class TextEditorTool(Tool):
    def get_parameters(self):
        return [
            ToolParameter(
                name="path",
                type="string",
                description="absolute path",
                required=True,
            )
        ]

    async def execute(self, arguments: ToolCallArguments) -> ToolExecResult:
        command = str(arguments["command"])
        path = str(arguments["path"]) if "path" in arguments else None
        if path is None:
            return ToolExecResult(error="missing")
        _path = Path(path)
        self.validate_path(command, _path)
        if command == "create":
            return self._create_handler(arguments, _path)
        if command == "str_replace":
            return self._str_replace_handler(arguments, _path)
        return self._insert_handler(arguments, _path)

    def validate_path(self, command: str, path: Path):
        if not path.is_absolute():
            raise ToolError("absolute path required")

    def write_file(self, path: Path, file: str):
        _ = path.write_text(file)

    def _create_handler(self, arguments: ToolCallArguments, _path: Path) -> ToolExecResult:
        file_text = str(arguments["file_text"])
        self.write_file(_path, file_text)
        return ToolExecResult()

    def _str_replace_handler(self, arguments: ToolCallArguments, _path: Path) -> ToolExecResult:
        old_str = str(arguments["old_str"])
        new_str = str(arguments["new_str"])
        return self.str_replace(_path, old_str, new_str)

    def _insert_handler(self, arguments: ToolCallArguments, _path: Path) -> ToolExecResult:
        insert_line = int(arguments["insert_line"])
        new_str_to_insert = str(arguments["new_str"])
        return self._insert(_path, insert_line, new_str_to_insert)

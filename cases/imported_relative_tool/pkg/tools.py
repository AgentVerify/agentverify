from agents import function_tool


@function_tool
def run_command(command: str) -> str:
    return command

from agents import function_tool


@function_tool(needs_approval=True)
def run_command(command: str) -> str:
    return f"Approval-only stub for {command}"

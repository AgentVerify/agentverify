import subprocess

from agents import function_tool


@function_tool(needs_approval=True)
def run_command(command: str) -> str:
    return subprocess.run(command, shell=True, text=True, capture_output=True).stdout

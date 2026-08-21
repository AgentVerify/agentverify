import subprocess

from agents import Agent, function_tool


@function_tool
def git_status() -> str:
    """Run a fixed, read-only command without a system shell."""
    return subprocess.run(
        ["git", "status", "--short"], check=True, capture_output=True, text=True
    ).stdout


agent = Agent(name="repository_reader", tools=[git_status])


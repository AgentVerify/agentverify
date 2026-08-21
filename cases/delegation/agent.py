import subprocess

from agents import Agent, function_tool


@function_tool
def run_command(command: str) -> str:
    return subprocess.run(command, shell=True, capture_output=True, text=True).stdout


worker = Agent(name="worker", tools=[run_command])
coordinator = Agent(name="coordinator", handoffs=[worker])


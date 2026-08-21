import subprocess

from agents import Agent, function_tool


@function_tool
def run_command(command: str) -> str:
    return subprocess.run(command, shell=True, text=True, capture_output=True).stdout


operator = Agent(name="operator", tools=[run_command])

import subprocess

from agents import Agent, function_tool


@function_tool(needs_approval=True)
def deploy(command: str) -> str:
    return subprocess.run(command, shell=True, capture_output=True, text=True).stdout


agent = Agent(name="deployer", tools=[deploy])


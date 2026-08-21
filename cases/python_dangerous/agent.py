import subprocess

from agents import Agent, function_tool
from openai import OpenAI


client = OpenAI()


@function_tool
def run_task(command: str) -> str:
    """Intentionally unsafe regression case."""
    return subprocess.run(command, shell=True, capture_output=True, text=True).stdout


agent = Agent(name="operator", model="gpt-5", tools=[run_task])

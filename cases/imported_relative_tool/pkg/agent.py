from agents import Agent

from .tools import run_command

agent = Agent(name="operator", tools=[run_command])

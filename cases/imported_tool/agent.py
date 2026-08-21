from agents import Agent

from tools import run_command


operator = Agent(name="operator", tools=[run_command])

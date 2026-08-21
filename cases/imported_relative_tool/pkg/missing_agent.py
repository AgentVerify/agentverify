from agents import Agent

from .missing import missing_tool

agent = Agent(name="unresolved", tools=[missing_tool])

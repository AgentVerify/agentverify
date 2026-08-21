from crewai import Agent
from pkg import tool

direct = Agent(role="direct", tools=[tool])


def parameter_agent(tool):
    return Agent(role="parameter", tools=[tool])


def rebound_agent():
    tool = object()
    return Agent(role="rebound", tools=[tool])

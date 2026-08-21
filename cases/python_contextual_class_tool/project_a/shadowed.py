from crewai import Agent
from tools.browser import BrowserTools

BrowserTools = object()  # noqa: F811
shadowed = Agent(role="shadowed", tools=[BrowserTools.browse])

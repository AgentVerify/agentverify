# ruff: noqa: F811, I001
from crewai import Agent
from tools.browser import BrowserTools
from missing.browser import BrowserTools

reimported = Agent(role="reimported", tools=[BrowserTools.browse])

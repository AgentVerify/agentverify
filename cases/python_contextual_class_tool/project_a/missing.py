from crewai import Agent
from tools.browser import BrowserTools

missing = Agent(role="missing", tools=[BrowserTools.not_exported])

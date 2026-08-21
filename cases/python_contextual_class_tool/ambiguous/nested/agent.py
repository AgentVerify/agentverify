from crewai import Agent
from tools.browser import BrowserTools

ambiguous = Agent(role="ambiguous", tools=[BrowserTools.browse])

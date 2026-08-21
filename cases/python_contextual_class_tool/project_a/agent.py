from crewai import Agent
from tools.browser import BrowserTools as WebTools

operator = Agent(role="operator", tools=[WebTools.browse])

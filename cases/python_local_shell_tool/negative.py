from agents import Agent
from agents import LocalShellTool as ReboundLocalShellTool
from local_agents import LocalShellTool


near = LocalShellTool(executor=execute)
near_agent = Agent(name="near-shell", tools=[near])

ReboundLocalShellTool = replacement
rebound = ReboundLocalShellTool(executor=execute)
rebound_agent = Agent(name="rebound-shell", tools=[rebound])

from agents import Agent
from agents import CodeInterpreterTool as ReboundCodeInterpreterTool
from local_agents import CodeInterpreterTool


near = CodeInterpreterTool(tool_config=config)
near_agent = Agent(name="near-code", tools=[near])

ReboundCodeInterpreterTool = replacement
rebound = ReboundCodeInterpreterTool(tool_config=config)
rebound_agent = Agent(name="rebound-code", tools=[rebound])

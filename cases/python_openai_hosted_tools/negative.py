from agents import Agent
from agents import FileSearchTool as ReboundFileSearchTool
from agents import ImageGenerationTool as ReboundImageGenerationTool
from agents import WebSearchTool as ReboundWebSearchTool
from local_agents import FileSearchTool, ImageGenerationTool, WebSearchTool


near_web = WebSearchTool()
near_web_agent = Agent(name="near-web", tools=[near_web])
near_files = FileSearchTool(vector_store_ids=[])
near_file_agent = Agent(name="near-files", tools=[near_files])
near_image = ImageGenerationTool(tool_config=config)
near_image_agent = Agent(name="near-image", tools=[near_image])

ReboundWebSearchTool = replacement
ReboundFileSearchTool = replacement
ReboundImageGenerationTool = replacement
rebound_web = ReboundWebSearchTool()
rebound_web_agent = Agent(name="rebound-web", tools=[rebound_web])
rebound_files = ReboundFileSearchTool(vector_store_ids=[])
rebound_file_agent = Agent(name="rebound-files", tools=[rebound_files])
rebound_image = ReboundImageGenerationTool(tool_config=config)
rebound_image_agent = Agent(name="rebound-image", tools=[rebound_image])

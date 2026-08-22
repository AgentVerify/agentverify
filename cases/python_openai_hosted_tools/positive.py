from agents import Agent, FileSearchTool, ImageGenerationTool, WebSearchTool
from agents.tool import WebSearchTool as AliasedWebSearchTool


web = WebSearchTool(external_web_access=False)
web_agent = Agent(name="web", tools=[web])

aliased_web = AliasedWebSearchTool()
aliased_web_agent = Agent(name="aliased-web", tools=[aliased_web])

files = FileSearchTool(vector_store_ids=["vs_1", "vs_2"])
file_agent = Agent(name="files", tools=[files])

dynamic_files = FileSearchTool(vector_store_ids=store_ids)
dynamic_file_agent = Agent(name="dynamic-files", tools=[dynamic_files])

image_agent = Agent(
    name="images",
    tools=[ImageGenerationTool(tool_config=image_config)],
)

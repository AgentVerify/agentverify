from agents import Agent
from external_sdk.tools import sdk_tool
from pkg.tools import imported_writer


operator = Agent(
    name="imported-operator",
    tools=[imported_writer, sdk_tool],
)

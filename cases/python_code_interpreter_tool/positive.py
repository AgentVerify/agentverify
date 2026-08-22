from agents import Agent, CodeInterpreterTool
from agents.tool import CodeInterpreterTool as AliasedCodeInterpreterTool


assigned = CodeInterpreterTool(
    tool_config={"type": "code_interpreter", "container": {"type": "auto"}},
)
assigned_agent = Agent(name="assigned-code", tools=[assigned])

aliased = AliasedCodeInterpreterTool(
    tool_config={"type": "code_interpreter", "container": "container_123"},
)
aliased_agent = Agent(name="aliased-code", tools=[aliased])

inline_agent = Agent(
    name="inline-code",
    tools=[
        CodeInterpreterTool(
            tool_config={"type": "code_interpreter", "container": "auto"},
        )
    ],
)

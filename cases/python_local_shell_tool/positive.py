from agents import Agent, LocalShellTool
from agents.tool import LocalShellTool as AliasedLocalShellTool


def execute(request):
    return str(request)


assigned = LocalShellTool(executor=execute)
assigned_agent = Agent(name="assigned-shell", tools=[assigned])

aliased = AliasedLocalShellTool(executor=execute)
aliased_agent = Agent(name="aliased-shell", tools=[aliased])

inline_agent = Agent(
    name="inline-shell",
    tools=[LocalShellTool(executor=execute)],
)

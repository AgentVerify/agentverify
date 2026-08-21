from crewai import Agent
from trusted.tools import ContextTools, ImportedTools, InlineTools, Toolkit


module_tools = ImportedTools()


def module_callable(value: str) -> str:
    return value


class LocalToolkit(Toolkit):
    pass


def module_bindings():
    return Agent(
        name="module-bindings",
        tools=[module_tools, module_callable],
    )


def local_binding():
    local_tools = ImportedTools()
    return Agent(name="local-binding", tools=[local_tools])


def inline_binding():
    return Agent(
        name="inline-binding",
        tools=[InlineTools(), LocalToolkit()],
    )


async def context_binding():
    async with ContextTools() as context_tools:
        return Agent(name="context-binding", tools=[context_tools])

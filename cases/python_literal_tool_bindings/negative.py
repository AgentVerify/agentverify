from crewai import Agent
from alpha.tools import AmbiguousTools
from beta.tools import AmbiguousTools
from fake_agents import tool_factory
from trusted.tools import ContextTools, ImportedTools, ShadowedTools


def reassigned_binding():
    tools = ImportedTools()
    tools = object()
    return Agent(name="reassigned-binding", tools=[tools])


def cross_branch_binding(enabled: bool):
    if enabled:
        tools = ImportedTools()
    return Agent(name="cross-branch-binding", tools=[tools])


def parameter_binding(tools):
    return Agent(name="parameter-binding", tools=[tools])


def unproven_factory():
    tools = tool_factory()
    return Agent(name="unproven-factory", tools=[tools])


def unproven_builtin():
    tools = object()
    return Agent(name="unproven-builtin", tools=[tools])


def ambiguous_constructor():
    tools = AmbiguousTools()
    return Agent(name="ambiguous-constructor", tools=[tools])


def shadowed_constructor():
    ShadowedTools = object
    tools = ShadowedTools()
    return Agent(name="shadowed-constructor", tools=[tools])


async def reassigned_context():
    async with ContextTools() as tools:
        tools = object()
        return Agent(name="reassigned-context", tools=[tools])


async def nested_context(enabled: bool):
    async with ContextTools() as tools:
        if enabled:
            return Agent(name="nested-context", tools=[tools])
    return None


def rebound_callable(value: str) -> str:
    return value


rebound_callable = object()


def callable_rebound():
    return Agent(name="callable-rebound", tools=[rebound_callable])

import subprocess

import agents as agent_sdk
from agents import Agent, function_tool as make_function_tool
from fake_agents import function_tool as fake_function_tool


def approved_wrapper():
    def run_command(command: str) -> None:
        subprocess.run(command, shell=True)

    wrapped = make_function_tool(run_command, needs_approval=True)
    return Agent("approved", tools=[wrapped])


def module_wrapper():
    def lookup(value: str) -> str:
        return value

    wrapped = agent_sdk.function_tool(lookup)
    return Agent("module", tools=[wrapped])


def wrong_import():
    def action(value: str) -> str:
        return value

    wrapped = fake_function_tool(action)
    return Agent("wrong-import", tools=[wrapped])


def shadowed_factory(make_function_tool):
    def action(value: str) -> str:
        return value

    wrapped = make_function_tool(action)
    return Agent("shadowed", tools=[wrapped])


def reassigned_wrapper():
    def action(value: str) -> str:
        return value

    wrapped = make_function_tool(action)
    wrapped = object()
    return Agent("reassigned", tools=[wrapped])


def reassigned_function():
    def action(value: str) -> str:
        return value

    action = object()
    wrapped = make_function_tool(action)
    return Agent("reassigned-function", tools=[wrapped])


def cross_branch(enabled: bool):
    if enabled:
        def action(value: str) -> str:
            return value

        wrapped = make_function_tool(action)
    return Agent("cross-branch", tools=[wrapped])


def lambda_wrapper():
    wrapped = make_function_tool(lambda value: value)
    return Agent("lambda", tools=[wrapped])


def multiple_wrappers():
    def action(value: str) -> str:
        return value

    first = make_function_tool(action)
    second = make_function_tool(action)
    return Agent("multiple", tools=[first, second])

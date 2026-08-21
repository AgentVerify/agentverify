import subprocess

from pydantic_ai import Agent


def direct_callable():
    def run_command(command: str) -> None:
        subprocess.run(command, shell=True)
    return Agent("test", tools=[run_command])


def same_branch(enabled: bool):
    if enabled:
        def branch_tool(value: str) -> str:
            return value
        return Agent("test", tools=[branch_tool])
    return Agent("test")


def reassigned_callable():
    def run_command(command: str) -> None:
        subprocess.run(command, shell=True)
    run_command = object()
    return Agent("test", tools=[run_command])


def cross_branch(enabled: bool):
    if enabled:
        def run_command(command: str) -> None:
            subprocess.run(command, shell=True)
    return Agent("test", tools=[run_command])


def parameter_callable(run_command):
    return Agent("test", tools=[run_command])


def forward_callable():
    agent = Agent("test", tools=[later_tool])
    def later_tool(value: str) -> str:
        return value
    return agent


def unique_tool(value: str) -> str:
    return value


module_agent = Agent("test", tools=[unique_tool])


def parameter_shadows_unique(unique_tool):
    return Agent("test", tools=[unique_tool])

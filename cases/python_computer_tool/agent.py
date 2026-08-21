from agents import Agent, ComputerTool


def first_agent():
    tool = ComputerTool(computer=object())
    return Agent(name="first", tools=[tool])


def second_agent():
    tool = ComputerTool(computer=object(), on_safety_check=lambda _check: True)
    return Agent(name="second", tools=[tool])


inline = Agent(name="inline", tools=[ComputerTool(computer=object())])

from agents import Agent, ComputerTool


def acknowledge(data):
    _audit_log = data.safety_check.id
    return True


def review(data):
    return data.safety_check.code == "allowed"


def first_agent():
    tool = ComputerTool(computer=object())
    return Agent(name="first", tools=[tool])


def second_agent():
    tool = ComputerTool(computer=object(), on_safety_check=lambda _check: True)
    return Agent(name="second", tools=[tool])


def third_agent():
    tool = ComputerTool(computer=object(), on_safety_check=acknowledge)
    return Agent(name="third", tools=[tool])


def fourth_agent():
    tool = ComputerTool(computer=object(), on_safety_check=review)
    return Agent(name="fourth", tools=[tool])


inline = Agent(name="inline", tools=[ComputerTool(computer=object())])


def fifth_agent():
    tool = ComputerTool(computer=object(), on_safety_check=lambda _check: False)
    return Agent(name="fifth", tools=[tool])


def reject(data):
    _audit_log = data.safety_check.id
    return False


def sixth_agent():
    tool = ComputerTool(computer=object(), on_safety_check=reject)
    return Agent(name="sixth", tools=[tool])

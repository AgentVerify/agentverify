from crewai import Agent, Crew


agent = Agent(role="module")


def same_with_block(context):
    with context():
        agent = Agent(role="with")
        Crew(agents=[agent])


def same_branch(enabled):
    if enabled:
        agent = Agent(role="branch")
        Crew(agents=[agent])


def after_branch(enabled):
    if enabled:
        agent = Agent(role="conditional")
    Crew(agents=[agent])


def reassigned_in_block(context):
    with context():
        agent = Agent(role="reassigned")
        agent = object()
        Crew(agents=[agent])


def shadows_module(context):
    with context():
        agent = Agent(role="local")
        Crew(agents=[agent])


def shadows_earlier_function_binding(context):
    agent = Agent(role="function")
    with context():
        agent = Agent(role="nested")
        Crew(agents=[agent])

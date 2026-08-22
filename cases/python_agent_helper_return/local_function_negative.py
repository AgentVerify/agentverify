from crewai import Agent, Crew


def conditional_factory():
    def make_worker(enabled):
        if enabled:
            return Agent(role="first", goal="g", backstory="b")
        return Agent(role="second", goal="g", backstory="b")

    worker = make_worker(True)
    return Crew(agents=[worker], tasks=[])


def indirect_factory():
    def make_worker():
        worker = Agent(role="indirect", goal="g", backstory="b")
        return worker

    worker = make_worker()
    return Crew(agents=[worker], tasks=[])


def rebound_factory(replacement):
    def make_worker():
        return Agent(role="rebound", goal="g", backstory="b")

    make_worker = replacement
    worker = make_worker()
    return Crew(agents=[worker], tasks=[])


def forward_factory():
    worker = make_worker()

    def make_worker():
        return Agent(role="forward", goal="g", backstory="b")

    return Crew(agents=[worker], tasks=[])


def constructor_shadowed(Agent):
    def make_worker():
        return Agent(role="shadowed", goal="g", backstory="b")

    worker = make_worker()
    return Crew(agents=[worker], tasks=[])


def result_rebound():
    def make_worker():
        return Agent(role="result", goal="g", backstory="b")

    worker = make_worker()
    worker = object()
    return Crew(agents=[worker], tasks=[])

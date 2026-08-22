from crewai import Agent, Crew


def positive_factory_calls():
    def make_worker(label):
        return Agent(role="worker", goal=label, backstory="b")

    first = make_worker("first")
    second = make_worker("second")
    return Crew(agents=[second, first], tasks=[])

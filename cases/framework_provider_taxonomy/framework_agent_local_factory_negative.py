from crewai import Crew
from agentscope.agent import ReActAgent


def conditional_factory(enabled):
    def make_worker():
        if enabled:
            return ReActAgent(name="factory-conditional")
        return ReActAgent(name="factory-conditional-fallback")

    worker = make_worker()
    return Crew(agents=[worker], tasks=[])


def rebound_factory(replacement):
    def make_worker():
        return ReActAgent(name="factory-rebound")

    make_worker = replacement
    worker = make_worker()
    return Crew(agents=[worker], tasks=[])


def forward_factory():
    worker = make_late()

    def make_late():
        return ReActAgent(name="factory-forward")

    return Crew(agents=[worker], tasks=[])

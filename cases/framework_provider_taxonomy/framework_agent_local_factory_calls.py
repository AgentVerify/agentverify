from crewai import Crew
from agents import Agent as OpenAIAgent
from agentscope.agent import ReActAgent
import google.adk.agents as adk_agents


def positive_crew_flow():
    def make_react():
        return ReActAgent(name="factory-react")

    def make_openai():
        return OpenAIAgent(name="factory-openai")

    def make_google():
        return adk_agents.Agent(name="factory-google-adk")

    react = make_react()
    worker = make_openai()
    google = make_google()
    return Crew(agents=[react, worker, google], tasks=[])

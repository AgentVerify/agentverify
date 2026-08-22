from agents import Agent
from external_sdk.alpha import duplicated
from external_sdk.beta import duplicated
from external_sdk.tools import class_shadow
from external_sdk.tools import local_shadow
from external_sdk.tools import parameter_tool
from external_sdk.tools import rebound_tool


rebound_tool = object()


def parameter_shadow(parameter_tool):
    return Agent(name="parameter-shadow", tools=[parameter_tool])


def local_assignment_shadow():
    local_shadow = object()
    return Agent(name="local-shadow", tools=[local_shadow])


class ShadowedContainer:
    class_shadow = object()
    agent = Agent(name="class-shadow", tools=[class_shadow])


duplicate_agent = Agent(name="duplicate-import", tools=[duplicated])
forward_agent = Agent(name="forward-import", tools=[forward_tool])


from external_sdk.tools import forward_tool

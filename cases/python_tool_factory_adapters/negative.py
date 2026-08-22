from agents import Agent, HostedMCPTool as AmbiguousTool
from autogen_ext.tools.graphrag import GlobalSearchTool
from external.adapters import Adapter
from unrelated import HostedMCPTool as AmbiguousTool


unknown_factory = GlobalSearchTool.build()
arbitrary_adapter = Adapter()
ambiguous_adapter = AmbiguousTool(tool_config={})

unknown_agent = Agent(name="unknown-factory", tools=[unknown_factory])
arbitrary_agent = Agent(name="arbitrary-adapter", tools=[arbitrary_adapter])
ambiguous_agent = Agent(name="ambiguous-adapter", tools=[ambiguous_adapter])


def parameter_receiver(worker):
    worker_tool = worker.as_tool()
    return Agent(name="parameter-receiver", tools=[worker_tool])


def nonagent_receiver():
    worker = object()
    worker_tool = worker.as_tool()
    return Agent(name="nonagent-receiver", tools=[worker_tool])


def reassigned_receiver():
    worker = Agent(name="first", tools=[])
    worker = Agent(name="second", tools=[])
    worker_tool = worker.as_tool()
    return Agent(name="reassigned-receiver", tools=[worker_tool])


def reassigned_adapter():
    worker = Agent(name="adapter-worker", tools=[])
    worker_tool = worker.as_tool()
    worker_tool = object()
    return Agent(name="reassigned-adapter", tools=[worker_tool])


def forward_receiver():
    worker_tool = worker.as_tool()
    worker = Agent(name="late-worker", tools=[])
    return Agent(name="forward-receiver", tools=[worker_tool])

import agentscope.agent as agentscope_agents
import google.adk.agents as adk_agents
import qwen_agent.agents as qwen_agents
import fake_agentscope.agent as fake_agents


agentscope_agents = object()
adk_agents.Agent = lambda **kwargs: {"shadowed": kwargs}
qwen_agents.Assistant = lambda **kwargs: {"shadowed": kwargs}

react = agentscope_agents.ReActAgent(name="shadowed-module-react")
google = adk_agents.Agent(name="shadowed-module-google")
qwen = qwen_agents.Assistant(name="shadowed-module-qwen")
near = fake_agents.ReActAgent(name="near-package-react")

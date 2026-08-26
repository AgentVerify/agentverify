from agentscope.agent import ReActAgent
from camel.agents import ChatAgent


ReActAgent = lambda **kwargs: {"decoy": kwargs}
ChatAgent = lambda **kwargs: {"decoy": kwargs}

react = ReActAgent(name="shadowed-react")
camel = ChatAgent(name="shadowed-camel")

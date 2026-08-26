from agents import *
from agentscope.agent import *
from google.adk.agents import *
from qwen_agent.agents import *


ReActAgent = lambda **kwargs: {"shadowed": kwargs}
Assistant = lambda **kwargs: {"shadowed": kwargs}

ambiguous_agent = Agent(name="ambiguous-star-agent")
shadowed_react = ReActAgent(name="shadowed-star-react")
shadowed_qwen = Assistant(name="shadowed-star-qwen")

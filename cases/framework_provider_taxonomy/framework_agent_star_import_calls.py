from agentscope.agent import *
from lagent.agents import *
from metagpt.roles import *
from qwen_agent.agents import *
from semantic_kernel.agents import *


react = ReActAgent(name="star-react")
semantic = ChatCompletionAgent(name="star-semantic-kernel")
qwen = Assistant(name="star-qwen")
lagent = AgentForInternLM(name="star-lagent")
metagpt = Role(name="star-metagpt")

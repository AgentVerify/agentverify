from agentscope.agent import *
from camel.agents import *
from lagent.agents import *
from marvin.agents import *
from metagpt.roles import *
from qwen_agent.agents import *
from semantic_kernel.agents import *


react = ReActAgent(name="star-react")
semantic = ChatCompletionAgent(name="star-semantic-kernel")
camel = ChatAgent(name="star-camel")
marvin = Agent(name="star-marvin")
qwen = Assistant(name="star-qwen")
lagent = AgentForInternLM(name="star-lagent")
metagpt = Role(name="star-metagpt")

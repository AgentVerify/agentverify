from agentscope.agent import ReActAgent
from camel.agents import ChatAgent as CamelChatAgent
from marvin.agents import Agent as MarvinAgent


react = ReActAgent(name="react-facade")
camel = CamelChatAgent(name="camel-facade")
marvin = MarvinAgent(name="marvin-facade")

from agents import Agent as OpenAIAgent


openai = OpenAIAgent(name="openai-facade")

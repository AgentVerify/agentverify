from agentscope.agent import ReActAgent
from camel.agents import ChatAgent as CamelChatAgent
from marvin.agents import Agent as MarvinAgent


react = ReActAgent(name="react-facade")
camel = CamelChatAgent(name="camel-facade")
marvin = MarvinAgent(name="marvin-facade")

from agents import Agent as OpenAIAgent


openai = OpenAIAgent(name="openai-facade")

from google.adk.agents import Agent as GoogleADKAgent


google = GoogleADKAgent(name="google-adk-facade")

from semantic_kernel.agents import ChatCompletionAgent as SemanticKernelAgent


semantic = SemanticKernelAgent(name="semantic-kernel-facade")

from qwen_agent.agents import Assistant as QwenAssistant
from lagent.agents import AgentForInternLM as LagentAgent
from metagpt.roles import Role as MetaGPTRole


qwen = QwenAssistant(name="qwen-facade")
lagent = LagentAgent(name="lagent-facade")
metagpt = MetaGPTRole(name="metagpt-facade")

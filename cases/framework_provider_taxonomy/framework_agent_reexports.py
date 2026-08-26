from agentscope.agent import ReActAgent as ProjectReActAgent
from agents import Agent as ProjectOpenAIAgent
from camel.agents import ChatAgent as ProjectChatAgent
from google.adk.agents import Agent as ProjectGoogleADKAgent
from lagent.agents import AgentForInternLM as HiddenLagentAgent
from semantic_kernel.agents import ChatCompletionAgent as ProjectSemanticKernelAgent
from qwen_agent.agents import Assistant as ProjectQwenAssistant
from lagent.agents import AgentForInternLM as ProjectLagentAgent
from metagpt.roles import Role as ProjectMetaGPTRole


__all__ = ["ProjectReActAgent", "ProjectChatAgent"]

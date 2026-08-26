from framework_agent_reexports import *
from marvin.agents import Agent as ProjectMarvinAgent
from agents import Agent as ProjectStarOpenAIAgent
from google.adk.agents import Agent as ProjectStarGoogleADKAgent
from semantic_kernel.agents import ChatCompletionAgent as ProjectStarSemanticKernelAgent
from qwen_agent.agents import Assistant as ProjectStarQwenAssistant
from lagent.agents import AgentForInternLM as ProjectStarLagentAgent
from metagpt.roles import Role as ProjectStarMetaGPTRole


__all__ = [
    "ProjectReActAgent",
    "ProjectMarvinAgent",
    "ProjectStarOpenAIAgent",
    "ProjectStarGoogleADKAgent",
    "ProjectStarSemanticKernelAgent",
    "ProjectStarQwenAssistant",
    "ProjectStarLagentAgent",
    "ProjectStarMetaGPTRole",
]

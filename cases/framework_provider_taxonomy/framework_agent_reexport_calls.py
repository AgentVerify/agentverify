from framework_agent_reexports import ProjectChatAgent
from framework_agent_reexports import ProjectReActAgent as ImportedReActAgent
from framework_agent_star_reexports import *


react = ImportedReActAgent(name="reexport-react")
camel = ProjectChatAgent(name="reexport-camel")
marvin = ProjectMarvinAgent(name="star-marvin")
hidden = HiddenLagentAgent(name="hidden-lagent")

from framework_agent_reexports import ProjectOpenAIAgent


openai = ProjectOpenAIAgent(name="reexport-openai")
openai_star = ProjectStarOpenAIAgent(name="star-openai")

from framework_agent_reexports import ProjectGoogleADKAgent


google = ProjectGoogleADKAgent(name="reexport-google-adk")
google_star = ProjectStarGoogleADKAgent(name="star-google-adk")

from framework_agent_reexports import ProjectSemanticKernelAgent


semantic = ProjectSemanticKernelAgent(name="reexport-semantic-kernel")
semantic_star = ProjectStarSemanticKernelAgent(name="star-semantic-kernel")

from framework_agent_reexports import ProjectQwenAssistant
from framework_agent_reexports import ProjectLagentAgent
from framework_agent_reexports import ProjectMetaGPTRole


qwen = ProjectQwenAssistant(name="reexport-qwen")
lagent = ProjectLagentAgent(name="reexport-lagent")
metagpt = ProjectMetaGPTRole(name="reexport-metagpt")
qwen_star = ProjectStarQwenAssistant(name="star-qwen")
lagent_star = ProjectStarLagentAgent(name="star-lagent")
metagpt_star = ProjectStarMetaGPTRole(name="star-metagpt")

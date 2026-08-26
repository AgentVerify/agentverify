from framework_agent_reexports import ProjectChatAgent
from framework_agent_reexports import ProjectReActAgent as ImportedReActAgent
from framework_agent_star_reexports import *


react = ImportedReActAgent(name="reexport-react")
camel = ProjectChatAgent(name="reexport-camel")
marvin = ProjectMarvinAgent(name="star-marvin")
hidden = HiddenLagentAgent(name="hidden-lagent")

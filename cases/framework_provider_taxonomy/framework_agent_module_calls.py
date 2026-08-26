import agents as openai_agents
import agentscope.agent as agentscope_agents
import camel.agents as camel_agents
import google.adk.agents as adk_agents
import lagent.agents
import marvin.agents as marvin_agents
import metagpt.roles as metagpt_roles
import qwen_agent.agents
import semantic_kernel.agents as sk_agents


react = agentscope_agents.ReActAgent(name="module-react")
openai = openai_agents.Agent(name="module-openai")
google = adk_agents.Agent(name="module-google-adk")
semantic = sk_agents.ChatCompletionAgent(name="module-semantic-kernel")
camel = camel_agents.ChatAgent(name="module-camel")
marvin = marvin_agents.Agent(name="module-marvin")
qwen = qwen_agent.agents.Assistant(name="module-qwen")
lagent_agent = lagent.agents.AgentForInternLM(name="module-lagent")
metagpt = metagpt_roles.Role(name="module-metagpt")

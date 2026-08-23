from trae_agent.agent.base_agent import BaseAgent
from trae_agent.tools import tools_registry


class TraeAgent(BaseAgent):
    def __init__(self, trae_agent_config, docker_config: dict | None = None, docker_keep=True):
        super().__init__(
            agent_config=trae_agent_config, docker_config=docker_config, docker_keep=docker_keep
        )

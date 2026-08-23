from abc import ABC

from trae_agent.tools import tools_registry
from trae_agent.tools.base import Tool, ToolCall, ToolExecutor, ToolResult
from trae_agent.tools.docker_tool_executor import DockerToolExecutor


class BaseAgent(ABC):
    def __init__(
        self, agent_config, docker_config: dict | None = None
    ):
        self._model_config = agent_config.model
        self._tools: list[Tool] = [
            tools_registry[tool_name](model_provider=self._model_config.model_provider.provider)
            for tool_name in agent_config.tools
        ]
        original_tool_executor = ToolExecutor(self._tools)
        if docker_config:
            self._tool_caller = DockerToolExecutor(
                original_executor=original_tool_executor,
                docker_manager=docker_config["manager"],
                docker_tools=["bash", "str_replace_based_edit_tool", "json_edit_tool"],
            )
        else:
            self._tool_caller = original_tool_executor

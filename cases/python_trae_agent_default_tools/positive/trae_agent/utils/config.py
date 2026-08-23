from dataclasses import dataclass, field


@dataclass
class AgentConfig:
    tools: list[str]


@dataclass
class TraeAgentConfig(AgentConfig):
    tools: list[str] = field(
        default_factory=lambda: [
            "bash",
            "str_replace_based_edit_tool",
            "sequentialthinking",
            "task_done",
        ]
    )

from typing import Literal

from agents import Agent, HostedMCPTool
from unrelated import HostedMCPTool as FakeHostedMCPTool


def prompt_approval(request):
    return {"approve": request.data.name != "delete_page"}


dynamic_policy = {"always": {"tool_names": ["unknown"]}}


def build_agent() -> Agent:
    require_approval: Literal["always"] = "always"
    agent = Agent(
        name="Python hosted MCP approval agent",
        tools=[
            HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "trusted",
                    "server_url": "https://mcp.example.com/mcp",
                    "require_approval": "never",
                }
            ),
            HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "approval_callback",
                    "server_url": "https://mcp.example.com/mcp",
                    "require_approval": require_approval,
                },
                on_approval_request=prompt_approval,
            ),
            HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "selective",
                    "server_url": "https://mcp.example.com/mcp",
                    "require_approval": {
                        "never": {"tool_names": ["read_page"], "read_only": True},
                        "always": {"tool_names": ["write_page"]},
                    },
                }
            ),
            HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "dynamic",
                    "server_url": "https://mcp.example.com/mcp",
                    "require_approval": dynamic_policy,
                }
            ),
            FakeHostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "fake",
                    "require_approval": "always",
                }
            ),
        ],
    )
    return agent

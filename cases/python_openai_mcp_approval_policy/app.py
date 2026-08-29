from typing import Literal

from agents import Agent
from agents.mcp import MCPServerStdio
from local_mcp import MCPServerStdio as FakeMCPServerStdio
from policies import IMPORTED_ALWAYS, IMPORTED_SELECTIVE, MUTATED_POLICY


def load_policy():
    return {"write_file": "always"}


def build_agent() -> Agent:
    require_approval: Literal["always"] = "always"
    selective_policy = {
        "never": {"tool_names": ["read_file"], "read_only": True},
        "always": {"tool_names": ["write_file"]},
    }
    dynamic_policy = load_policy()

    no_approval = MCPServerStdio(
        params={"command": "python", "args": ["mcp_server.py"]},
        require_approval="never",
    )
    literal_approval = MCPServerStdio(
        params={"command": "python", "args": ["mcp_server.py"]},
        require_approval=require_approval,
    )
    selective_approval = MCPServerStdio(
        params={"command": "python", "args": ["mcp_server.py"]},
        require_approval=selective_policy,
    )
    dynamic_approval = MCPServerStdio(
        params={"command": "python", "args": ["mcp_server.py"]},
        require_approval=dynamic_policy,
    )
    imported_literal_approval = MCPServerStdio(
        params={"command": "python", "args": ["mcp_server.py"]},
        require_approval=IMPORTED_ALWAYS,
    )
    imported_selective_approval = MCPServerStdio(
        params={"command": "python", "args": ["mcp_server.py"]},
        require_approval=IMPORTED_SELECTIVE,
    )
    imported_mutated_approval = MCPServerStdio(
        params={"command": "python", "args": ["mcp_server.py"]},
        require_approval=MUTATED_POLICY,
    )
    fake_approval = FakeMCPServerStdio(
        params={"command": "python", "args": ["mcp_server.py"]},
        require_approval="always",
    )
    return Agent(
        name="Python MCP approval policy agent",
        mcp_servers=[
            no_approval,
            literal_approval,
            selective_approval,
            dynamic_approval,
            imported_literal_approval,
            imported_selective_approval,
            imported_mutated_approval,
            fake_approval,
        ],
    )

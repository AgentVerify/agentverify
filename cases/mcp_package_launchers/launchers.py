from agents.mcp import MCPServer as Server
from agno.tools.mcp import MCPTools
from marvin.mcp import MCPServerStdio
from mcp import StdioServerParameters
from ordinary import MCPServer as FakeServer

workspace = "/workspace"
extra_args = ["--headless"]
dynamic_package = "mcp-server-fetch"

filesystem = Server(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", workspace],
)
scanner = MCPTools("npx -y @x402scan/mcp@latest")
git = MCPServerStdio(
    command="uvx",
    args=["--with", "mcp==1.29.0", "mcp-server-git"],
)

pinned_python = StdioServerParameters(
    command="uvx",
    args=["mcp-server-fetch==2026.7.10"],
)
pinned_npm = Server(command="npx", args=["-y", "repomix@1.4.2", "--mcp"])
cached_only = Server(
    command="npx",
    args=["--no-install", "@scope/local-server"],
)
prompted = Server(command="npx", args=["unreviewed-server"])
unknown = Server(command="uvx", args=[dynamic_package])
fake = FakeServer(command="npx", args=["-y", "not-an-mcp-constructor"])

config = {
    "mcpServers": {
        "time": {"command": "uvx", "args": ["mcp-server-time"]},
        "playwright": {
            "command": "npx",
            "args": ["-y", "@playwright/mcp"] + extra_args,
        },
        "pinned": {
            "command": "npx",
            "args": ["-y", "@scope/server@2.3.4"],
        },
        "dynamic": {"command": "uvx", "args": [dynamic_package]},
    }
}

ordinary_config = {
    "servers": {
        "not-mcp": {"command": "npx", "args": ["-y", "ordinary-package"]}
    }
}

from_pinned = Server(
    command="uvx",
    args=["--from", "alternate-mcp-server==1.0.0rc1", "alternate-server"],
)


def shadowed_constructor(Server):
    return Server(command="npx", args=["-y", "shadowed-package"])


def restored_module_constructor():
    return Server(command="npx", args=["-y", "restored-server@3.0.0"])

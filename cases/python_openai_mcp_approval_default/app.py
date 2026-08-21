from agents.mcp import MCPServerStdio
from agents.sandbox import SandboxAgent


async def main() -> None:
    async with MCPServerStdio(
        name="Reference Policy Server",
        params={"command": "python", "args": ["server.py"]},
    ) as server:
        agent = SandboxAgent(
            name="Renewal Review Assistant",
            mcp_servers=[server],
        )
        print(agent)

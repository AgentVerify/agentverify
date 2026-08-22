from pathlib import Path

from fastmcp import FastMCP
from pydantic_ai import Agent


server = FastMCP("filesystem tools")


@server.tool()
def write_file(destination: str) -> str:
    Path(destination).write_text("updated")
    return destination


if __name__ == "__main__":
    agent = Agent(name="filesystem-agent", mcp_servers=[server])

from agents import Agent
from agents.mcp import MCPServerSse, MCPServerStreamableHttp
from local_mcp import MCPServerSse as FakeMCPServerSse


def build_agent() -> Agent:
    sse_server = MCPServerSse(
        params={"url": "https://user:pass@example.com/sse?token=secret"},
        require_approval="always",
    )
    http_server = MCPServerStreamableHttp(
        params={"url": "https://api.example.com/mcp"},
        require_approval={"read": "never", "write": "always"},
    )
    fake_server = FakeMCPServerSse(
        params={"url": "https://fake.example.com/sse"},
        require_approval="always",
    )
    return Agent(
        name="Python remote MCP approval policy agent",
        mcp_servers=[sse_server, http_server, fake_server],
    )

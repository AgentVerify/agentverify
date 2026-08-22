from fastmcp import FastMCP


server = FastMCP("rebound server")
server = replacement


@server.tool()
def unrelated_tool() -> str:
    return "not registered on the proven server"

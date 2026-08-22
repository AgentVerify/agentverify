from pydantic_ai.mcp import MCPToolset

MCPToolset = local_toolset
toolset = MCPToolset("https://example.com/mcp", sampling_model=trusted_model)

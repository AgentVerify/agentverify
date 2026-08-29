IMPORTED_ALWAYS = "always"

IMPORTED_SELECTIVE = {
    "read_hosted": "never",
    "write_hosted": "always",
}

MUTATED_POLICY = "always"
MUTATED_POLICY = "never"

IMPORTED_TOOL_CONFIG = {
    "type": "mcp",
    "server_label": "imported_tool_config",
    "server_url": "https://mcp.example.com/mcp",
    "require_approval": {
        "never": {"tool_names": ["read_config"], "read_only": True},
        "always": {"tool_names": ["write_config"]},
    },
}

ALIASED_TOOL_CONFIG = {
    "type": "mcp",
    "server_label": "aliased_tool_config",
    "server_url": "https://mcp.example.com/mcp",
    "require_approval": "always",
}

MUTATED_TOOL_CONFIG = {
    "type": "mcp",
    "server_label": "mutated_tool_config",
    "server_url": "https://mcp.example.com/mcp",
    "require_approval": "always",
}
MUTATED_TOOL_CONFIG["require_approval"] = "never"

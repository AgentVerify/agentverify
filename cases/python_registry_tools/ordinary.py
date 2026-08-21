from local_registry import register_tool


@register_tool("ordinary")
def ordinary_function(code: str):
    return code

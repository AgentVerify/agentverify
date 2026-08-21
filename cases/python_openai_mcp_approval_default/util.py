def to_function_tool(tool, server, agent):
    needs_approval = server._get_needs_approval_for_tool(tool, agent)
    function_tool = _build_wrapped_function_tool(
        name=tool.name,
        needs_approval=needs_approval,
    )
    return function_tool

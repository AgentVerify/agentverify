async def execute_tool(invocation_context, tool, args, tool_context):
    await invocation_context.plugin_manager.run_before_tool_callback(
        tool=tool, tool_args=args, tool_context=tool_context
    )
    try:
        result = await __call_tool_async(tool, args=args, tool_context=tool_context)
    except Exception as error:
        await invocation_context.plugin_manager.run_on_tool_error_callback(
            tool=tool, tool_args=args, tool_context=tool_context, error=error
        )
        raise
    await invocation_context.plugin_manager.run_after_tool_callback(
        tool=tool, tool_args=args, tool_context=tool_context, result=result
    )
    return result

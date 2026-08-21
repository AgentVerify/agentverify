class ToolResult:
    status = "ok"


async def run_agent_tool_loop(tool_calls, tool_by_name, on_action_round=None):
    round_actions = []
    for _tool_call_id, tool_name, args in tool_calls:
        spec = tool_by_name.get(tool_name)
        result = await spec.handler(args)
        if spec is not None and (spec.billable or spec.recordable):
            round_actions.append((tool_name, args, result.status == "ok"))
    if round_actions and on_action_round is not None:
        try:
            await on_action_round(round_actions)
        except Exception:
            LOG.warning("taskv3 on_action_round callback failed", turn=0, exc_info=True)

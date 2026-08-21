from agents import Agent, ApplyPatchTool, CustomTool, ShellTool


def conditional_approval(_context, _action) -> bool:
    return True


agent = Agent(
    name="operator",
    tools=[
        ShellTool(executor=object(), needs_approval=True),
        ApplyPatchTool(editor=object(), needs_approval=False),
        CustomTool(
            "custom", "Run an external action", object(), needs_approval=conditional_approval
        ),
        ShellTool(object(), needs_approval=True, on_approval=conditional_approval),
    ],
)

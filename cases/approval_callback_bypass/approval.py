import os

from agents import Agent, ShellTool


SHELL_AUTO_APPROVE = os.environ.get("SHELL_AUTO_APPROVE") == "1"
UNUSED_AUTO_APPROVE = os.environ.get("UNUSED_AUTO_APPROVE") == "1"


async def prompt_shell_approval() -> bool:
    if SHELL_AUTO_APPROVE:
        return True
    return False


async def approval_wrapper(_context, _item) -> bool:
    return await prompt_shell_approval()


async def unused_prompt() -> bool:
    if UNUSED_AUTO_APPROVE:
        return True
    return False


async def safe_callback(_context, _item) -> bool:
    return False


operator = Agent(
    name="operator",
    tools=[
        ShellTool(
            executor=object(),
            needs_approval=True,
            on_approval=approval_wrapper,
        ),
        ShellTool(
            executor=object(),
            needs_approval=True,
            on_approval=safe_callback,
        ),
        ShellTool(
            environment={"type": "container_auto"},
            needs_approval=True,
            on_approval=approval_wrapper,
        ),
    ],
)

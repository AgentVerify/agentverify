from metagpt.tools.tool_registry import register_tool
from playwright.async_api import Page


def register_tool(*args, **kwargs):
    return lambda value: value


@register_tool()
def rebound_function(page: Page, code: str):
    return page.evaluate(code)

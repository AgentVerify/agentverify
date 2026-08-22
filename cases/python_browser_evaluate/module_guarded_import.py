import sys

from pydantic_ai import Agent

try:
    from playwright.async_api import Page
except ImportError:
    print("Playwright is required")
    sys.exit(1)


agent = Agent("openai:gpt-5")
guarded_page: Page | None = None


@agent.tool
async def guarded_module_page_evaluate(script: str):
    if guarded_page is None:
        return None
    return await guarded_page.evaluate(script)

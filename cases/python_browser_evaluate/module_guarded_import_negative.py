from pydantic_ai import Agent

try:
    from playwright.async_api import Page
except ImportError:
    Page = object


agent = Agent("openai:gpt-5")
continuing_page: Page | None = None


@agent.tool
async def continuing_guard_page_evaluate(script: str):
    return await continuing_page.evaluate(script)

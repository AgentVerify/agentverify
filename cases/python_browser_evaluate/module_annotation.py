from playwright.async_api import Page
from pydantic_ai import Agent


agent = Agent("openai:gpt-5")
shared_page: Page | None = None


async def set_page(page: Page) -> None:
    global shared_page
    shared_page = page


@agent.tool
async def module_page_evaluate(selector: str, script: str):
    if shared_page is None:
        return None
    locator = shared_page.locator(selector).first
    return await locator.evaluate(script)


rebound_page: Page | None = None
rebound_page = object()


@agent.tool
async def rebound_module_page_evaluate(script: str):
    return await rebound_page.evaluate(script)


duplicate_page: Page | None = None
duplicate_page: object | None = None


@agent.tool
async def duplicate_module_page_evaluate(script: str):
    return await duplicate_page.evaluate(script)


@agent.tool
async def shadowed_module_page_evaluate(shared_page, script: str):
    return await shared_page.evaluate(script)


@agent.tool
async def branch_only_module_page_evaluate(selector: str, script: str):
    if selector:
        branch_locator = shared_page.locator(selector)
    return await branch_locator.evaluate(script)


tuple_rebound_page: Page | None = None
tuple_rebound_page, marker = object(), "rebound"


@agent.tool
async def tuple_rebound_module_page_evaluate(script: str):
    return await tuple_rebound_page.evaluate(script)

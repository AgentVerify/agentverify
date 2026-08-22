from playwright.async_api import Page
from pydantic_ai import Agent

agent = Agent("openai:gpt-5")


@agent.tool
async def dynamic_evaluate(page: Page, script: str):
    return await page.evaluate(script)


@agent.tool
async def literal_evaluate(page: Page):
    return await page.evaluate("document.title")


@agent.tool
async def aliased_evaluate(page: Page, suffix: str):
    script = "https://fixed.example/" + suffix
    return await page.evaluate(script)


@agent.tool
async def aliased_page(page: Page, script: str):
    browser_page = page
    return await browser_page.evaluate(script)


class AnnotatedBrowser:
    page: Page

    @agent.tool
    async def class_evaluate(self, script: str):
        return await self.page.evaluate(script)


class InitAnnotatedBrowser:
    def __init__(self):
        self.browser_page: Page | None = None

    @agent.tool
    async def init_class_evaluate(self, script: str):
        return await self.browser_page.evaluate(script)

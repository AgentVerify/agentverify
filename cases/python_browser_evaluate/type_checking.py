from typing import TYPE_CHECKING

from pydantic_ai import Agent

if TYPE_CHECKING:
    from playwright.async_api import Page as BrowserPage


agent = Agent("openai:gpt-5")


class TypedOnlyBrowser:
    page: BrowserPage

    @agent.tool
    async def evaluate_script(self, script: str):
        return await self.page.evaluate(script)

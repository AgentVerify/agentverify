from playwright.async_api import Page
from pydantic_ai import Agent


agent = Agent("openai:gpt-5")


class PropertyBrowser:
    def __init__(self, page: Page):
        self._page = page

    @property
    def page(self) -> Page:
        return self._page

    @agent.tool
    async def property_evaluate(self, script: str):
        return await self.page.evaluate(script)


class RepeatedPropertyBrowser:
    @property
    def page(self) -> Page:
        raise NotImplementedError

    @page.setter
    def page(self, value: Page) -> None:
        pass

    @agent.tool
    async def property_evaluate(self, script: str):
        return await self.page.evaluate(script)

from playwright.async_api import Page
from pydantic_ai import Agent


agent = Agent("openai:gpt-5")


def property(function):
    return function


class ShadowedPropertyBrowser:
    @property
    def page(self) -> Page:
        raise NotImplementedError

    @agent.tool
    async def property_evaluate(self, script: str):
        return await self.page.evaluate(script)

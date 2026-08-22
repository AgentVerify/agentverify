from typing import TYPE_CHECKING

from local_types import Page as DuplicatePage
from pydantic_ai import Agent

if TYPE_CHECKING:
    from local_playwright.async_api import Page as NearPage
    from playwright.async_api import Page as ReboundPage
    from playwright.sync_api import Page as DuplicatePage


agent = Agent("openai:gpt-5")
ReboundPage = replacement


class NearBrowser:
    page: NearPage

    @agent.tool
    def evaluate_script(self, script: str):
        return self.page.evaluate(script)


class ReboundBrowser:
    page: ReboundPage

    @agent.tool
    def evaluate_script(self, script: str):
        return self.page.evaluate(script)


class DuplicateBrowser:
    page: DuplicatePage

    @agent.tool
    def evaluate_script(self, script: str):
        return self.page.evaluate(script)

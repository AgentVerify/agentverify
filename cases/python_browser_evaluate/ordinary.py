from playwright.async_api import Page
from pydantic_ai import Agent


agent = Agent("openai:gpt-5")


class Calculator:
    def evaluate(self, expression: str):
        return expression


@agent.tool
def ordinary_evaluate(calculator: Calculator, expression: str):
    return calculator.evaluate(expression)


@agent.tool
def shadowed_page(page: Page, script: str):
    page = Calculator()
    return page.evaluate(script)


@agent.tool
def late_page_alias(page: Page, script: str):
    result = browser_page.evaluate(script)
    browser_page = page
    return result


@agent.tool
def branch_page_alias(page: Page, script: str, enabled: bool):
    if enabled:
        browser_page = page
    return browser_page.evaluate(script)


@agent.tool
def container_page(pages: list[Page], script: str):
    return pages.evaluate(script)

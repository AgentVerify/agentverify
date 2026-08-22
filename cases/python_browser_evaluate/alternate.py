from playwright.async_api import Locator, Page
from pydantic_ai import Agent


agent = Agent("openai:gpt-5")


@agent.tool
async def selector_script(page: Page, script: str):
    return await page.eval_on_selector("#target", script)


@agent.tool
async def selector_only(page: Page, selector: str):
    return await page.eval_on_selector_all(selector, "els => els.length")


@agent.tool
async def handle_script(page: Page, script: str):
    return await page.evaluate_handle(expression=script)


@agent.tool
async def locator_all_script(locator: Locator, script: str):
    return await locator.evaluate_all(script)


@agent.tool
async def keyword_evaluate(page: Page, script: str):
    return await page.evaluate(expression=script)


class Calculator:
    async def evaluate_handle(self, expression: str):
        return expression


@agent.tool
async def ordinary_handle(calculator: Calculator, script: str):
    return await calculator.evaluate_handle(script)

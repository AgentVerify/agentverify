import contextlib

from playwright.async_api import async_playwright
from pydantic_ai import Agent


agent = Agent("openai:gpt-5")


@contextlib.asynccontextmanager
async def browser_page():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            context = await browser.new_context()
            page = await context.new_page()
            yield page
        finally:
            await browser.close()


@agent.tool
async def yielded_page(script: str):
    async with browser_page() as page:
        return await page.evaluate(script)


@contextlib.asynccontextmanager
async def branch_page(use_page: bool):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        if use_page:
            yield page
        else:
            yield object()


@agent.tool
async def branch_yield():
    async with branch_page(True) as page:
        return await page.evaluate("document.title")


@contextlib.asynccontextmanager
async def ordinary_page(value):
    yield value


@agent.tool
async def ordinary_yield(value):
    async with ordinary_page(value) as page:
        return await page.evaluate("document.title")


@agent.tool
async def reassigned_yield(value):
    async with browser_page() as page:
        page = value
        return await page.evaluate("document.title")

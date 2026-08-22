import contextlib

from playwright.async_api import async_playwright


@contextlib.asynccontextmanager
async def browser_page():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        yield page


async def _inspect_exact(page):
    return await page.evaluate("document.title")


async def exact_caller():
    async with browser_page() as page:
        return await _inspect_exact(page)


async def _inspect_mixed(page):
    return await page.evaluate("document.title")


async def mixed_caller():
    async with browser_page() as page:
        await _inspect_mixed(page)
    return await _inspect_mixed(object())


def consume(value):
    return value


async def _inspect_escaped(page):
    return await page.evaluate("document.title")


async def escaped_caller():
    consume(_inspect_escaped)
    async with browser_page() as page:
        return await _inspect_escaped(page)


async def _inspect_lambda(page):
    return await page.evaluate("document.title")


async def lambda_caller():
    callback = lambda: _inspect_lambda(object())
    consume(callback)
    async with browser_page() as page:
        return await _inspect_lambda(page)


async def _inspect_shadowed(page):
    return await page.evaluate("document.title")


async def shadowed_caller(_inspect_shadowed):
    async with browser_page() as page:
        return await _inspect_shadowed(page)


async def _inspect_factory_shadowed(page):
    return await page.evaluate("document.title")


async def factory_shadowed_caller(browser_page):
    async with browser_page() as page:
        return await _inspect_factory_shadowed(page)

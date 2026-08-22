from typing import Literal

from playwright.async_api import async_playwright


class ExactHelper:
    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"

    async def run(self):
        async with async_playwright() as playwright:
            browser_type = getattr(playwright, self.browser_type)
            browser = await browser_type.launch()
            scrape = self._scrape_exact
            return await scrape(browser)

    async def _scrape_exact(self, browser):
        context = await browser.new_context()
        page = await context.new_page()
        return await page.evaluate("document.title")


class MixedCalls:
    browser_type: Literal["chromium", "firefox"] = "chromium"

    async def run(self):
        async with async_playwright() as playwright:
            browser_type = getattr(playwright, self.browser_type)
            browser = await browser_type.launch()
            scrape = self._scrape_mixed
            await scrape(browser)
            return await scrape(object())

    async def _scrape_mixed(self, browser):
        context = await browser.new_context()
        page = await context.new_page()
        return await page.evaluate("document.title")


class MutableAlias:
    browser_type: Literal["chromium", "firefox"] = "chromium"

    async def run(self):
        async with async_playwright() as playwright:
            browser_type = getattr(playwright, self.browser_type)
            browser = await browser_type.launch()
            scrape = self._scrape_mutable
            scrape = self._other_mutable
            return await scrape(browser)

    async def _scrape_mutable(self, browser):
        context = await browser.new_context()
        page = await context.new_page()
        return await page.evaluate("document.title")

    async def _other_mutable(self, browser):
        return browser


class InvalidLiteral:
    browser_type: Literal["chromium", "remote"] = "chromium"

    async def run(self):
        async with async_playwright() as playwright:
            browser_type = getattr(playwright, self.browser_type)
            browser = await browser_type.launch()
            scrape = self._scrape_invalid
            return await scrape(browser)

    async def _scrape_invalid(self, browser):
        context = await browser.new_context()
        page = await context.new_page()
        return await page.evaluate("document.title")


def consume(value):
    return value


class EscapedAlias:
    browser_type: Literal["chromium", "firefox"] = "chromium"

    async def run(self):
        async with async_playwright() as playwright:
            browser_type = getattr(playwright, self.browser_type)
            browser = await browser_type.launch()
            scrape = self._scrape_escaped
            consume(scrape)
            return await scrape(browser)

    async def _scrape_escaped(self, browser):
        context = await browser.new_context()
        page = await context.new_page()
        return await page.evaluate("document.title")


class ConditionalLaunch:
    browser_type: Literal["chromium", "firefox"] = "chromium"

    async def run(self, enabled):
        async with async_playwright() as playwright:
            browser_type = getattr(playwright, self.browser_type)
            if enabled:
                browser = await browser_type.launch()
            return await self._scrape_conditional(browser)

    async def _scrape_conditional(self, browser):
        context = await browser.new_context()
        page = await context.new_page()
        return await page.evaluate("document.title")


class ExactLifecycle:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        self.page = await self.browser.new_page()

    async def title(self):
        return await self.page.evaluate("document.title")


class ConditionalLifecycle:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    async def start(self, enabled):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        if enabled:
            self.page = await self.browser.new_page()

    async def title(self):
        return await self.page.evaluate("document.title")


class ReassignedLifecycle:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        self.page = await self.browser.new_page()
        self.page = object()

    async def title(self):
        return await self.page.evaluate("document.title")


class ReassignedBrowserLifecycle:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        self.browser = object()
        self.page = await self.browser.new_page()

    async def title(self):
        return await self.page.evaluate("document.title")


class ShadowedFactoryLifecycle:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    async def start(self, async_playwright):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        self.page = await self.browser.new_page()

    async def title(self):
        return await self.page.evaluate("document.title")

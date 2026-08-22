class BranchingBrowser:
    def __init__(self):
        from playwright.async_api import async_playwright

        self.playwright = async_playwright()
        self.runtime = None
        self.browser = None
        self.context = None
        self.page = None

    async def start(self, persistent):
        self.runtime = await self.playwright.start()
        if persistent:
            self.context = await self.runtime.chromium.launch_persistent_context()
            self.browser = None
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()
        else:
            self.browser = await self.runtime.chromium.launch()
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

    async def switch_popup(self):
        popup = None
        async with self.page.expect_event("popup") as popup_info:
            pass
        popup = await popup_info.value
        if popup:
            self.page = popup

    async def inspect(self):
        return await self.page.evaluate("document.title")


class ReassignedBranchingBrowser:
    def __init__(self):
        from playwright.async_api import async_playwright

        self.playwright = async_playwright()
        self.runtime = None
        self.context = None
        self.page = None

    async def start(self):
        self.runtime = await self.playwright.start()
        self.context = await self.runtime.chromium.launch_persistent_context()
        self.page = await self.context.new_page()
        self.page = object()

    async def inspect(self):
        return await self.page.evaluate("document.title")


class WrongEventBranchingBrowser:
    def __init__(self):
        from playwright.async_api import async_playwright

        self.playwright = async_playwright()
        self.runtime = None
        self.context = None
        self.page = None

    async def start(self):
        self.runtime = await self.playwright.start()
        self.context = await self.runtime.chromium.launch_persistent_context()
        self.page = await self.context.new_page()

    async def switch_download(self):
        download = None
        async with self.page.expect_event("download") as download_info:
            pass
        download = await download_info.value
        if download:
            self.page = download

    async def inspect(self):
        return await self.page.evaluate("document.title")


class SetattrBranchingBrowser:
    def __init__(self):
        from playwright.async_api import async_playwright

        self.playwright = async_playwright()
        self.runtime = None
        self.context = None
        self.page = None

    async def start(self):
        self.runtime = await self.playwright.start()
        self.context = await self.runtime.chromium.launch_persistent_context()
        self.page = await self.context.new_page()
        field = "page"
        object.__setattr__(self, field, object())

    async def inspect(self):
        return await self.page.evaluate("document.title")


class ShadowedFactoryBranchingBrowser:
    def __init__(self, async_playwright):
        self.playwright = async_playwright()
        self.runtime = None
        self.context = None
        self.page = None

    async def start(self):
        self.runtime = await self.playwright.start()
        self.context = await self.runtime.chromium.launch_persistent_context()
        self.page = await self.context.new_page()

    async def inspect(self):
        return await self.page.evaluate("document.title")


class TupleReassignedBranchingBrowser:
    def __init__(self):
        from playwright.async_api import async_playwright

        self.playwright = async_playwright()
        self.runtime = None
        self.context = None
        self.page = None
        self.marker = None

    async def start(self):
        self.runtime = await self.playwright.start()
        self.context = await self.runtime.chromium.launch_persistent_context()
        self.page = await self.context.new_page()
        self.page, self.marker = object(), "reassigned"

    async def inspect(self):
        return await self.page.evaluate("document.title")


class PagesSliceBranchingBrowser:
    def __init__(self):
        from playwright.async_api import async_playwright

        self.playwright = async_playwright()
        self.runtime = None
        self.context = None
        self.page = None

    async def start(self):
        self.runtime = await self.playwright.start()
        self.context = await self.runtime.chromium.launch_persistent_context()
        self.page = self.context.pages[:]

    async def inspect(self):
        return await self.page.evaluate("document.title")


class ReassignedPopupInfoBranchingBrowser:
    def __init__(self):
        from playwright.async_api import async_playwright

        self.playwright = async_playwright()
        self.runtime = None
        self.context = None
        self.page = None

    async def start(self):
        self.runtime = await self.playwright.start()
        self.context = await self.runtime.chromium.launch_persistent_context()
        self.page = await self.context.new_page()

    async def switch_popup(self):
        popup = None
        async with self.page.expect_event("popup") as popup_info:
            pass
        popup_info = object()
        popup = await popup_info.value
        if popup:
            self.page = popup

    async def inspect(self):
        return await self.page.evaluate("document.title")

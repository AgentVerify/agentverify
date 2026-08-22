from pydantic_ai import Agent
from playwright.sync_api import sync_playwright


agent = Agent("openai:gpt-5")


class ConstructedBrowser:
    def __init__(self):
        self.runtime = sync_playwright().start()
        self.browser = self.runtime.chromium.launch()
        self.page = self.browser.new_page()

    @agent.tool
    def direct_evaluate(self, script: str):
        return self.page.evaluate(script)

    @agent.tool
    def aliased_evaluate(self, script: str):
        page = self.page
        return page.evaluate(script)


class ContextConstructedBrowser:
    def __init__(self):
        runtime = sync_playwright().start()
        browser = runtime.chromium.launch()
        context = browser.new_context()
        self.page = context.new_page()

    @agent.tool
    def evaluate_script(self, script: str):
        return self.page.evaluate(script)


class Calculator:
    def evaluate(self, expression: str):
        return expression


class ReassignedConstructedBrowser:
    def __init__(self):
        browser = sync_playwright().start().chromium.launch()
        self.page = browser.new_page()
        self.page = Calculator()

    @agent.tool
    def evaluate_script(self, script: str):
        return self.page.evaluate(script)


class ConditionalConstructedBrowser:
    def __init__(self, enabled: bool):
        browser = sync_playwright().start().chromium.launch()
        if enabled:
            self.page = browser.new_page()

    @agent.tool
    def evaluate_script(self, script: str):
        return self.page.evaluate(script)


class NearFactoryBrowser:
    def __init__(self, browser):
        self.page = browser.new_page()

    @agent.tool
    def evaluate_script(self, script: str):
        return self.page.evaluate(script)


class ShadowedFactoryBrowser:
    def __init__(self, sync_playwright):
        browser = sync_playwright().start().chromium.launch()
        self.page = browser.new_page()

    @agent.tool
    def evaluate_script(self, script: str):
        return self.page.evaluate(script)


class LateConstructedBrowser:
    def __init__(self):
        self.page = None

    def start(self):
        browser = sync_playwright().start().chromium.launch()
        self.page = browser.new_page()

    @agent.tool
    def evaluate_script(self, script: str):
        return self.page.evaluate(script)


class ReboundIntermediateBrowser:
    def __init__(self, browsers):
        browser = sync_playwright().start().chromium.launch()
        for browser in browsers:
            pass
        self.page = browser.new_page()

    @agent.tool
    def evaluate_script(self, script: str):
        return self.page.evaluate(script)

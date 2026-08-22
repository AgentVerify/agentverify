from pydantic_ai import Agent


agent = Agent("openai:gpt-5")


@agent.tool
def local_page_evaluate(script: str):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        try:
            context = browser.new_context()
            page = context.new_page()
            return page.evaluate(script)
        finally:
            browser.close()


@agent.tool
def shadowed_factory_evaluate(sync_playwright, script: str):
    with sync_playwright() as runtime:
        page = runtime.chromium.launch().new_page()
        return page.evaluate(script)


@agent.tool
def conditional_page_evaluate(script: str, enabled: bool):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        if enabled:
            page = browser.new_page()
        return page.evaluate(script)


@agent.tool
def reassigned_page_evaluate(script: str):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as runtime:
        page = runtime.chromium.launch().new_page()
        page = object()
        return page.evaluate(script)

import requests
from playwright.async_api import Page
from qwen_agent.tools.base import register_tool as qwen_register


@qwen_register("code_runner")
class CodeRunner:
    def call(self, page: Page, code: str):
        return page.evaluate(code)

    def helper(self, page: Page, code: str):
        return page.evaluate(code)


TOOL_NAME = "opaque_runner"


@qwen_register(TOOL_NAME)
class DynamicNameRunner:
    def call(self, page: Page, code: str):
        return page.evaluate(code)


@qwen_register("fixed_search")
class FixedSearch:
    def __init__(self):
        self.url = "https://api.example.test/search?q={query}"

    def call(self, query: str):
        host = "https://api.example.test"
        local_url = host + "/search?q=" + query
        first = requests.get(local_url)
        second = requests.get(self.url.format(query=query))
        return first, second

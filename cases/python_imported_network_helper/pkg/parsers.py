from qwen_agent.tools.base import register_tool

from .helpers import fetch_url


@register_tool("url_parser")
class UrlParser:
    def call(self, params: dict):
        url = params["url"]
        return fetch_url(url)

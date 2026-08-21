from qwen_agent.tools.base import register_tool

from .parsers import UrlParser


@register_tool("chain_parser")
class ChainParser:
    def __init__(self):
        self.parser = UrlParser()

    def call(self, params: dict):
        return self.parser.call(params)

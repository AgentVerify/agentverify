from qwen_agent.tools.base import register_tool

from . import parsers
from .chain import ChainParser
from .parsers import UrlParser
from .parsers import UrlParser as ChangedParser

ChangedParser = object


@register_tool("direct_class_loader")
class DirectClassLoader:
    def call(self, url: str):
        return UrlParser().call({"url": url})


@register_tool("bound_class_loader")
class BoundClassLoader:
    def __init__(self):
        self.parser = UrlParser()

    def call(self, url: str):
        return self.parser.call({"url": url})


@register_tool("fixed_class_loader")
class FixedClassLoader:
    def call(self):
        return UrlParser().call({"url": "https://fixed.example.test/data"})


@register_tool("multi_hop_loader")
class MultiHopLoader:
    def call(self, url: str):
        return ChainParser().call({"url": url})


@register_tool("mutable_class_loader")
class MutableClassLoader:
    def __init__(self):
        self.parser = UrlParser()

    def replace(self):
        self.parser = UrlParser()

    def call(self, url: str):
        return self.parser.call({"url": url})


@register_tool("module_class_loader")
class ModuleClassLoader:
    def call(self, url: str):
        return parsers.UrlParser().call({"url": url})


@register_tool("rebound_class_loader")
class ReboundClassLoader:
    def call(self, url: str):
        return ChangedParser().call({"url": url})


@register_tool("setattr_class_loader")
class SetattrClassLoader:
    def __init__(self):
        self.parser = UrlParser()

    def replace(self):
        setattr(self, "parser", UrlParser())

    def call(self, url: str):
        return self.parser.call({"url": url})


@register_tool("shadowed_class_loader")
class ShadowedClassLoader:
    def __init__(self):
        UrlParser = object
        self.parser = UrlParser()

    def call(self, url: str):
        return self.parser.call({"url": url})


@register_tool("mixed_field_loader")
class MixedFieldLoader:
    def call(self, query: str):
        return UrlParser().call({
            "url": "https://fixed.example.test/data",
            "query": query,
        })


@register_tool("nested_binding_loader")
class NestedBindingLoader:
    def __init__(self):
        def bind():
            self.parser = UrlParser()

        bind()

    def call(self, url: str):
        return self.parser.call({"url": url})


@register_tool("shadowed_module_class_loader")
class ShadowedModuleClassLoader:
    def call(self, url: str):
        parsers = object()
        return parsers.UrlParser().call({"url": url})

from qwen_agent.tools.base import register_tool

from . import helpers
from .helpers import fetch_url as download
from .helpers import fixed_search, nested_fetch
from .helpers import fetch_url as changed_download
from .rebound_helpers import fetch_url as rebound_client_fetch

changed_download = lambda value: value


@register_tool("remote_loader")
class RemoteLoader:
    def call(self, url: str):
        download(url)
        fixed_search(url)
        nested_fetch(url)
        changed_download(url)
        rebound_client_fetch(url)
        helpers.fetch_url(url)


@register_tool("fixed_loader")
class FixedLoader:
    def call(self):
        download("https://fixed.example.test/data")


@register_tool("local_rebound_loader")
class LocalReboundLoader:
    def call(self, url: str):
        from .helpers import fetch_url as local_download

        local_download = lambda value: value
        local_download(url)

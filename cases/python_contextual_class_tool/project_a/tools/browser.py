import requests
from langchain.tools import tool


class BrowserTools:
    @tool("Browse a URL")
    def browse(url: str) -> str:
        return requests.get(url).text

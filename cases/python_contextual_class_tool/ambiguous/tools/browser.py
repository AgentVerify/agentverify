from langchain.tools import tool


class BrowserTools:
    @tool("Parent browser")
    def browse(url: str) -> str:
        return url

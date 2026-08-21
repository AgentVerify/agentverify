from langchain.tools import tool


class OtherBrowserTools:
    @tool("Other browser")
    def browse(url: str) -> str:
        return url

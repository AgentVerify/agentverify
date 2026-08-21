from langchain.tools import tool


class BrowserTools:
    @tool("Nested browser")
    def browse(url: str) -> str:
        return url

import requests
from agents import Agent, function_tool


@function_tool
def fetch_url(url: str) -> str:
    return requests.get(url, timeout=10).text


@function_tool
def search(query: str) -> dict:
    return requests.get(f"https://search.example/api?q={query}", timeout=10).json()


@function_tool
def status() -> dict:
    return requests.get("https://status.example/api", timeout=10).json()


agent = Agent(name="networker", tools=[fetch_url, search, status])

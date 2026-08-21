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


import urllib.request as urlrequest
from urllib import request as request_alias
from urllib.request import Request as URLRequest
from urllib.request import urlopen as open_url
from urllib.request import urlopen as changed_urlopen

changed_urlopen = object


@function_tool
def urllib_direct(url: str) -> bytes:
    return urlrequest.urlopen(url=url).read()


@function_tool
def urllib_request(url: str) -> bytes:
    request = URLRequest(url)
    return open_url(request).read()


@function_tool
def urllib_fixed_request(query: str) -> bytes:
    request = request_alias.Request(f"https://search.example/api?q={query}")
    return request_alias.urlopen(request).read()


@function_tool
def urllib_shadowed(url: str) -> bytes:
    open_url = lambda value: value
    return open_url(url).read()


@function_tool
def urllib_rebound(url: str) -> bytes:
    return changed_urlopen(url).read()


agent = Agent(
    name="networker",
    tools=[
        fetch_url,
        search,
        status,
        urllib_direct,
        urllib_request,
        urllib_fixed_request,
        urllib_shadowed,
        urllib_rebound,
    ],
)

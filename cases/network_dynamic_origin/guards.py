import requests
from agents import Agent, function_tool
from urllib.parse import urlparse, urlsplit

ALLOWED_HOSTS = frozenset({"api.example.com", "cdn.example.com"})


@function_tool
def guarded_fetch(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("origin is not allowed")
    return requests.get(url, allow_redirects=False, timeout=10).text


@function_tool
def guarded_alias_fetch(url: str) -> str:
    target = url
    parsed = urlparse(target)
    if parsed.scheme not in {"https"} or parsed.hostname not in {"api.example.com"}:
        raise ValueError("origin is not allowed")
    return requests.get(target, timeout=10).text


@function_tool
def late_guard(url: str) -> str:
    response = requests.get(url, timeout=10)
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("origin is not allowed")
    return response.text


@function_tool
def scheme_only(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https":
        raise ValueError("scheme is not allowed")
    return requests.get(url, timeout=10).text


@function_tool
def continuing_guard(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        print("origin is not allowed")
    return requests.get(url, timeout=10).text


@function_tool
def rebound_parser(url: str) -> str:
    parsed = urlsplit(url)
    parsed = object()
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("origin is not allowed")
    return requests.get(url, timeout=10).text


@function_tool
def shadowed_parser(url: str) -> str:
    urlsplit = lambda value: value
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("origin is not allowed")
    return requests.get(url, timeout=10).text


MUTABLE_HOSTS = {"api.example.com"}


@function_tool
def mutable_host_policy(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in MUTABLE_HOSTS:
        raise ValueError("origin is not allowed")
    return requests.get(url, timeout=10).text


@function_tool
def rejection_branch_request(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        return requests.get(url, timeout=10).text
    return "allowed"


agent = Agent(
    name="guarded-networker",
    tools=[
        guarded_fetch,
        guarded_alias_fetch,
        late_guard,
        scheme_only,
        continuing_guard,
        rebound_parser,
        shadowed_parser,
        mutable_host_policy,
        rejection_branch_request,
    ],
)

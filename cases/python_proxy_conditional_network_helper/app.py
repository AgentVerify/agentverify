import requests
from transport.url_safety import safe_get, safe_request


def download(url: str):
    return safe_get(url)


def upload(url: str, body: bytes):
    return safe_request("PUT", url, data=body)


def incomplete(url: str):
    return requests.get(url)

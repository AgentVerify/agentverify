from urllib.parse import urljoin

import requests

from secure_transport.safe_path import validate_url
from secure_transport.ssrf_adapter import SSRFProtectedAdapter


def create_safe_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.proxies = {}
    adapter = SSRFProtectedAdapter()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _raw_get(url: str, **kwargs: object) -> requests.Response:
    session = create_safe_session()
    return session.get(url, **kwargs)


def _reject_proxies(kwargs: dict[str, object]) -> None:
    if kwargs.pop("proxies", None):
        raise ValueError("proxies disabled")
    kwargs["proxies"] = {}


def safe_get(url: str, **kwargs: object) -> requests.Response:
    current_url = validate_url(url)
    _reject_proxies(kwargs)
    request_kwargs = {**kwargs, "allow_redirects": False}
    while True:
        response = _raw_get(current_url, **request_kwargs)
        location = response.headers.get("Location")
        if not location:
            return response
        redirect_url = validate_url(urljoin(response.url, location))
        current_url = redirect_url


def partial_get(url: str, **kwargs: object) -> requests.Response:
    current_url = validate_url(url)
    _reject_proxies(kwargs)
    request_kwargs = {**kwargs, "allow_redirects": False}
    while True:
        response = _raw_get(current_url, **request_kwargs)
        location = response.headers.get("Location")
        if not location:
            return response
        current_url = urljoin(response.url, location)

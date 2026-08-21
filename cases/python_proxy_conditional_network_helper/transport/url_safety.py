import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests


def is_blocked_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return not address.is_global


def assert_safe_fetch_target(url: str) -> list[str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("unsafe scheme")
    addresses = [result[4][0] for result in socket.getaddrinfo(parsed.hostname, None)]
    for address in addresses:
        if is_blocked_ip(address):
            raise ValueError("blocked address")
    return addresses


class _PinnedAddressAdapter:
    def __init__(self, addresses: list[str]):
        self.addresses = addresses

    def get_connection_with_tls_context(self):
        connection = self.connection
        address = self.addresses[0]
        hostname = connection._dns_host
        connection._dns_host = address
        sock = open_socket()
        connection._dns_host = hostname
        _assert_pinned_peer(sock, address, hostname)
        return connection


def _assert_pinned_peer(sock, address: str, hostname: str) -> None:
    peer = sock.getpeername()[0]
    if ipaddress.ip_address(peer) == ipaddress.ip_address(address):
        return
    sock.close()
    raise ValueError(f"{hostname} connected to {peer}")


def _proxy_applies(url: str, proxies) -> bool:
    try:
        environment = requests.utils.get_environ_proxies(url)
        return (
            requests.utils.select_proxy(url, {**environment, **(proxies or {})})
            is not None
        )
    except OSError:
        return True


def _pinned_request(method: str, url: str, **kwargs):
    addresses = assert_safe_fetch_target(url)
    session = requests.Session()
    if not _proxy_applies(url, kwargs.get("proxies")):
        adapter = _PinnedAddressAdapter(addresses)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
    response = session.request(method, url, allow_redirects=False, **kwargs)
    return response


def safe_get(url: str, **kwargs):
    return _pinned_request("GET", url, **kwargs)


def safe_request(method: str, url: str, *, max_redirects: int = 5, **kwargs):
    current_url = url
    for _ in range(max_redirects + 1):
        response = _pinned_request(method, current_url, **kwargs)
        location = response.headers.get("Location")
        if response.status_code not in {301, 302, 303, 307, 308} or location is None:
            return response
        current_url = urljoin(current_url, location)
    raise ValueError("too many redirects")


def open_socket():
    return object()

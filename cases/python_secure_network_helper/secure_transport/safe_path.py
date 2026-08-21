import ipaddress
import os
import socket
from urllib.parse import urlparse

_UNSAFE_PATHS_ENV = "ALLOW_UNSAFE_NETWORK"
_FORCE_SAFE_PATHS_ENV = "FORCE_SAFE_NETWORK"


def _env_flag_enabled(name: str) -> bool:
    return os.environ.get(name, "").lower() in ("true", "1", "yes")


def _is_escape_hatch_enabled() -> bool:
    if _env_flag_enabled(_FORCE_SAFE_PATHS_ENV):
        return False
    return _env_flag_enabled(_UNSAFE_PATHS_ENV)


def is_blocked_ip(value: str) -> bool:
    return ipaddress.ip_address(value).is_private


def validate_url(url: str) -> str:
    if _is_escape_hatch_enabled():
        return url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("unsupported scheme")
    if not parsed.hostname:
        raise ValueError("missing host")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
    for address in addresses:
        if is_blocked_ip(address[4][0]):
            raise ValueError("private address")
    return url

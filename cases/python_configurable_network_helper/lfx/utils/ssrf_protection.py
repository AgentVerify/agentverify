import os
from urllib.parse import urlparse


def get_settings_service():
    return object()


def is_ssrf_protection_enabled() -> bool:
    os.getenv("LANGFLOW_SSRF_PROTECTION_ENABLED")
    return bool(get_settings_service())


def is_connector_ssrf_validation_enabled() -> bool:
    os.getenv("LANGFLOW_CONNECTOR_SSRF_VALIDATION_ENABLED")
    return bool(get_settings_service())


def is_connector_loopback_allowed() -> bool:
    os.getenv("LANGFLOW_CONNECTOR_SSRF_ALLOW_LOOPBACK")
    return bool(get_settings_service())


def get_allowed_hosts():
    os.getenv("LANGFLOW_SSRF_ALLOWED_HOSTS")
    get_settings_service()
    return []


def is_host_allowed(hostname):
    return hostname in get_allowed_hosts()


def _validate_raw_url_authority(url):
    if not url:
        raise ValueError("missing URL")


def _is_loopback_host(hostname):
    return hostname == "localhost"


def _connector_url_has_loopback_exemption(url: str) -> bool:
    if not is_ssrf_protection_enabled():
        return False
    _validate_raw_url_authority(url)
    parsed = urlparse(url)
    if not parsed.hostname:
        raise ValueError("missing hostname")
    return is_connector_loopback_allowed() and _is_loopback_host(parsed.hostname)


def validate_and_resolve_connector_url(url: str):
    if not is_connector_ssrf_validation_enabled() or _connector_url_has_loopback_exemption(url):
        return url, []
    return validate_and_resolve_url(url)


def validate_and_resolve_url(url: str):
    if not is_ssrf_protection_enabled():
        return url, []
    parsed = urlparse(url)
    _validate_url_scheme(parsed.scheme)
    hostname = _validate_hostname_exists(parsed.hostname)
    if is_host_allowed(hostname):
        return url, []
    resolved_ips = resolve_hostname(hostname)
    if any(is_ip_blocked(ip) for ip in resolved_ips):
        raise ValueError("blocked")
    return url, resolved_ips


def _validate_url_scheme(value):
    return value


def _validate_hostname_exists(value):
    return value


def resolve_hostname(value):
    return [value]


def is_ip_blocked(value):
    return False

from urllib.parse import urljoin

from lfx.utils.ssrf_protection import (
    is_ssrf_protection_enabled,
    validate_and_resolve_connector_url,
)
from lfx.utils.ssrf_transport import (
    SSRFProtectedSyncTransport,
    SSRFProtectedTransport,
    create_ssrf_protected_client,
    create_ssrf_protected_sync_client,
)

TRANSPORT_TYPES = (SSRFProtectedTransport, SSRFProtectedSyncTransport)


def AsyncClient():
    return object()


def Client():
    return object()


def _raise_if_following_redirects(kwargs):
    if kwargs.get("follow_redirects"):
        raise ValueError("automatic redirects disabled")


def _async_client_for_url(url, validated_ips):
    if is_ssrf_protection_enabled() and validated_ips:
        return create_ssrf_protected_client(url, validated_ips)
    return AsyncClient()


def _sync_client_for_url(url, validated_ips):
    if is_ssrf_protection_enabled() and validated_ips:
        return create_ssrf_protected_sync_client(url, validated_ips)
    return Client()


async def ssrf_safe_async_get(url, **kwargs):
    _raise_if_following_redirects(kwargs)
    validated_url, validated_ips = validate_and_resolve_connector_url(url)
    client = _async_client_for_url(validated_url, validated_ips)
    return await client.get(validated_url)


async def ssrf_safe_async_post(url, **kwargs):
    _raise_if_following_redirects(kwargs)
    validated_url, validated_ips = validate_and_resolve_connector_url(url)
    client = _async_client_for_url(validated_url, validated_ips)
    return await client.post(validated_url)


def ssrf_safe_httpx_get(url, *, follow_redirects=False, max_redirects=5):
    current_url = url
    for _ in range(max_redirects + 1):
        validated_url, validated_ips = validate_and_resolve_connector_url(current_url)
        client = _sync_client_for_url(validated_url, validated_ips)
        response = client.get(validated_url, follow_redirects=False)
        if not follow_redirects:
            return response
        current_url = urljoin(validated_url, response.headers["location"])
    raise ValueError("redirect limit")


def ssrf_safe_httpx_post(url, **kwargs):
    _raise_if_following_redirects(kwargs)
    validated_url, validated_ips = validate_and_resolve_connector_url(url)
    client = _sync_client_for_url(validated_url, validated_ips)
    return client.post(validated_url)

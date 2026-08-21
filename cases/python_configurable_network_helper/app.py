import httpx
from lfx.utils.ssrf_httpx import ssrf_safe_async_get, ssrf_safe_httpx_get


def models(url: str):
    return ssrf_safe_httpx_get(url)


async def async_models(url: str):
    return await ssrf_safe_async_get(url)


def incomplete(url: str):
    return httpx.get(url)

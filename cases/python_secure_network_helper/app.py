from secure_transport.safe_requests import partial_get, safe_get
from secure_transport.safe_requests import safe_get as protected_get


def load(url: str):
    return safe_get(url)


def load_alias(url: str):
    return protected_get(url)


def load_partial(url: str):
    return partial_get(url)


safe_get = lambda url: url  # noqa: F811


def load_rebound(url: str):
    return safe_get(url)

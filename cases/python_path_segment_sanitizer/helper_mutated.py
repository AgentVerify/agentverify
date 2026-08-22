import hashlib


def replace_hashlib() -> None:
    global hashlib
    hashlib = None


def digest_segment(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

import hashlib


def digest_segment(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

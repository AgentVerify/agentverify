import hashlib


def digest_segment(value: str) -> str:
    digest = hashlib.sha256(value.encode())
    encoded = digest.hexdigest()
    return encoded

import os

from agents import function_tool
from helper import digest_segment

CACHE_ROOT = "/var/tmp/agentverify-cache"


@function_tool
def shadowed_hashlib(user_value: str) -> None:
    target = os.path.join(CACHE_ROOT, digest_segment(user_value))
    os.makedirs(target, exist_ok=True)

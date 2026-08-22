import os

from agents import function_tool
from helper import digest_segment
from helper_mutated import digest_segment as mutable_digest

CACHE_ROOT = "/var/tmp/agentverify-cache"


def unsafe_join(*parts: str) -> str:
    return parts[-1]


os.path.join = unsafe_join


@function_tool
def mutated_join(user_value: str) -> None:
    target = os.path.join(CACHE_ROOT, digest_segment(user_value))
    os.makedirs(target, exist_ok=True)


@function_tool
def mutated_hashlib(user_value: str) -> None:
    target = unsafe_join(CACHE_ROOT, mutable_digest(user_value))
    os.makedirs(target, exist_ok=True)

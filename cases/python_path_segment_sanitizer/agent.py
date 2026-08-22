import os

from agents import function_tool
from fake import digest_segment as fake_segment
from helper import digest_segment as segment_key

CACHE_ROOT = "/var/tmp/agentverify-cache"


@function_tool
def safe_digest_directory(user_value: str) -> None:
    target = os.path.join(CACHE_ROOT, segment_key(user_value))
    os.makedirs(target, exist_ok=True)


@function_tool
def unsafe_extra_segment(user_value: str) -> None:
    target = os.path.join(CACHE_ROOT, segment_key(user_value), user_value)
    os.makedirs(target, exist_ok=True)


@function_tool
def unsafe_digest_root(user_value: str) -> None:
    target = os.path.join(segment_key(user_value), "cache")
    os.makedirs(target, exist_ok=True)


@function_tool
def unsafe_lookalike(user_value: str) -> None:
    target = os.path.join(CACHE_ROOT, fake_segment(user_value))
    os.makedirs(target, exist_ok=True)


@function_tool
def unsafe_rebound(user_value: str) -> None:
    segment_key = lambda value: value
    target = os.path.join(CACHE_ROOT, segment_key(user_value))
    os.makedirs(target, exist_ok=True)


@function_tool
def unsafe_branch_escape(user_value: str, enabled: bool) -> None:
    if enabled:
        target = os.path.join(CACHE_ROOT, segment_key(user_value))
    os.makedirs(target, exist_ok=True)

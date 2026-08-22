import os

from agents import Agent, function_tool
import requests

from pkg import settings
from pkg.settings import ALIASED_BASE as RENAMED_BASE
from pkg.settings import COMPOSED_BASE
from pkg.settings import ENV_BASE
from pkg.settings import FIXED_BASE
from pkg.settings import GLOBAL_MUTATED_BASE
from pkg.settings import REASSIGNED_SOURCE_BASE
from pkg.settings import REBOUND_BASE


REBOUND_BASE = os.getenv("REBOUND_BASE", "https://fallback.example.com")
VERSIONED_BASE = f"{FIXED_BASE}/v1"


@function_tool
def fixed_import(item: str) -> str:
    url = f"{FIXED_BASE}/items/{item}"
    return requests.get(url, timeout=10).text


@function_tool
def fixed_alias(item: str) -> str:
    return requests.get(f"{RENAMED_BASE}/items/{item}", timeout=10).text


@function_tool
def fixed_module_alias(item: str) -> str:
    return requests.get(f"{VERSIONED_BASE}/items/{item}", timeout=10).text


@function_tool
def environment_origin(item: str) -> str:
    return requests.get(f"{ENV_BASE}/items/{item}", timeout=10).text


@function_tool
def composed_source_origin(item: str) -> str:
    return requests.get(f"{COMPOSED_BASE}/items/{item}", timeout=10).text


@function_tool
def reassigned_source_origin(item: str) -> str:
    return requests.get(f"{REASSIGNED_SOURCE_BASE}/items/{item}", timeout=10).text


@function_tool
def global_mutated_origin(item: str) -> str:
    return requests.get(f"{GLOBAL_MUTATED_BASE}/items/{item}", timeout=10).text


@function_tool
def rebound_consumer_origin(item: str) -> str:
    return requests.get(f"{REBOUND_BASE}/items/{item}", timeout=10).text


@function_tool
def shadowed_import(FIXED_BASE: str, item: str) -> str:
    return requests.get(f"{FIXED_BASE}/items/{item}", timeout=10).text


@function_tool
def module_qualified_origin(item: str) -> str:
    return requests.get(f"{settings.FIXED_BASE}/items/{item}", timeout=10).text


@function_tool
def match_shadowed_import(item: str, payload: dict) -> str:
    match payload:
        case {"base": FIXED_BASE}:
            return requests.get(f"{FIXED_BASE}/items/{item}", timeout=10).text
    return "no base"


agent = Agent(
    name="imported-literal-origins",
    tools=[
        fixed_import,
        fixed_alias,
        fixed_module_alias,
        environment_origin,
        composed_source_origin,
        reassigned_source_origin,
        global_mutated_origin,
        rebound_consumer_origin,
        shadowed_import,
        module_qualified_origin,
        match_shadowed_import,
    ],
)

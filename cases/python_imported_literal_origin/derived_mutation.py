from agents import function_tool
import requests

from pkg.settings import FIXED_BASE


DERIVED_BASE = f"{FIXED_BASE}/v2"


def replace_derived_base(value: str) -> None:
    global DERIVED_BASE
    DERIVED_BASE = value


@function_tool
def globally_mutated_derived_origin(item: str) -> str:
    return requests.get(f"{DERIVED_BASE}/items/{item}", timeout=10).text

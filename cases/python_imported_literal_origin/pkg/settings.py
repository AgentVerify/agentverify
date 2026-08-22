import os


FIXED_BASE = "https://api.example.com"
ALIASED_BASE = "https://alias.example.com"
ENV_BASE = os.getenv("API_BASE", "https://fallback.example.com")
COMPOSED_BASE = "https://" + "composed.example.com"

REASSIGNED_SOURCE_BASE = "https://first.example.com"
REASSIGNED_SOURCE_BASE = "https://second.example.com"

GLOBAL_MUTATED_BASE = "https://global.example.com"


def replace_global_base(value: str) -> None:
    global GLOBAL_MUTATED_BASE
    GLOBAL_MUTATED_BASE = value


REBOUND_BASE = "https://rebound.example.com"

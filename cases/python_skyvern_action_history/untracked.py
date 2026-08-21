import requests
from agents import function_tool


@function_tool
def send_untracked(payload: dict) -> None:
    requests.post("https://example.invalid/send", json=payload)

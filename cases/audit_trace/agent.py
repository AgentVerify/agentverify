import httpx
from agents import function_tool
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


@function_tool
def send_email(payload: dict) -> dict:
    with tracer.start_as_current_span("gmail.send"):
        return httpx.post("https://example.invalid/send", json=payload).json()


@function_tool
def delete_email(message_id: str) -> None:
    httpx.delete(f"https://example.invalid/messages/{message_id}")

from pathlib import Path


def imported_write(path: str) -> None:
    Path(path).write_text("imported")


def rebound_write(path: str) -> None:
    Path(path).write_text("rebound")


def nested_write(path: str) -> None:
    Path(path).write_text("nested")


def wrapped_write(path: str) -> None:
    Path(path).write_text("wrapped")


def direct_wrapped_write(path: str) -> None:
    Path(path).write_text("direct wrapped")


def factory_wrapped_write(path: str) -> None:
    Path(path).write_text("factory wrapped")


def nested_wrapped_write(path: str) -> None:
    Path(path).write_text("nested wrapped")


def misleading_wrapped_write(path: str) -> None:
    Path(path).write_text("misleading wrapped")


def branch_wrapped_write(path: str) -> None:
    Path(path).write_text("branch wrapped")


def deferred_wrapped_write(path: str) -> None:
    Path(path).write_text("deferred wrapped")

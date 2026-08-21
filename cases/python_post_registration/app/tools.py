from pathlib import Path


def imported_write(path: str) -> None:
    Path(path).write_text("imported")


def rebound_write(path: str) -> None:
    Path(path).write_text("rebound")


def nested_write(path: str) -> None:
    Path(path).write_text("nested")


def wrapped_write(path: str) -> None:
    Path(path).write_text("wrapped")

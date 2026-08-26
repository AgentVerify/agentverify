from pathlib import Path

__all__ = ["star_writer"]


def star_writer(path: str) -> str:
    Path(path).write_text("star", encoding="utf-8")
    return path


def filtered_hidden(path: str) -> str:
    Path(path).write_text("hidden", encoding="utf-8")
    return path

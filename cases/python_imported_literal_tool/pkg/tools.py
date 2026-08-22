from pathlib import Path


def imported_writer(path: str) -> str:
    Path(path).write_text("updated", encoding="utf-8")
    return path

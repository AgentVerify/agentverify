from pathlib import Path

from langchain.tools import tool


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _resolve(self, requested: str) -> Path:
        candidate = Path(requested)
        target = candidate if candidate.is_absolute() else self.root / candidate
        target = target.resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            raise ValueError("outside workspace") from None
        return target

    @tool
    def write(self, requested: str) -> None:
        target = self._resolve(requested=requested)
        target.write_text("bounded", encoding="utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)

    @tool
    def reassigned_caller(self, requested: str) -> None:
        target = self._resolve(requested)
        target = Path(requested).resolve()
        target.write_text("reassigned", encoding="utf-8")


class ContinuingHandler:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _resolve(self, requested: str) -> Path:
        target = (self.root / Path(requested)).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            pass
        return target

    @tool
    def write(self, requested: str) -> None:
        target = self._resolve(requested)
        target.write_text("continuing handler", encoding="utf-8")


class WrongReturn:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _resolve(self, requested: str) -> Path:
        target = (self.root / Path(requested)).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            raise ValueError("outside workspace") from None
        other = Path(requested).resolve()
        return other

    @tool
    def write(self, requested: str) -> None:
        target = self._resolve(requested)
        target.write_text("wrong return", encoding="utf-8")


class ReassignedReturn:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _resolve(self, requested: str) -> Path:
        target = (self.root / Path(requested)).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            raise ValueError("outside workspace") from None
        target = Path(requested).resolve()
        return target

    @tool
    def write(self, requested: str) -> None:
        target = self._resolve(requested)
        target.write_text("reassigned return", encoding="utf-8")


class TransformedReturn:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _resolve(self, requested: str) -> Path:
        target = (self.root / Path(requested)).with_name(requested).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            raise ValueError("outside workspace") from None
        return target

    @tool
    def write(self, requested: str) -> None:
        target = self._resolve(requested)
        target.write_text("opaque transform", encoding="utf-8")


class DuplicateHelper:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _resolve(self, requested: str) -> Path:
        target = (self.root / Path(requested)).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            raise ValueError("outside workspace") from None
        return target

    def _resolve(self, requested: str) -> Path:
        return Path(requested).resolve()

    @tool
    def write(self, requested: str) -> None:
        target = self._resolve(requested)
        target.write_text("duplicate helper", encoding="utf-8")


class FinallyReassigned:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _resolve(self, requested: str) -> Path:
        target = (self.root / Path(requested)).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            raise ValueError("outside workspace") from None
        finally:
            target = Path(requested).resolve()
        return target

    @tool
    def write(self, requested: str) -> None:
        target = self._resolve(requested)
        target.write_text("finally reassigned", encoding="utf-8")


class ConditionalPrelude:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _resolve(self, requested: str, replace: bool) -> Path:
        target = (self.root / Path(requested)).resolve()
        if replace:
            target = Path(requested)
        try:
            target.relative_to(self.root)
        except ValueError:
            raise ValueError("outside workspace") from None
        return target

    @tool
    def write(self, requested: str) -> None:
        target = self._resolve(requested, replace=True)
        target.write_text("conditional prelude", encoding="utf-8")

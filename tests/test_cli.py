from __future__ import annotations

from pathlib import Path

import pytest

from agentverify import cli

ROOT = Path(__file__).resolve().parents[1]


def test_cli_handles_closed_output_pipe(monkeypatch: pytest.MonkeyPatch) -> None:
    def closed_pipe(*args: object, **kwargs: object) -> None:
        raise BrokenPipeError

    monkeypatch.setattr("builtins.print", closed_pipe)
    assert cli.main(["scan", str(ROOT / "examples/safe_agent")]) == 0

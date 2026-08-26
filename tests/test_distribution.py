from __future__ import annotations

import importlib.util
import os
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_distribution", ROOT / "scripts/verify_distribution.py"
)
assert SPEC is not None
verify_distribution = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(verify_distribution)

REQUIRED_SCHEMA_FILES = verify_distribution.REQUIRED_SCHEMA_FILES
REQUIRED_ENTRY_POINTS = verify_distribution.REQUIRED_ENTRY_POINTS
latest_wheel = verify_distribution.latest_wheel
verify_wheel = verify_distribution.verify_wheel


def write_wheel(path: Path, names: set[str], *, entry_points: bool = True) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name in sorted(names):
            archive.writestr(name, "{}\n")
        if entry_points:
            archive.writestr(
                "agentverify-0.1.0.dist-info/entry_points.txt",
                "[console_scripts]\nagentverify = agentverify.cli:main\n",
            )


def test_distribution_verifier_accepts_all_required_schemas(tmp_path: Path) -> None:
    wheel = tmp_path / "agentverify-0.1.0-py3-none-any.whl"
    write_wheel(wheel, set(REQUIRED_SCHEMA_FILES) | {"agentverify/__init__.py"})

    payload = verify_wheel(wheel)

    assert payload["passed"] is True
    assert payload["required_schema_files"] == 4
    assert payload["missing_schema_files"] == []
    assert payload["present_schema_files"] == sorted(REQUIRED_SCHEMA_FILES)
    assert payload["console_scripts"] == REQUIRED_ENTRY_POINTS
    assert payload["missing_entry_points"] == {}


def test_distribution_verifier_rejects_missing_schema(tmp_path: Path) -> None:
    wheel = tmp_path / "agentverify-0.1.0-py3-none-any.whl"
    missing = {"agentverify/schemas/agentverify-rules-v1.schema.json"}
    write_wheel(wheel, set(REQUIRED_SCHEMA_FILES) - missing)

    with pytest.raises(RuntimeError, match="agentverify-rules-v1.schema.json"):
        verify_wheel(wheel)


def test_distribution_verifier_rejects_missing_console_script(tmp_path: Path) -> None:
    wheel = tmp_path / "agentverify-0.1.0-py3-none-any.whl"
    write_wheel(wheel, set(REQUIRED_SCHEMA_FILES), entry_points=False)

    with pytest.raises(RuntimeError, match="missing_entry_points"):
        verify_wheel(wheel)


def test_distribution_verifier_selects_newest_wheel(tmp_path: Path) -> None:
    older = tmp_path / "agentverify-0.0.9-py3-none-any.whl"
    newer = tmp_path / "agentverify-0.1.0-py3-none-any.whl"
    write_wheel(older, set(REQUIRED_SCHEMA_FILES))
    write_wheel(newer, set(REQUIRED_SCHEMA_FILES))
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))

    assert latest_wheel(tmp_path) == newer

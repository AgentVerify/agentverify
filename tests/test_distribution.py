from __future__ import annotations

import importlib.util
import io
import os
import tarfile
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
REQUIRED_BENCHMARK_RESULT_FILES = verify_distribution.REQUIRED_BENCHMARK_RESULT_FILES
REQUIRED_SOURCE_FILES = verify_distribution.REQUIRED_SOURCE_FILES
REQUIRED_ENTRY_POINTS = verify_distribution.REQUIRED_ENTRY_POINTS
latest_sdist = verify_distribution.latest_sdist
latest_wheel = verify_distribution.latest_wheel
verify_sdist = verify_distribution.verify_sdist
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


def write_sdist(path: Path, names: set[str], *, root: str = "agentverify-0.1.0") -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name in sorted(names):
            content = b"{}\n" if name.endswith(".json") else b"placeholder\n"
            info = tarfile.TarInfo(f"{root}/{name}")
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))


def test_distribution_verifier_accepts_all_required_schemas(tmp_path: Path) -> None:
    wheel = tmp_path / "agentverify-0.1.0-py3-none-any.whl"
    write_wheel(wheel, set(REQUIRED_SCHEMA_FILES) | {"agentverify/__init__.py"})

    payload = verify_wheel(wheel)

    assert payload["passed"] is True
    assert payload["required_schema_files"] == 8
    assert payload["missing_schema_files"] == []
    assert payload["present_schema_files"] == sorted(REQUIRED_SCHEMA_FILES)
    assert payload["console_scripts"] == REQUIRED_ENTRY_POINTS
    assert payload["missing_entry_points"] == {}


def test_distribution_verifier_accepts_required_source_artifacts(tmp_path: Path) -> None:
    sdist = tmp_path / "agentverify-0.1.0.tar.gz"
    write_sdist(
        sdist,
        set(REQUIRED_SOURCE_FILES)
        | set(REQUIRED_BENCHMARK_RESULT_FILES)
        | {"src/agentverify/__init__.py"},
    )

    payload = verify_sdist(sdist)

    assert payload["passed"] is True
    assert payload["required_source_files"] == len(
        REQUIRED_SOURCE_FILES | REQUIRED_BENCHMARK_RESULT_FILES
    )
    assert payload["missing_source_files"] == []
    assert payload["present_source_files"] == sorted(
        REQUIRED_SOURCE_FILES | REQUIRED_BENCHMARK_RESULT_FILES
    )
    assert payload["required_benchmark_result_files"] == len(REQUIRED_BENCHMARK_RESULT_FILES)
    assert payload["missing_benchmark_result_files"] == []
    assert payload["present_benchmark_result_files"] == sorted(REQUIRED_BENCHMARK_RESULT_FILES)


def test_distribution_verifier_rejects_missing_schema(tmp_path: Path) -> None:
    wheel = tmp_path / "agentverify-0.1.0-py3-none-any.whl"
    missing = {"agentverify/schemas/agentverify-rules-v1.schema.json"}
    write_wheel(wheel, set(REQUIRED_SCHEMA_FILES) - missing)

    with pytest.raises(RuntimeError, match="agentverify-rules-v1.schema.json"):
        verify_wheel(wheel)


def test_distribution_verifier_rejects_missing_source_artifact(tmp_path: Path) -> None:
    sdist = tmp_path / "agentverify-0.1.0.tar.gz"
    missing = {"examples/repository-policy.json"}
    write_sdist(
        sdist, (set(REQUIRED_SOURCE_FILES) | set(REQUIRED_BENCHMARK_RESULT_FILES)) - missing
    )

    with pytest.raises(RuntimeError, match="examples/repository-policy.json"):
        verify_sdist(sdist)


def test_distribution_verifier_rejects_missing_benchmark_result_artifact(
    tmp_path: Path,
) -> None:
    sdist = tmp_path / "agentverify-0.1.0.tar.gz"
    missing = {"benchmarks/ir-truthset-results.json"}
    write_sdist(
        sdist, (set(REQUIRED_SOURCE_FILES) | set(REQUIRED_BENCHMARK_RESULT_FILES)) - missing
    )

    with pytest.raises(RuntimeError, match="missing_benchmark_result_files"):
        verify_sdist(sdist)


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


def test_distribution_verifier_selects_newest_sdist(tmp_path: Path) -> None:
    older = tmp_path / "agentverify-0.0.9.tar.gz"
    newer = tmp_path / "agentverify-0.1.0.tar.gz"
    write_sdist(older, set(REQUIRED_SOURCE_FILES) | set(REQUIRED_BENCHMARK_RESULT_FILES))
    write_sdist(newer, set(REQUIRED_SOURCE_FILES) | set(REQUIRED_BENCHMARK_RESULT_FILES))
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))

    assert latest_sdist(tmp_path) == newer

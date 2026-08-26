from __future__ import annotations

import importlib.util
import io
import os
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
GITHUB_BENCHMARK_VERIFY = ROOT / "examples/github-benchmark-verify.yml"
GITHUB_CODE_SCANNING = ROOT / "examples/github-code-scanning.yml"
GITHUB_POLICY_GATE = ROOT / "examples/github-policy-gate.yml"
SPEC = importlib.util.spec_from_file_location(
    "verify_distribution", ROOT / "scripts/verify_distribution.py"
)
assert SPEC is not None
verify_distribution = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(verify_distribution)
SIGNED_POLICY_SPEC = importlib.util.spec_from_file_location(
    "verify_signed_policy_example", ROOT / "scripts/verify_signed_policy_example.py"
)
assert SIGNED_POLICY_SPEC is not None
verify_signed_policy_example = importlib.util.module_from_spec(SIGNED_POLICY_SPEC)
assert SIGNED_POLICY_SPEC.loader is not None
SIGNED_POLICY_SPEC.loader.exec_module(verify_signed_policy_example)

REQUIRED_SCHEMA_FILES = verify_distribution.REQUIRED_SCHEMA_FILES
REQUIRED_BENCHMARK_RESULT_FILES = verify_distribution.REQUIRED_BENCHMARK_RESULT_FILES
REQUIRED_SOURCE_FILES = verify_distribution.REQUIRED_SOURCE_FILES
REQUIRED_ENTRY_POINTS = verify_distribution.REQUIRED_ENTRY_POINTS
REQUIRED_RUNTIME_DEPENDENCIES = verify_distribution.REQUIRED_RUNTIME_DEPENDENCIES
latest_sdist = verify_distribution.latest_sdist
latest_wheel = verify_distribution.latest_wheel
verify_sdist = verify_distribution.verify_sdist
verify_wheel = verify_distribution.verify_wheel


def write_wheel(
    path: Path,
    names: set[str],
    *,
    entry_points: bool = True,
    runtime_dependencies: bool = True,
) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name in sorted(names):
            archive.writestr(name, "{}\n")
        if entry_points:
            archive.writestr(
                "agentverify-0.1.0.dist-info/entry_points.txt",
                "[console_scripts]\nagentverify = agentverify.cli:main\n",
            )
        if runtime_dependencies:
            dependencies = "".join(
                f"Requires-Dist: {dependency}\n"
                for dependency in sorted(REQUIRED_RUNTIME_DEPENDENCIES)
            )
            archive.writestr("agentverify-0.1.0.dist-info/METADATA", dependencies)


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
    assert payload["required_schema_files"] == 15
    assert payload["missing_schema_files"] == []
    assert payload["present_schema_files"] == sorted(REQUIRED_SCHEMA_FILES)
    assert payload["console_scripts"] == REQUIRED_ENTRY_POINTS
    assert payload["missing_entry_points"] == {}
    assert set(payload["runtime_dependencies"]) >= REQUIRED_RUNTIME_DEPENDENCIES
    assert payload["missing_runtime_dependencies"] == []


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


def test_ci_workflow_verifies_checked_in_benchmark_results() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert (
        "agentverify benchmark verify --require-evaluation-kind public-regression "
        "--require-all-passed"
    ) in workflow


def test_ci_workflow_verifies_ephemeral_signed_policy_example() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "python scripts/verify_signed_policy_example.py" in workflow


def test_github_policy_gate_example_is_read_only_and_fail_closed() -> None:
    workflow = GITHUB_POLICY_GATE.read_text(encoding="utf-8")
    policy_docs = (ROOT / "docs/policy.md").read_text(encoding="utf-8")
    code_scanning_docs = (ROOT / "docs/code-scanning.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "permissions:\n  contents: read" in workflow
    assert "security-events: write" not in workflow
    assert "agentverify policy agentverify-policy.json" in workflow
    assert "--policy agentverify-policy.json" in workflow
    assert "--format summary" in workflow
    assert "--require-suppression-expiry" in workflow
    assert "python -m pip install agentverify==0.1.0" in workflow
    assert "[`examples/github-policy-gate.yml`](../examples/github-policy-gate.yml)" in policy_docs
    assert "[`examples/github-policy-gate.yml`](../examples/github-policy-gate.yml)" in code_scanning_docs
    assert "[`examples/github-policy-gate.yml`](examples/github-policy-gate.yml)" in readme


def test_github_code_scanning_example_uploads_sarif_without_policy_gate() -> None:
    workflow = GITHUB_CODE_SCANNING.read_text(encoding="utf-8")
    code_scanning_docs = (ROOT / "docs/code-scanning.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "permissions:\n  contents: read" in workflow
    assert "security-events: write" in workflow
    assert "agentverify scan . --format sarif --output agentverify.sarif" in workflow
    assert "github/codeql-action/upload-sarif@v4" in workflow
    assert "category: agentverify" in workflow
    assert "--policy" not in workflow
    assert "--fail-on" not in workflow
    assert "python -m pip install agentverify==0.1.0" in workflow
    assert "[`examples/github-code-scanning.yml`](../examples/github-code-scanning.yml)" in (
        code_scanning_docs
    )
    assert "[GitHub code-scanning workflow](examples/github-code-scanning.yml)" in readme


def test_github_benchmark_verify_example_is_read_only_and_exports_verifier_json() -> None:
    workflow = GITHUB_BENCHMARK_VERIFY.read_text(encoding="utf-8")
    release_checklist = (ROOT / "benchmarks/release-checklist.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    checked_example = (ROOT / "examples/benchmark-verification.json").read_text(encoding="utf-8")

    assert "permissions:\n  contents: read" in workflow
    assert "security-events: write" not in workflow
    assert "agentverify benchmark verify" in workflow
    assert "--require-evaluation-kind public-regression" in workflow
    assert "--require-all-passed" in workflow
    assert "--output agentverify-benchmark-verification.json" in workflow
    assert "agentverify schema benchmark-verification" in workflow
    assert "Draft202012Validator(schema).validate(payload)" in workflow
    assert "actions/upload-artifact@v5" in workflow
    assert "python -m pip install agentverify==0.1.0" in workflow
    assert "[`examples/github-benchmark-verify.yml`](../examples/github-benchmark-verify.yml)" in (
        release_checklist
    )
    assert "[`examples/github-benchmark-verify.yml`](examples/github-benchmark-verify.yml)" in readme
    assert "[`examples/benchmark-verification.json`](../examples/benchmark-verification.json)" in (
        release_checklist
    )
    assert "[`examples/benchmark-verification.json`](examples/benchmark-verification.json)" in readme
    assert "\"all_labels_passed\": true" in checked_example


def test_signed_policy_example_uses_ephemeral_key(tmp_path: Path) -> None:
    payload = verify_signed_policy_example.run_signed_policy_example(
        ROOT / "examples/repository-policy.json",
        agentverify_command=[sys.executable, "-m", "agentverify.cli"],
        work_dir=tmp_path,
        key_id="pytest-ephemeral",
    )

    assert payload["signature_verified"] is True
    assert payload["signature_trusted"] is True
    assert payload["verified_key_ids"] == ["pytest-ephemeral"]
    assert payload["private_key_material"] == "ephemeral-memory-only"
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "policy-key-trust-root.json",
        "policy-signature.json",
        "policy-signing-payload.json",
    ]
    assert not any("private" in path.name or "secret" in path.name for path in tmp_path.iterdir())


def test_distribution_verifier_rejects_missing_schema(tmp_path: Path) -> None:
    wheel = tmp_path / "agentverify-0.1.0-py3-none-any.whl"
    missing = {"agentverify/schemas/agentverify-rules-v1.schema.json"}
    write_wheel(wheel, set(REQUIRED_SCHEMA_FILES) - missing)

    with pytest.raises(RuntimeError, match="agentverify-rules-v1.schema.json"):
        verify_wheel(wheel)


def test_distribution_verifier_rejects_missing_runtime_dependency(tmp_path: Path) -> None:
    wheel = tmp_path / "agentverify-0.1.0-py3-none-any.whl"
    write_wheel(
        wheel,
        set(REQUIRED_SCHEMA_FILES) | {"agentverify/__init__.py"},
        runtime_dependencies=False,
    )

    with pytest.raises(RuntimeError, match="cryptography"):
        verify_wheel(wheel)


def test_distribution_verifier_rejects_missing_source_artifact(tmp_path: Path) -> None:
    sdist = tmp_path / "agentverify-0.1.0.tar.gz"
    missing = {"examples/repository-policy.json"}
    write_sdist(
        sdist, (set(REQUIRED_SOURCE_FILES) | set(REQUIRED_BENCHMARK_RESULT_FILES)) - missing
    )

    with pytest.raises(RuntimeError, match="examples/repository-policy.json"):
        verify_sdist(sdist)


def test_distribution_verifier_requires_holdout_label_template(tmp_path: Path) -> None:
    sdist = tmp_path / "agentverify-0.1.0.tar.gz"
    missing = {"benchmarks/holdout-labels.template.json"}
    write_sdist(
        sdist, (set(REQUIRED_SOURCE_FILES) | set(REQUIRED_BENCHMARK_RESULT_FILES)) - missing
    )

    with pytest.raises(RuntimeError, match="benchmarks/holdout-labels.template.json"):
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

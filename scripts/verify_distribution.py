"""Verify release distribution artifacts that AgentVerify depends on."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from pathlib import Path, PurePosixPath

REQUIRED_ENTRY_POINTS = {"agentverify": "agentverify.cli:main"}
REQUIRED_RUNTIME_DEPENDENCIES = {"cryptography>=46.0", "jsonschema>=4.23"}
REQUIRED_BENCHMARK_RESULT_FILES = frozenset(
    {
        "benchmarks/ir-truthset-results.json",
        "benchmarks/truthset-results.json",
    }
)
REQUIRED_SOURCE_FILES = frozenset(
    {
        ".pre-commit-hooks.yaml",
        "README.md",
        "pyproject.toml",
        "benchmarks/benchmark-results-v1.schema.json",
        "benchmarks/holdout-design.md",
        "benchmarks/holdout-manifest.template.json",
        "benchmarks/ir-truthset.json",
        "benchmarks/release-checklist.md",
        "benchmarks/truthset.json",
        "docs/code-scanning.md",
        "docs/editor-integration.md",
        "docs/pre-commit.md",
        "docs/policy.md",
        "docs/policy-signatures.md",
        "examples/ci-policy.json",
        "examples/editor-diagnostics.json",
        "examples/github-code-scanning.yml",
        "examples/github-policy-gate.yml",
        "examples/org-policy.json",
        "examples/policy-trust-root.json",
        "examples/pre-commit-config.yaml",
        "examples/repository-policy.json",
        "examples/safe_agent/agent.py",
        "scripts/export_editor_contracts.py",
        "scripts/verify_signed_policy_example.py",
    }
)
REQUIRED_SCHEMA_FILES = frozenset(
    {
        "agentverify/schemas/agentverify-benchmark-result-v1.schema.json",
        "agentverify/schemas/agentverify-ai-bom-v1.schema.json",
        "agentverify/schemas/agentverify-policy-key-trust-root-v1.schema.json",
        "agentverify/schemas/agentverify-policy-signature-v1.schema.json",
        "agentverify/schemas/agentverify-policy-signing-payload-v1.schema.json",
        "agentverify/schemas/agentverify-policy-v1.schema.json",
        "agentverify/schemas/agentverify-policy-summary-v1.schema.json",
        "agentverify/schemas/agentverify-policy-trust-root-v1.schema.json",
        "agentverify/schemas/agentverify-report-v1.schema.json",
        "agentverify/schemas/agentverify-rules-v1.schema.json",
    }
)


def latest_wheel(dist_dir: Path) -> Path:
    wheels = sorted(dist_dir.glob("agentverify-*.whl"), key=lambda path: path.stat().st_mtime)
    if not wheels:
        raise FileNotFoundError(f"no agentverify wheel found in {dist_dir}")
    return wheels[-1]


def latest_sdist(dist_dir: Path) -> Path:
    sdists = sorted(dist_dir.glob("agentverify-*.tar.gz"), key=lambda path: path.stat().st_mtime)
    if not sdists:
        raise FileNotFoundError(f"no agentverify source distribution found in {dist_dir}")
    return sdists[-1]


def wheel_names(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return set(archive.namelist())


def sdist_source_names(path: Path) -> set[str]:
    with tarfile.open(path, "r:gz") as archive:
        raw_names = [member.name for member in archive.getmembers() if member.isfile()]
    names: set[str] = set()
    for raw_name in raw_names:
        parts = PurePosixPath(raw_name).parts
        if len(parts) > 1:
            names.add(PurePosixPath(*parts[1:]).as_posix())
        else:
            names.add(raw_name)
    return names


def entry_points(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        candidates = [
            name for name in archive.namelist() if name.endswith(".dist-info/entry_points.txt")
        ]
        if not candidates:
            return {}
        content = archive.read(candidates[0]).decode("utf-8")
    section = None
    values: dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if section == "console_scripts" and "=" in line:
            name, target = line.split("=", 1)
            values[name.strip()] = target.strip()
    return values


def requires_dist(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        candidates = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if not candidates:
            return set()
        content = archive.read(candidates[0]).decode("utf-8")
    values = set()
    for raw_line in content.splitlines():
        if raw_line.startswith("Requires-Dist:"):
            values.add(raw_line.partition(":")[2].strip())
    return values


def command(argv: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(argv, cwd=cwd, check=True, text=True, capture_output=True)
    return completed.stdout


def script_path(venv_dir: Path, name: str) -> Path:
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    suffix = ".exe" if sys.platform == "win32" else ""
    return venv_dir / scripts / f"{name}{suffix}"


def smoke_install(path: Path, source_root: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="agentverify-wheel-") as raw_dir:
        venv_dir = Path(raw_dir) / "venv"
        generated_trust_root = Path(raw_dir) / "generated-policy-trust-root.json"
        editor_contracts_dir = Path(raw_dir) / "editor-contracts"
        venv.EnvBuilder(with_pip=True).create(venv_dir)
        python = script_path(venv_dir, "python")
        command([str(python), "-m", "pip", "install", str(path)])
        agentverify = script_path(venv_dir, "agentverify")
        version = command([str(agentverify), "--version"]).strip()
        schema_list = command([str(agentverify), "schema"]).splitlines()
        benchmark_schema = json.loads(command([str(agentverify), "schema", "benchmark-result"]))
        report_schema = json.loads(command([str(agentverify), "schema", "report"]))
        rules_schema = json.loads(command([str(agentverify), "schema", "rules"]))
        policy_key_trust_root_schema = json.loads(
            command([str(agentverify), "schema", "policy-key-trust-root"])
        )
        policy_signature_schema = json.loads(
            command([str(agentverify), "schema", "policy-signature"])
        )
        policy_summary_schema = json.loads(command([str(agentverify), "schema", "policy-summary"]))
        policy_signing_payload_schema = json.loads(
            command([str(agentverify), "schema", "policy-signing-payload"])
        )
        policy_trust_root_schema = json.loads(
            command([str(agentverify), "schema", "policy-trust-root"])
        )
        benchmark_verification = json.loads(
            command(
                [
                    str(agentverify),
                    "benchmark",
                    "verify",
                    str(source_root / "benchmarks/truthset-results.json"),
                    str(source_root / "benchmarks/ir-truthset-results.json"),
                    "--root",
                    str(source_root),
                    "--require-evaluation-kind",
                    "public-regression",
                    "--require-all-passed",
                ]
            )
        )
        editor_contracts = json.loads(
            command(
                [
                    str(agentverify),
                    "contracts",
                    "--output-dir",
                    str(editor_contracts_dir),
                    "--sample-root",
                    str(source_root / "examples/safe_agent"),
                ]
            )
        )
        policy_signing_payload = json.loads(
            command(
                [
                    str(agentverify),
                    "policy",
                    str(source_root / "examples/repository-policy.json"),
                    "--export-signing-payload",
                ]
            )
        )
        signed_policy_example = json.loads(
            command(
                [
                    str(python),
                    str(source_root / "scripts/verify_signed_policy_example.py"),
                    "--agentverify",
                    str(agentverify),
                    "--policy",
                    str(source_root / "examples/repository-policy.json"),
                    "--key-id",
                    "installed-wheel-smoke",
                ]
            )
        )
        policy_summary = json.loads(
            command(
                [
                    str(agentverify),
                    "policy",
                    str(source_root / "examples/repository-policy.json"),
                    "--format",
                    "json",
                ]
            )
        )
        command(
            [
                str(agentverify),
                "policy",
                str(source_root / "examples/repository-policy.json"),
                "--export-trust-root",
                "--output",
                str(generated_trust_root),
            ]
        )
        generated_trusted_policy_summary = json.loads(
            command(
                [
                    str(agentverify),
                    "policy",
                    str(source_root / "examples/repository-policy.json"),
                    "--trust-root",
                    str(generated_trust_root),
                    "--require-trusted",
                    "--format",
                    "json",
                ]
            )
        )
        trusted_policy_summary = json.loads(
            command(
                [
                    str(agentverify),
                    "policy",
                    str(source_root / "examples/repository-policy.json"),
                    "--trust-root",
                    str(source_root / "examples/policy-trust-root.json"),
                    "--require-trusted",
                    "--format",
                    "json",
                ]
            )
        )
        summary = command(
            [
                str(agentverify),
                "scan",
                str(source_root / "examples/safe_agent"),
                "--format",
                "summary",
            ]
        )
        editor_contract_files_present = sorted(
            path.name for path in editor_contracts_dir.iterdir() if path.is_file()
        )
    checks = {
        "version": version,
        "schema_list": schema_list,
        "benchmark_schema_title": benchmark_schema.get("title"),
        "report_schema_title": report_schema.get("title"),
        "rules_schema_title": rules_schema.get("title"),
        "policy_key_trust_root_schema_title": policy_key_trust_root_schema.get("title"),
        "policy_signature_schema_title": policy_signature_schema.get("title"),
        "policy_summary_schema_title": policy_summary_schema.get("title"),
        "policy_signing_payload_schema_title": policy_signing_payload_schema.get("title"),
        "policy_trust_root_schema_title": policy_trust_root_schema.get("title"),
        "policy_signing_payload_format": policy_signing_payload.get(
            "policy_signing_payload_format"
        ),
        "policy_signing_payload_sources": [
            item.get("source") for item in policy_signing_payload.get("policy_set", [])
        ],
        "policy_summary_format": policy_summary.get("policy_format"),
        "policy_signature_verified": policy_summary.get("trust", {}).get("signature_verified"),
        "benchmark_verification_passed": benchmark_verification.get("passed"),
        "benchmark_verification_labels": [
            item.get("labels") for item in benchmark_verification.get("results", [])
        ],
        "editor_contract_artifacts": [
            item.get("path") for item in editor_contracts.get("artifacts", [])
        ],
        "editor_contract_files_present": editor_contract_files_present,
        "signed_policy_signature_verified": signed_policy_example.get("signature_verified"),
        "signed_policy_signature_trusted": signed_policy_example.get("signature_trusted"),
        "signed_policy_private_key_material": signed_policy_example.get("private_key_material"),
        "generated_policy_trust_root_trusted": generated_trusted_policy_summary.get("trust", {})
        .get("trust_root", {})
        .get("trusted"),
        "policy_trust_root_trusted": trusted_policy_summary.get("trust", {})
        .get("trust_root", {})
        .get("trusted"),
        "safe_agent_summary": "AgentVerify Summary" in summary and "No findings" in summary,
    }
    failed = []
    if not version.startswith("agentverify "):
        failed.append("version")
    expected_schema_names = [
        "benchmark-result",
        "bom",
        "policy",
        "policy-key-trust-root",
        "policy-signature",
        "policy-signing-payload",
        "policy-summary",
        "policy-trust-root",
        "report",
        "rules",
    ]
    if schema_list != expected_schema_names:
        failed.append("schema_list")
    if benchmark_schema.get("title") != "AgentVerify Benchmark Results 1":
        failed.append("benchmark_schema_title")
    if report_schema.get("title") != "AgentVerify JSON Report 1":
        failed.append("report_schema_title")
    if rules_schema.get("title") != "AgentVerify Rules Catalog 1":
        failed.append("rules_schema_title")
    if policy_key_trust_root_schema.get("title") != "AgentVerify Policy Key Trust Root 1":
        failed.append("policy_key_trust_root_schema_title")
    if policy_signature_schema.get("title") != "AgentVerify Policy Signature 1":
        failed.append("policy_signature_schema_title")
    if policy_summary_schema.get("title") != "AgentVerify Policy Summary 1":
        failed.append("policy_summary_schema_title")
    if policy_signing_payload_schema.get("title") != "AgentVerify Policy Signing Payload 1":
        failed.append("policy_signing_payload_schema_title")
    if policy_trust_root_schema.get("title") != "AgentVerify Policy Trust Root 1":
        failed.append("policy_trust_root_schema_title")
    if (
        policy_signing_payload.get("policy_signing_payload_format")
        != "AgentVerify Policy Signing Payload"
    ):
        failed.append("policy_signing_payload_format")
    if checks["policy_signing_payload_sources"] != ["org-policy.json", "repository-policy.json"]:
        failed.append("policy_signing_payload_sources")
    if policy_summary.get("policy_format") != "AgentVerify Policy Summary":
        failed.append("policy_summary_format")
    if policy_summary.get("trust", {}).get("signature_verified") is not False:
        failed.append("policy_signature_verified")
    if checks["benchmark_verification_passed"] is not True:
        failed.append("benchmark_verification_passed")
    if checks["benchmark_verification_labels"] != [714, 1554]:
        failed.append("benchmark_verification_labels")
    expected_editor_contract_files = [
        "agentverify-report-v1.schema.json",
        "agentverify-rules-v1.schema.json",
        "agentverify-rules.json",
        "agentverify-sample-report.json",
    ]
    if checks["editor_contract_artifacts"] != expected_editor_contract_files:
        failed.append("editor_contract_artifacts")
    if checks["editor_contract_files_present"] != sorted(
        [*expected_editor_contract_files, "manifest.json"]
    ):
        failed.append("editor_contract_files_present")
    if checks["signed_policy_signature_verified"] is not True:
        failed.append("signed_policy_signature_verified")
    if checks["signed_policy_signature_trusted"] is not True:
        failed.append("signed_policy_signature_trusted")
    if checks["signed_policy_private_key_material"] != "ephemeral-memory-only":
        failed.append("signed_policy_private_key_material")
    if checks["generated_policy_trust_root_trusted"] is not True:
        failed.append("generated_policy_trust_root_trusted")
    if checks["policy_trust_root_trusted"] is not True:
        failed.append("policy_trust_root_trusted")
    if not checks["safe_agent_summary"]:
        failed.append("safe_agent_summary")
    if failed:
        raise RuntimeError(
            json.dumps(
                {"wheel": str(path), "failed_smoke_checks": failed, "smoke_checks": checks},
                indent=2,
            )
        )
    return checks


def verify_wheel(
    path: Path, *, smoke: bool = False, source_root: Path = Path(".")
) -> dict[str, object]:
    names = wheel_names(path)
    console_scripts = entry_points(path)
    dependencies = requires_dist(path)
    missing = sorted(REQUIRED_SCHEMA_FILES - names)
    missing_dependencies = sorted(REQUIRED_RUNTIME_DEPENDENCIES - dependencies)
    missing_entry_points = {
        name: target
        for name, target in REQUIRED_ENTRY_POINTS.items()
        if console_scripts.get(name) != target
    }
    present = sorted(REQUIRED_SCHEMA_FILES & names)
    payload: dict[str, object] = {
        "wheel": str(path),
        "required_schema_files": len(REQUIRED_SCHEMA_FILES),
        "present_schema_files": present,
        "missing_schema_files": missing,
        "console_scripts": console_scripts,
        "missing_entry_points": missing_entry_points,
        "runtime_dependencies": sorted(dependencies),
        "missing_runtime_dependencies": missing_dependencies,
        "passed": not missing and not missing_entry_points and not missing_dependencies,
    }
    if missing or missing_entry_points or missing_dependencies:
        raise RuntimeError(json.dumps(payload, indent=2))
    if smoke:
        payload["smoke_install"] = smoke_install(path, source_root)
    return payload


def verify_sdist(path: Path) -> dict[str, object]:
    names = sdist_source_names(path)
    required = REQUIRED_SOURCE_FILES | REQUIRED_BENCHMARK_RESULT_FILES
    missing = sorted(required - names)
    present = sorted(required & names)
    missing_benchmark_results = sorted(REQUIRED_BENCHMARK_RESULT_FILES - names)
    present_benchmark_results = sorted(REQUIRED_BENCHMARK_RESULT_FILES & names)
    payload: dict[str, object] = {
        "sdist": str(path),
        "required_source_files": len(required),
        "present_source_files": present,
        "missing_source_files": missing,
        "required_benchmark_result_files": len(REQUIRED_BENCHMARK_RESULT_FILES),
        "present_benchmark_result_files": present_benchmark_results,
        "missing_benchmark_result_files": missing_benchmark_results,
        "passed": not missing,
    }
    if missing:
        raise RuntimeError(json.dumps(payload, indent=2))
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that AgentVerify distribution artifacts contain required contracts."
    )
    parser.add_argument(
        "wheel",
        nargs="?",
        type=Path,
        help="wheel to inspect; defaults to the newest agentverify wheel in --dist-dir",
    )
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    parser.add_argument(
        "--smoke-install",
        action="store_true",
        help="install the wheel into a temporary virtualenv and run the console script",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path("."),
        help="source checkout root used by --smoke-install for example scans",
    )
    parser.add_argument(
        "--require-sdist",
        action="store_true",
        help="also verify that a source distribution contains documented examples and benchmarks",
    )
    parser.add_argument(
        "--sdist",
        type=Path,
        help="source distribution to inspect when --require-sdist is set; defaults to newest in --dist-dir",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        wheel = args.wheel if args.wheel is not None else latest_wheel(args.dist_dir)
        payload = verify_wheel(wheel, smoke=args.smoke_install, source_root=args.source_root)
        if args.require_sdist:
            sdist = args.sdist if args.sdist is not None else latest_sdist(args.dist_dir)
            payload["source_distribution"] = verify_sdist(sdist)
    except (
        FileNotFoundError,
        RuntimeError,
        subprocess.CalledProcessError,
        tarfile.TarError,
        zipfile.BadZipFile,
    ) as error:
        print(f"agentverify distribution verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2) + "\n", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Verify release wheel contents that AgentVerify depends on at runtime."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

REQUIRED_ENTRY_POINTS = {"agentverify": "agentverify.cli:main"}
REQUIRED_SCHEMA_FILES = frozenset(
    {
        "agentverify/schemas/agentverify-benchmark-result-v1.schema.json",
        "agentverify/schemas/agentverify-ai-bom-v1.schema.json",
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


def wheel_names(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return set(archive.namelist())


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
        venv.EnvBuilder(with_pip=True).create(venv_dir)
        python = script_path(venv_dir, "python")
        command([str(python), "-m", "pip", "install", "--no-deps", str(path)])
        agentverify = script_path(venv_dir, "agentverify")
        version = command([str(agentverify), "--version"]).strip()
        benchmark_schema = json.loads(command([str(agentverify), "schema", "benchmark-result"]))
        report_schema = json.loads(command([str(agentverify), "schema", "report"]))
        rules_schema = json.loads(command([str(agentverify), "schema", "rules"]))
        policy_summary_schema = json.loads(command([str(agentverify), "schema", "policy-summary"]))
        policy_trust_root_schema = json.loads(
            command([str(agentverify), "schema", "policy-trust-root"])
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
    checks = {
        "version": version,
        "benchmark_schema_title": benchmark_schema.get("title"),
        "report_schema_title": report_schema.get("title"),
        "rules_schema_title": rules_schema.get("title"),
        "policy_summary_schema_title": policy_summary_schema.get("title"),
        "policy_trust_root_schema_title": policy_trust_root_schema.get("title"),
        "policy_summary_format": policy_summary.get("policy_format"),
        "policy_signature_verified": policy_summary.get("trust", {}).get("signature_verified"),
        "policy_trust_root_trusted": trusted_policy_summary.get("trust", {})
        .get("trust_root", {})
        .get("trusted"),
        "safe_agent_summary": "AgentVerify Summary" in summary and "No findings" in summary,
    }
    failed = []
    if not version.startswith("agentverify "):
        failed.append("version")
    if benchmark_schema.get("title") != "AgentVerify Benchmark Results 1":
        failed.append("benchmark_schema_title")
    if report_schema.get("title") != "AgentVerify JSON Report 1":
        failed.append("report_schema_title")
    if rules_schema.get("title") != "AgentVerify Rules Catalog 1":
        failed.append("rules_schema_title")
    if policy_summary_schema.get("title") != "AgentVerify Policy Summary 1":
        failed.append("policy_summary_schema_title")
    if policy_trust_root_schema.get("title") != "AgentVerify Policy Trust Root 1":
        failed.append("policy_trust_root_schema_title")
    if policy_summary.get("policy_format") != "AgentVerify Policy Summary":
        failed.append("policy_summary_format")
    if policy_summary.get("trust", {}).get("signature_verified") is not False:
        failed.append("policy_signature_verified")
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
    missing = sorted(REQUIRED_SCHEMA_FILES - names)
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
        "passed": not missing and not missing_entry_points,
    }
    if missing or missing_entry_points:
        raise RuntimeError(json.dumps(payload, indent=2))
    if smoke:
        payload["smoke_install"] = smoke_install(path, source_root)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that an AgentVerify wheel contains required runtime schemas."
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        wheel = args.wheel if args.wheel is not None else latest_wheel(args.dist_dir)
        payload = verify_wheel(wheel, smoke=args.smoke_install, source_root=args.source_root)
    except (
        FileNotFoundError,
        RuntimeError,
        subprocess.CalledProcessError,
        zipfile.BadZipFile,
    ) as error:
        print(f"agentverify distribution verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2) + "\n", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

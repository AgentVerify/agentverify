"""Scan two fixtures and verify the reports and CI gates without running target code."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cases = (
        ("Dynamic shell command", "cases/python_dangerous", ["AV-EXEC001"], 1),
        ("Fixed argv comparison", "examples/safe_agent", [], 0),
    )
    for title, path, expected_rules, expected_exit in cases:
        print(f"\n{title}\n$ agentverify scan {path} --format summary", flush=True)
        command = [sys.executable, "-m", "agentverify", "scan", str(ROOT / path)]
        subprocess.run(command + ["--format", "summary"], check=True, timeout=30)
        result = subprocess.run(
            command + ["--format", "json", "--fail-on", "high"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != expected_exit:
            raise RuntimeError(f"{path}: unexpected exit {result.returncode}: {result.stderr}")
        report = json.loads(result.stdout)
        observed = sorted(finding["rule_id"] for finding in report["findings"])
        if observed != expected_rules:
            raise RuntimeError(f"{path}: expected {expected_rules}, got {observed}")
        print(f"Verified: expected findings and --fail-on high exit code {expected_exit}.")
    print("\nDemo passed. Scan your project with: agentverify scan /path/to/project --format summary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

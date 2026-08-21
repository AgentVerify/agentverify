"""Schema-aligned policy loading and non-hiding gate evaluation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .ir import RepositoryIR

SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3}
RESULT_KINDS = {"finding", "review"}


class PolicyError(ValueError):
    """Raised when a policy document does not satisfy the supported contract."""


def _string_list(value: object, field: str, *, allowed: set[str] | None = None) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise PolicyError(f"{field} must be a non-empty string array")
    items = list(dict.fromkeys(item.strip() for item in value))
    if allowed is not None and not set(items) <= allowed:
        invalid = sorted(set(items) - allowed)
        raise PolicyError(f"{field} contains unsupported values: {', '.join(invalid)}")
    return items


def normalize_policy(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PolicyError("policy must be a JSON object")
    unknown = set(payload) - {"schema_version", "name", "gates"}
    if unknown:
        raise PolicyError(f"unknown policy fields: {', '.join(sorted(unknown))}")
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise PolicyError("schema_version must be 1")
    name = payload.get("name", "unnamed")
    if not isinstance(name, str) or not name.strip():
        raise PolicyError("name must be a non-empty string")
    name = name.strip()
    raw_gates = payload.get("gates")
    if not isinstance(raw_gates, list) or not raw_gates:
        raise PolicyError("gates must be a non-empty array")

    gates = []
    gate_ids = set()
    for index, raw_gate in enumerate(raw_gates):
        field = f"gates[{index}]"
        if not isinstance(raw_gate, dict):
            raise PolicyError(f"{field} must be an object")
        unknown_gate = set(raw_gate) - {
            "id",
            "rules",
            "result_kinds",
            "min_severity",
            "max_count",
        }
        if unknown_gate:
            raise PolicyError(f"{field} has unknown fields: {', '.join(sorted(unknown_gate))}")
        gate_id = raw_gate.get("id")
        if not isinstance(gate_id, str) or not gate_id.strip():
            raise PolicyError(f"{field}.id must be a non-empty string")
        gate_id = gate_id.strip()
        if gate_id in gate_ids:
            raise PolicyError(f"duplicate gate id: {gate_id}")
        gate_ids.add(gate_id)
        minimum = raw_gate.get("min_severity", "high")
        if not isinstance(minimum, str) or minimum not in SEVERITY_RANK:
            raise PolicyError(f"{field}.min_severity must be info, low, medium, or high")
        maximum = raw_gate.get("max_count")
        if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 0:
            raise PolicyError(f"{field}.max_count must be a non-negative integer")
        rules = _string_list(raw_gate["rules"], f"{field}.rules") if "rules" in raw_gate else []
        result_kinds = (
            _string_list(raw_gate["result_kinds"], f"{field}.result_kinds", allowed=RESULT_KINDS)
            if "result_kinds" in raw_gate
            else ["finding"]
        )
        gates.append(
            {
                "id": gate_id,
                "rules": rules,
                "result_kinds": result_kinds,
                "min_severity": minimum,
                "max_count": maximum,
            }
        )
    return {"schema_version": 1, "name": name, "gates": gates}


def load_policy(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PolicyError(f"invalid JSON: {error}") from error
    return normalize_policy(payload), hashlib.sha256(raw).hexdigest()


def evaluate_policy(ir: RepositoryIR, policy: dict[str, Any], *, source: str, digest: str) -> bool:
    gate_results = []
    for gate in policy["gates"]:
        minimum = SEVERITY_RANK[gate["min_severity"]]
        matches = [
            finding
            for finding in ir.findings
            if (not gate["rules"] or finding.rule_id in gate["rules"])
            and finding.result_kind in gate["result_kinds"]
            and SEVERITY_RANK.get(finding.severity, 0) >= minimum
        ]
        passed = len(matches) <= gate["max_count"]
        gate_results.append(
            {
                **gate,
                "matched_count": len(matches),
                "matched_fingerprints": sorted(finding.fingerprint for finding in matches),
                "passed": passed,
            }
        )
    passed = all(gate["passed"] for gate in gate_results)
    ir.policy_summary = {
        "name": policy["name"],
        "source": source,
        "sha256": digest,
        "evaluated_after_baseline": True,
        "passed": passed,
        "gates": gate_results,
    }
    return passed

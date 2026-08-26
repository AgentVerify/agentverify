"""Schema-aligned policy loading and non-hiding gate evaluation."""

from __future__ import annotations

import hashlib
import json
import posixpath
from collections import Counter
from pathlib import Path
from typing import Any

from .ir import Finding, RepositoryIR
from .rules import REPORTING_RULE_IDS, RULE_CATALOG

SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3}
RESULT_KINDS = {"finding", "review"}
MAX_POLICY_DEPTH = 32


class PolicyError(ValueError):
    """Raised when a policy document does not satisfy the supported contract."""


def _matched_summary(matches: list[Finding]) -> dict[str, dict[str, int]]:
    return {
        "by_result_kind": dict(sorted(Counter(finding.result_kind for finding in matches).items())),
        "by_rule": dict(sorted(Counter(finding.rule_id for finding in matches).items())),
        "by_severity": dict(sorted(Counter(finding.severity for finding in matches).items())),
    }


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
    unknown = set(payload) - {"schema_version", "name", "extends", "gates"}
    if unknown:
        raise PolicyError(f"unknown policy fields: {', '.join(sorted(unknown))}")
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise PolicyError("schema_version must be 1")
    name = payload.get("name", "unnamed")
    if not isinstance(name, str) or not name.strip():
        raise PolicyError("name must be a non-empty string")
    name = name.strip()
    extends = _string_list(payload["extends"], "extends") if "extends" in payload else []
    raw_gates = payload.get("gates", [])
    if not isinstance(raw_gates, list) or ("gates" in payload and not raw_gates):
        raise PolicyError("gates must be a non-empty array")
    if not extends and not raw_gates:
        raise PolicyError("policy must define extends or gates")

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
        rules = (
            _string_list(
                raw_gate["rules"],
                f"{field}.rules",
                allowed=REPORTING_RULE_IDS,
            )
            if "rules" in raw_gate
            else []
        )
        result_kinds = (
            _string_list(raw_gate["result_kinds"], f"{field}.result_kinds", allowed=RESULT_KINDS)
            if "result_kinds" in raw_gate
            else ["finding"]
        )
        excluded_by_kind = [
            rule_id for rule_id in rules if RULE_CATALOG[rule_id].result_kind not in result_kinds
        ]
        if excluded_by_kind:
            details = ", ".join(
                f"{rule_id} emits {RULE_CATALOG[rule_id].result_kind}"
                for rule_id in excluded_by_kind
            )
            raise PolicyError(f"{field}.rules cannot match {field}.result_kinds: {details}")
        excluded_by_severity = [
            rule_id
            for rule_id in rules
            if SEVERITY_RANK[RULE_CATALOG[rule_id].severity] < SEVERITY_RANK[minimum]
        ]
        if excluded_by_severity:
            details = ", ".join(
                f"{rule_id} emits {RULE_CATALOG[rule_id].severity}"
                for rule_id in excluded_by_severity
            )
            raise PolicyError(
                f"{field}.rules cannot meet {field}.min_severity {minimum}: {details}"
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
    normalized = {"schema_version": 1, "name": name, "gates": gates}
    if extends:
        normalized["extends"] = extends
    return normalized


def load_policy(path: Path) -> tuple[dict[str, Any], str]:
    root = path.resolve()
    display_root = root.parent
    loaded: set[Path] = set()
    stack: list[Path] = []
    sources: list[dict[str, str]] = []
    gates: list[dict[str, Any]] = []
    gate_sources: dict[str, str] = {}
    root_policy: dict[str, Any] | None = None
    root_digest = ""

    def display_name(policy_path: Path) -> str:
        try:
            return policy_path.relative_to(display_root).as_posix()
        except ValueError:
            return posixpath.relpath(policy_path.as_posix(), display_root.as_posix())

    def visit(policy_path: Path, depth: int) -> None:
        nonlocal root_policy, root_digest
        resolved = policy_path.resolve()
        source = display_name(resolved)
        if resolved in stack:
            cycle = " -> ".join(display_name(item) for item in [*stack, resolved])
            raise PolicyError(f"policy composition cycle: {cycle}")
        if resolved in loaded:
            return
        if depth >= MAX_POLICY_DEPTH:
            raise PolicyError(f"policy composition exceeds {MAX_POLICY_DEPTH} levels at {source}")
        try:
            raw = resolved.read_bytes()
        except OSError as error:
            raise PolicyError(f"cannot read {source}: {error}") from error
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PolicyError(f"invalid JSON in {source}: {error}") from error
        try:
            normalized = normalize_policy(payload)
        except PolicyError as error:
            raise PolicyError(f"{source}: {error}") from error
        digest = hashlib.sha256(raw).hexdigest()
        if resolved == root:
            root_policy = normalized
            root_digest = digest

        stack.append(resolved)
        for reference in normalized.get("extends", []):
            candidate = Path(reference)
            if candidate.is_absolute() or "://" in reference:
                raise PolicyError(f"{source}: extends entries must be relative local paths")
            visit(resolved.parent / candidate, depth + 1)
        stack.pop()

        for gate in normalized["gates"]:
            gate_id = gate["id"]
            if gate_id in gate_sources:
                raise PolicyError(
                    f"duplicate gate id {gate_id}: {gate_sources[gate_id]} and {source}"
                )
            gate_sources[gate_id] = source
            gates.append({**gate, "_policy_source": source, "_policy_sha256": digest})
        loaded.add(resolved)
        sources.append({"source": source, "sha256": digest})

    visit(root, 0)
    if root_policy is None:  # pragma: no cover - the root visit either loads or raises
        raise PolicyError("root policy was not loaded")
    return {
        "schema_version": 1,
        "name": root_policy["name"],
        "gates": gates,
        "_sources": sources,
    }, root_digest


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
                **{key: value for key, value in gate.items() if not key.startswith("_")},
                "policy_source": gate.get("_policy_source", source),
                "policy_sha256": gate.get("_policy_sha256", digest),
                "matched_count": len(matches),
                "matched_summary": _matched_summary(matches),
                "matched_fingerprints": sorted(finding.fingerprint for finding in matches),
                "passed": passed,
            }
        )
    passed = all(gate["passed"] for gate in gate_results)
    ir.policy_summary = {
        "name": policy["name"],
        "source": source,
        "sha256": digest,
        "sources": policy.get("_sources", [{"source": source, "sha256": digest}]),
        "evaluated_after_baseline": True,
        "passed": passed,
        "gates": gate_results,
    }
    return passed

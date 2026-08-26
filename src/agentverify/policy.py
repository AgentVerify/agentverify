"""Schema-aligned policy loading and non-hiding gate evaluation."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import posixpath
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from .ir import Finding, RepositoryIR
from .rules import REPORTING_RULE_IDS, RULE_CATALOG

SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3}
RESULT_KINDS = {"finding", "review"}
MAX_POLICY_DEPTH = 32
TRUST_MODEL = "local-content-digest-allowlist"
SIGNATURE_TRUST_MODEL = "local-key-signature"
POLICY_SIGNATURE_FORMAT = "agentverify-policy-signature"
POLICY_SIGNING_PAYLOAD_FORMAT = "AgentVerify Policy Signing Payload"
POLICY_SIGNATURE_ALGORITHM = "ed25519"


class PolicyError(ValueError):
    """Raised when a policy document does not satisfy the supported contract."""


def _sha256_hexdigest(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PolicyError(f"{field} must be a non-empty string")
    digest = value.strip()
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise PolicyError(f"{field} must be a lowercase SHA-256 hex digest")
    return digest


def _base64_bytes(value: object, field: str, *, expected_length: int) -> bytes:
    if not isinstance(value, str) or not value.strip():
        raise PolicyError(f"{field} must be a non-empty base64 string")
    try:
        decoded = base64.b64decode(value.strip(), validate=True)
    except (binascii.Error, ValueError) as error:
        raise PolicyError(f"{field} must be valid base64") from error
    if len(decoded) != expected_length:
        raise PolicyError(f"{field} must decode to {expected_length} bytes")
    return decoded


def _datetime(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise PolicyError(f"{field} must be a non-empty date-time string")
    raw = value.strip()
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise PolicyError(f"{field} must be an RFC3339 date-time") from error
    if parsed.tzinfo is None:
        raise PolicyError(f"{field} must include a timezone")
    return parsed


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


def normalize_policy_trust_root(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PolicyError("policy trust root must be a JSON object")
    unknown = set(payload) - {"schema_version", "trust_model", "policies"}
    if unknown:
        raise PolicyError(f"unknown policy trust root fields: {', '.join(sorted(unknown))}")
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise PolicyError("schema_version must be 1")
    if payload.get("trust_model") != TRUST_MODEL:
        raise PolicyError(f"trust_model must be {TRUST_MODEL}")
    policies = payload.get("policies")
    if not isinstance(policies, list) or not policies:
        raise PolicyError("policies must be a non-empty array")
    normalized = []
    seen = set()
    for index, item in enumerate(policies):
        field = f"policies[{index}]"
        if not isinstance(item, dict):
            raise PolicyError(f"{field} must be an object")
        unknown_item = set(item) - {"source", "sha256"}
        if unknown_item:
            raise PolicyError(f"{field} has unknown fields: {', '.join(sorted(unknown_item))}")
        source = item.get("source")
        digest = item.get("sha256")
        if not isinstance(source, str) or not source.strip():
            raise PolicyError(f"{field}.source must be a non-empty string")
        source = source.strip()
        digest = _sha256_hexdigest(digest, f"{field}.sha256")
        if source in seen:
            raise PolicyError(f"duplicate trusted policy source: {source}")
        seen.add(source)
        normalized.append({"source": source, "sha256": digest})
    return {"schema_version": 1, "trust_model": TRUST_MODEL, "policies": normalized}


def normalize_policy_signing_payload(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PolicyError("policy signing payload must be a JSON object")
    unknown = set(payload) - {
        "policy_signing_payload_format",
        "schema_version",
        "root_source",
        "root_sha256",
        "policy_set",
    }
    if unknown:
        raise PolicyError(f"unknown policy signing payload fields: {', '.join(sorted(unknown))}")
    if payload.get("policy_signing_payload_format") != POLICY_SIGNING_PAYLOAD_FORMAT:
        raise PolicyError(f"policy_signing_payload_format must be {POLICY_SIGNING_PAYLOAD_FORMAT}")
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise PolicyError("schema_version must be 1")
    root_source = payload.get("root_source")
    if not isinstance(root_source, str) or not root_source.strip():
        raise PolicyError("root_source must be a non-empty string")
    root_source = root_source.strip()
    root_digest = _sha256_hexdigest(payload.get("root_sha256"), "root_sha256")
    policy_set = payload.get("policy_set")
    if not isinstance(policy_set, list) or not policy_set:
        raise PolicyError("policy_set must be a non-empty array")
    normalized_sources = []
    seen = set()
    for index, item in enumerate(policy_set):
        field = f"policy_set[{index}]"
        if not isinstance(item, dict):
            raise PolicyError(f"{field} must be an object")
        unknown_item = set(item) - {"source", "sha256"}
        if unknown_item:
            raise PolicyError(f"{field} has unknown fields: {', '.join(sorted(unknown_item))}")
        source = item.get("source")
        if not isinstance(source, str) or not source.strip():
            raise PolicyError(f"{field}.source must be a non-empty string")
        source = source.strip()
        digest = _sha256_hexdigest(item.get("sha256"), f"{field}.sha256")
        if source in seen:
            raise PolicyError(f"duplicate signed policy source: {source}")
        seen.add(source)
        normalized_sources.append({"source": source, "sha256": digest})
    if root_source not in seen:
        raise PolicyError("root_source must appear in policy_set")
    root_matches = [
        item
        for item in normalized_sources
        if item["source"] == root_source and item["sha256"] == root_digest
    ]
    if not root_matches:
        raise PolicyError("root_sha256 must match the root_source policy_set digest")
    return {
        "policy_signing_payload_format": POLICY_SIGNING_PAYLOAD_FORMAT,
        "schema_version": 1,
        "root_source": root_source,
        "root_sha256": root_digest,
        "policy_set": normalized_sources,
    }


def normalize_policy_key_trust_root(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PolicyError("policy key trust root must be a JSON object")
    unknown = set(payload) - {"schema_version", "trust_model", "keys"}
    if unknown:
        raise PolicyError(f"unknown policy key trust root fields: {', '.join(sorted(unknown))}")
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise PolicyError("schema_version must be 1")
    if payload.get("trust_model") != SIGNATURE_TRUST_MODEL:
        raise PolicyError(f"trust_model must be {SIGNATURE_TRUST_MODEL}")
    keys = payload.get("keys")
    if not isinstance(keys, list) or not keys:
        raise PolicyError("keys must be a non-empty array")
    normalized = []
    seen = set()
    for index, item in enumerate(keys):
        field = f"keys[{index}]"
        if not isinstance(item, dict):
            raise PolicyError(f"{field} must be an object")
        unknown_item = set(item) - {
            "key_id",
            "algorithm",
            "public_key",
            "trusted_for",
            "not_before",
            "not_after",
        }
        if unknown_item:
            raise PolicyError(f"{field} has unknown fields: {', '.join(sorted(unknown_item))}")
        key_id = item.get("key_id")
        if not isinstance(key_id, str) or not key_id.strip():
            raise PolicyError(f"{field}.key_id must be a non-empty string")
        key_id = key_id.strip()
        if key_id in seen:
            raise PolicyError(f"duplicate trusted key id: {key_id}")
        seen.add(key_id)
        if item.get("algorithm") != POLICY_SIGNATURE_ALGORITHM:
            raise PolicyError(f"{field}.algorithm must be {POLICY_SIGNATURE_ALGORITHM}")
        public_key = item.get("public_key")
        public_key_bytes = _base64_bytes(public_key, f"{field}.public_key", expected_length=32)
        trusted_for = item.get("trusted_for")
        if (
            not isinstance(trusted_for, list)
            or not trusted_for
            or not all(isinstance(value, str) and value.strip() for value in trusted_for)
        ):
            raise PolicyError(f"{field}.trusted_for must be a non-empty string array")
        purposes = list(dict.fromkeys(value.strip() for value in trusted_for))
        if purposes != ["policy-signing"]:
            raise PolicyError(f"{field}.trusted_for must contain only policy-signing")
        not_before_raw = item.get("not_before")
        not_after_raw = item.get("not_after")
        not_before = _datetime(not_before_raw, f"{field}.not_before")
        not_after = _datetime(not_after_raw, f"{field}.not_after")
        if not_before >= not_after:
            raise PolicyError(f"{field}.not_before must be before not_after")
        assert isinstance(public_key, str)
        assert isinstance(not_before_raw, str)
        assert isinstance(not_after_raw, str)
        normalized.append(
            {
                "key_id": key_id,
                "algorithm": POLICY_SIGNATURE_ALGORITHM,
                "public_key": public_key.strip(),
                "_public_key_bytes": public_key_bytes,
                "trusted_for": purposes,
                "not_before": not_before_raw.strip(),
                "not_after": not_after_raw.strip(),
                "_not_before": not_before,
                "_not_after": not_after,
            }
        )
    return {"schema_version": 1, "trust_model": SIGNATURE_TRUST_MODEL, "keys": normalized}


def normalize_policy_signature(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PolicyError("policy signature must be a JSON object")
    unknown = set(payload) - {
        "schema_version",
        "signature_format",
        "signed_at",
        "payload",
        "signatures",
    }
    if unknown:
        raise PolicyError(f"unknown policy signature fields: {', '.join(sorted(unknown))}")
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise PolicyError("schema_version must be 1")
    if payload.get("signature_format") != POLICY_SIGNATURE_FORMAT:
        raise PolicyError(f"signature_format must be {POLICY_SIGNATURE_FORMAT}")
    signed_at_raw = payload.get("signed_at")
    signed_at = _datetime(signed_at_raw, "signed_at")
    signature_payload = normalize_policy_signing_payload(payload.get("payload"))
    signatures = payload.get("signatures")
    if not isinstance(signatures, list) or not signatures:
        raise PolicyError("signatures must be a non-empty array")
    normalized_signatures = []
    for index, item in enumerate(signatures):
        field = f"signatures[{index}]"
        if not isinstance(item, dict):
            raise PolicyError(f"{field} must be an object")
        unknown_item = set(item) - {"key_id", "algorithm", "signature"}
        if unknown_item:
            raise PolicyError(f"{field} has unknown fields: {', '.join(sorted(unknown_item))}")
        key_id = item.get("key_id")
        if not isinstance(key_id, str) or not key_id.strip():
            raise PolicyError(f"{field}.key_id must be a non-empty string")
        key_id = key_id.strip()
        if item.get("algorithm") != POLICY_SIGNATURE_ALGORITHM:
            raise PolicyError(f"{field}.algorithm must be {POLICY_SIGNATURE_ALGORITHM}")
        signature = item.get("signature")
        signature_bytes = _base64_bytes(signature, f"{field}.signature", expected_length=64)
        assert isinstance(signature, str)
        normalized_signatures.append(
            {
                "key_id": key_id,
                "algorithm": POLICY_SIGNATURE_ALGORITHM,
                "signature": signature.strip(),
                "_signature_bytes": signature_bytes,
            }
        )
    assert isinstance(signed_at_raw, str)
    return {
        "schema_version": 1,
        "signature_format": POLICY_SIGNATURE_FORMAT,
        "signed_at": signed_at_raw.strip(),
        "_signed_at": signed_at,
        "payload": signature_payload,
        "signatures": normalized_signatures,
    }


def load_policy_trust_root(path: Path) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise PolicyError(f"cannot read {path.name}: {error}") from error
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PolicyError(f"invalid JSON in {path.name}: {error}") from error
    return normalize_policy_trust_root(payload), hashlib.sha256(raw).hexdigest()


def load_policy_key_trust_root(path: Path) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise PolicyError(f"cannot read {path.name}: {error}") from error
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PolicyError(f"invalid JSON in {path.name}: {error}") from error
    return normalize_policy_key_trust_root(payload), hashlib.sha256(raw).hexdigest()


def load_policy_signature(path: Path) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise PolicyError(f"cannot read {path.name}: {error}") from error
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PolicyError(f"invalid JSON in {path.name}: {error}") from error
    return normalize_policy_signature(payload), hashlib.sha256(raw).hexdigest()


def render_policy_trust_root(policy: dict[str, Any]) -> str:
    payload = {
        "schema_version": 1,
        "trust_model": TRUST_MODEL,
        "policies": policy["_sources"],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def policy_signing_payload(
    policy: dict[str, Any],
    *,
    source: str,
    digest: str,
) -> dict[str, Any]:
    """Return the deterministic source-digest manifest that future signatures should cover."""
    return {
        "policy_signing_payload_format": POLICY_SIGNING_PAYLOAD_FORMAT,
        "schema_version": 1,
        "root_source": source,
        "root_sha256": digest,
        "policy_set": policy.get("_sources", [{"source": source, "sha256": digest}]),
    }


def render_policy_signing_payload(policy: dict[str, Any], *, source: str, digest: str) -> str:
    return json.dumps(policy_signing_payload(policy, source=source, digest=digest), indent=2) + "\n"


def _policy_signing_payload_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2) + "\n").encode("utf-8")


def _policy_signature_result(
    summary: dict[str, Any],
    *,
    key_trust_root: dict[str, Any],
    signature_bundle: dict[str, Any],
    signature_source: str,
    signature_digest: str,
    trust_root_source: str,
    trust_root_digest: str,
) -> dict[str, Any]:
    signed_sources = {
        item["source"]: item["sha256"] for item in signature_bundle["payload"]["policy_set"]
    }
    matched_sources = []
    missing_sources = []
    digest_mismatches = []
    payload_mismatches = []
    for item in summary["sources"]:
        expected = signed_sources.get(item["source"])
        if expected is None:
            missing_sources.append(item["source"])
        elif expected != item["sha256"]:
            digest_mismatches.append(
                {
                    "source": item["source"],
                    "expected_sha256": expected,
                    "actual_sha256": item["sha256"],
                }
            )
        else:
            matched_sources.append(item["source"])
    expected_payload = {
        "policy_signing_payload_format": POLICY_SIGNING_PAYLOAD_FORMAT,
        "schema_version": 1,
        "root_source": summary["source"],
        "root_sha256": summary["sha256"],
        "policy_set": summary["sources"],
    }
    signed_payload = signature_bundle["payload"]
    for field in ("root_source", "root_sha256", "policy_set"):
        if signed_payload[field] != expected_payload[field]:
            payload_mismatches.append(field)

    trusted_keys = {key["key_id"]: key for key in key_trust_root["keys"]}
    signed_at = signature_bundle["_signed_at"]
    signed_payload_bytes = _policy_signing_payload_bytes(signature_bundle["payload"])
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as error:  # pragma: no cover - dependency is declared for normal installs
        raise PolicyError("cryptography is required to verify policy signatures") from error
    verified_signatures = []
    untrusted_signatures = []
    expired_signatures = []
    invalid_signatures = []
    for signature in signature_bundle["signatures"]:
        key_id = signature["key_id"]
        key = trusted_keys.get(key_id)
        if key is None:
            untrusted_signatures.append({"key_id": key_id})
            continue
        if signed_at < key["_not_before"] or signed_at > key["_not_after"]:
            expired_signatures.append(
                {
                    "key_id": key_id,
                    "not_before": key["not_before"],
                    "not_after": key["not_after"],
                }
            )
            continue
        public_key = Ed25519PublicKey.from_public_bytes(key["_public_key_bytes"])
        try:
            public_key.verify(signature["_signature_bytes"], signed_payload_bytes)
        except InvalidSignature:
            invalid_signatures.append({"key_id": key_id})
        else:
            verified_signatures.append({"key_id": key_id})
    trusted = (
        not missing_sources
        and not digest_mismatches
        and not payload_mismatches
        and bool(verified_signatures)
    )
    return {
        "source": signature_source,
        "sha256": signature_digest,
        "trust_root_source": trust_root_source,
        "trust_root_sha256": trust_root_digest,
        "trust_model": key_trust_root["trust_model"],
        "signature_format": signature_bundle["signature_format"],
        "trusted": trusted,
        "signed_at": signature_bundle["signed_at"],
        "matched_sources": matched_sources,
        "missing_sources": missing_sources,
        "digest_mismatches": digest_mismatches,
        "payload_mismatches": payload_mismatches,
        "verified_signatures": verified_signatures,
        "untrusted_signatures": untrusted_signatures,
        "expired_signatures": expired_signatures,
        "invalid_signatures": invalid_signatures,
        "unsupported_algorithms": [],
    }


def policy_trust_summary(
    summary: dict[str, Any],
    trust_root: dict[str, Any] | None = None,
    *,
    source: str | None = None,
    digest: str | None = None,
    key_trust_root: dict[str, Any] | None = None,
    key_trust_root_source: str | None = None,
    key_trust_root_digest: str | None = None,
    signature_bundle: dict[str, Any] | None = None,
    signature_source: str | None = None,
    signature_digest: str | None = None,
) -> dict[str, Any]:
    base = {
        "content_hashes": True,
        "signature_verified": False,
        "note": "SHA-256 digests identify local policy content; they do not prove author authenticity.",
    }
    if signature_bundle is not None or key_trust_root is not None:
        if (
            signature_bundle is None
            or key_trust_root is None
            or not signature_source
            or not signature_digest
            or not key_trust_root_source
            or not key_trust_root_digest
        ):
            raise PolicyError("policy signature and key trust root metadata are required")
        signature = _policy_signature_result(
            summary,
            key_trust_root=key_trust_root,
            signature_bundle=signature_bundle,
            signature_source=signature_source,
            signature_digest=signature_digest,
            trust_root_source=key_trust_root_source,
            trust_root_digest=key_trust_root_digest,
        )
        return {**base, "signature_verified": signature["trusted"], "signature": signature}
    if trust_root is None:
        return base
    if not source or not digest:
        raise PolicyError("policy trust root source and sha256 are required")
    trusted = {item["source"]: item["sha256"] for item in trust_root["policies"]}
    matched_sources = []
    missing_sources = []
    digest_mismatches = []
    for item in summary["sources"]:
        expected = trusted.get(item["source"])
        if expected is None:
            missing_sources.append(item["source"])
        elif expected != item["sha256"]:
            digest_mismatches.append(
                {
                    "source": item["source"],
                    "expected_sha256": expected,
                    "actual_sha256": item["sha256"],
                }
            )
        else:
            matched_sources.append(item["source"])
    return {
        **base,
        "trust_root": {
            "source": source,
            "sha256": digest,
            "trust_model": trust_root["trust_model"],
            "trusted": not missing_sources and not digest_mismatches,
            "matched_sources": matched_sources,
            "missing_sources": missing_sources,
            "digest_mismatches": digest_mismatches,
        },
    }


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


def policy_summary(
    policy: dict[str, Any],
    *,
    source: str,
    digest: str,
    trust_root: dict[str, Any] | None = None,
    trust_root_source: str | None = None,
    trust_root_digest: str | None = None,
    key_trust_root: dict[str, Any] | None = None,
    key_trust_root_source: str | None = None,
    key_trust_root_digest: str | None = None,
    signature_bundle: dict[str, Any] | None = None,
    signature_source: str | None = None,
    signature_digest: str | None = None,
) -> dict[str, Any]:
    """Return scan-independent policy composition and provenance metadata."""
    gates = [
        {
            **{key: value for key, value in gate.items() if not key.startswith("_")},
            "policy_source": gate.get("_policy_source", source),
            "policy_sha256": gate.get("_policy_sha256", digest),
        }
        for gate in policy["gates"]
    ]
    summary = {
        "policy_format": "AgentVerify Policy Summary",
        "schema_version": 1,
        "name": policy["name"],
        "source": source,
        "sha256": digest,
        "sources": policy.get("_sources", [{"source": source, "sha256": digest}]),
        "gates": gates,
    }
    summary["trust"] = policy_trust_summary(
        summary,
        trust_root,
        source=trust_root_source,
        digest=trust_root_digest,
        key_trust_root=key_trust_root,
        key_trust_root_source=key_trust_root_source,
        key_trust_root_digest=key_trust_root_digest,
        signature_bundle=signature_bundle,
        signature_source=signature_source,
        signature_digest=signature_digest,
    )
    return summary


def render_policy_summary(
    policy: dict[str, Any],
    *,
    source: str,
    digest: str,
    output_format: str = "text",
    trust_root: dict[str, Any] | None = None,
    trust_root_source: str | None = None,
    trust_root_digest: str | None = None,
    key_trust_root: dict[str, Any] | None = None,
    key_trust_root_source: str | None = None,
    key_trust_root_digest: str | None = None,
    signature_bundle: dict[str, Any] | None = None,
    signature_source: str | None = None,
    signature_digest: str | None = None,
) -> str:
    """Render a scan-independent policy validation/explanation report."""
    summary = policy_summary(
        policy,
        source=source,
        digest=digest,
        trust_root=trust_root,
        trust_root_source=trust_root_source,
        trust_root_digest=trust_root_digest,
        key_trust_root=key_trust_root,
        key_trust_root_source=key_trust_root_source,
        key_trust_root_digest=key_trust_root_digest,
        signature_bundle=signature_bundle,
        signature_source=signature_source,
        signature_digest=signature_digest,
    )
    if output_format == "json":
        return json.dumps(summary, indent=2, sort_keys=True) + "\n"
    lines = [
        "AgentVerify Policy",
        f"Name: {summary['name']}",
        f"Source: {summary['source']}",
        f"SHA-256: {summary['sha256']}",
        f"Policy sources: {len(summary['sources'])}",
        f"Gates: {len(summary['gates'])}",
    ]
    for gate in summary["gates"]:
        rules = ", ".join(gate["rules"]) if gate["rules"] else "all reporting rules"
        lines.append(
            f"  {gate['id']} ({gate['policy_source']}): "
            f"rules={rules}; result_kinds={','.join(gate['result_kinds'])}; "
            f"min_severity={gate['min_severity']}; max_count={gate['max_count']}"
        )
    if signature_result := summary["trust"].get("signature"):
        signature_status = "verified" if signature_result["trusted"] else "untrusted"
        lines.append(f"Trust: policy signature {signature_status}")
        lines.append(
            f"Signature: {signature_result['source']} "
            f"[{signature_result['trust_model']}; signed_at={signature_result['signed_at']}]"
        )
        if signature_result["verified_signatures"]:
            key_ids = ", ".join(item["key_id"] for item in signature_result["verified_signatures"])
            lines.append(f"  Verified keys: {key_ids}")
        if signature_result["missing_sources"]:
            lines.append(
                f"  Missing signed sources: {', '.join(signature_result['missing_sources'])}"
            )
        if signature_result["digest_mismatches"]:
            sources = ", ".join(item["source"] for item in signature_result["digest_mismatches"])
            lines.append(f"  Signed digest mismatches: {sources}")
        if signature_result["untrusted_signatures"]:
            key_ids = ", ".join(item["key_id"] for item in signature_result["untrusted_signatures"])
            lines.append(f"  Untrusted signature keys: {key_ids}")
        if signature_result["expired_signatures"]:
            key_ids = ", ".join(item["key_id"] for item in signature_result["expired_signatures"])
            lines.append(f"  Expired signature keys: {key_ids}")
        if signature_result["invalid_signatures"]:
            key_ids = ", ".join(item["key_id"] for item in signature_result["invalid_signatures"])
            lines.append(f"  Invalid signature keys: {key_ids}")
    else:
        lines.append("Trust: content hashes only; no author signature verified")
    if trust_root_result := summary["trust"].get("trust_root"):
        trust_status = "trusted" if trust_root_result["trusted"] else "untrusted"
        lines.append(
            f"Trust root: {trust_root_result['source']} "
            f"[{trust_root_result['trust_model']}; {trust_status}]"
        )
        if trust_root_result["missing_sources"]:
            lines.append(f"  Missing sources: {', '.join(trust_root_result['missing_sources'])}")
        if trust_root_result["digest_mismatches"]:
            sources = ", ".join(item["source"] for item in trust_root_result["digest_mismatches"])
            lines.append(f"  Digest mismatches: {sources}")
    return "\n".join(lines) + "\n"

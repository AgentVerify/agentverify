"""Exercise signed policy verification with an ephemeral Ed25519 key.

The script intentionally never writes private-key material. It exports the deterministic
AgentVerify policy-signing payload, signs the exact exported bytes with an in-memory key, writes only
the detached signature bundle plus public-key trust root, and then requires the AgentVerify CLI to
verify the signed policy.
"""

from __future__ import annotations

import argparse
import base64
import json
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

DEFAULT_SIGNED_AT = "2026-08-26T00:00:00Z"
DEFAULT_NOT_BEFORE = "2026-01-01T00:00:00Z"
DEFAULT_NOT_AFTER = "2027-01-01T00:00:00Z"


def command(argv: Sequence[str]) -> str:
    completed = subprocess.run(argv, check=True, text=True, capture_output=True)
    return completed.stdout


def write_ephemeral_signature_artifacts(
    payload_path: Path,
    signature_path: Path,
    trust_root_path: Path,
    *,
    key_id: str,
    signed_at: str = DEFAULT_SIGNED_AT,
    not_before: str = DEFAULT_NOT_BEFORE,
    not_after: str = DEFAULT_NOT_AFTER,
) -> None:
    payload_bytes = payload_path.read_bytes()
    payload = json.loads(payload_bytes)
    private_key = Ed25519PrivateKey.generate()
    signature = private_key.sign(payload_bytes)
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    signature_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "signature_format": "agentverify-policy-signature",
                "signed_at": signed_at,
                "payload": payload,
                "signatures": [
                    {
                        "key_id": key_id,
                        "algorithm": "ed25519",
                        "signature": base64.b64encode(signature).decode("ascii"),
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    trust_root_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "trust_model": "local-key-signature",
                "keys": [
                    {
                        "key_id": key_id,
                        "algorithm": "ed25519",
                        "public_key": base64.b64encode(public_key).decode("ascii"),
                        "trusted_for": ["policy-signing"],
                        "not_before": not_before,
                        "not_after": not_after,
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def run_signed_policy_example(
    policy_path: Path,
    *,
    agentverify_command: Sequence[str] = ("agentverify",),
    work_dir: Path | None = None,
    key_id: str = "ephemeral-ci-smoke",
) -> dict[str, object]:
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    if work_dir is None:
        temp_dir = tempfile.TemporaryDirectory(prefix="agentverify-signed-policy-")
        workspace = Path(temp_dir.name)
    else:
        workspace = work_dir
        workspace.mkdir(parents=True, exist_ok=True)
    try:
        signing_payload = workspace / "policy-signing-payload.json"
        signature_bundle = workspace / "policy-signature.json"
        key_trust_root = workspace / "policy-key-trust-root.json"
        command(
            [
                *agentverify_command,
                "policy",
                str(policy_path),
                "--export-signing-payload",
                "--output",
                str(signing_payload),
            ]
        )
        write_ephemeral_signature_artifacts(
            signing_payload,
            signature_bundle,
            key_trust_root,
            key_id=key_id,
        )
        summary = json.loads(
            command(
                [
                    *agentverify_command,
                    "policy",
                    str(policy_path),
                    "--signature",
                    str(signature_bundle),
                    "--trust-root",
                    str(key_trust_root),
                    "--require-trusted",
                    "--format",
                    "json",
                ]
            )
        )
        signature = summary.get("trust", {}).get("signature", {})
        checks = {
            "policy": str(policy_path),
            "key_id": key_id,
            "signature_verified": summary.get("trust", {}).get("signature_verified"),
            "signature_trusted": signature.get("trusted"),
            "verified_key_ids": [
                item.get("key_id") for item in signature.get("verified_signatures", [])
            ],
            "private_key_material": "ephemeral-memory-only",
            "generated_artifacts": [
                signing_payload.name,
                signature_bundle.name,
                key_trust_root.name,
            ],
        }
        failed = [
            name
            for name in ("signature_verified", "signature_trusted")
            if checks.get(name) is not True
        ]
        if checks["verified_key_ids"] != [key_id]:
            failed.append("verified_key_ids")
        if failed:
            raise RuntimeError(
                json.dumps(
                    {
                        "failed_signed_policy_checks": failed,
                        "checks": checks,
                        "policy_summary": summary,
                    },
                    indent=2,
                )
            )
        return checks
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify examples/repository-policy.json using an ephemeral detached Ed25519 signature."
        )
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("examples/repository-policy.json"),
        help="policy file to verify after exporting and signing its deterministic payload",
    )
    parser.add_argument(
        "--agentverify",
        default="agentverify",
        help="AgentVerify command to run; quote multi-word commands such as 'python -m agentverify.cli'",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help=(
            "optional directory for generated public artifacts; omit to use a temporary directory "
            "that is deleted on success"
        ),
    )
    parser.add_argument("--key-id", default="ephemeral-ci-smoke")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = run_signed_policy_example(
            args.policy,
            agentverify_command=shlex.split(args.agentverify),
            work_dir=args.work_dir,
            key_id=args.key_id,
        )
    except (RuntimeError, subprocess.CalledProcessError, OSError, json.JSONDecodeError) as error:
        print(f"agentverify signed policy example failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2) + "\n", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

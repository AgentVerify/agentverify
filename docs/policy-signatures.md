# Signed policy provenance

AgentVerify currently supports local policy content trust through SHA-256 digest allowlists. That is
useful for CI reproducibility, but it deliberately does not prove who authored, approved, or
published a policy. Signed policy provenance adds author authenticity without weakening the
current fail-closed digest behavior.

AgentVerify exports the deterministic source-digest payload that external signing tools sign, then
verifies a detached Ed25519 signature bundle against a local public-key trust root with
`agentverify policy --signature ... --trust-root ...`. Digest-only allowlists continue to report
`signature_verified: false`; signature mode reports `signature_verified: true` only after the signed
manifest and at least one trusted signature verify.

## Goals

- Verify that every composed policy source was approved by a locally trusted signing identity.
- Preserve exact source-byte provenance: the bytes scanned by `agentverify policy` are the bytes
  whose digest is signed.
- Support offline CI. Verification should not require network access, transparency log access, or a
  hosted key service.
- Keep migration from `local-content-digest-allowlist` straightforward for teams already pinning
  policy digests.
- Fail closed on unknown trust-root fields, unknown signature-bundle fields, malformed keys,
  unsupported algorithms, missing sources, stale digests, and untrusted signers.

## Non-goals

- Legal compliance claims.
- Remote key discovery or automatic trust-on-first-use.
- Runtime sandbox guarantees.
- Replacing digest allowlists. Digest allowlists remain a valid local approval mechanism even after
  signatures exist.

## Threat model

Signed policy provenance should protect against a repository policy being changed after approval, a
base organization policy being swapped for another local file, or a CI job accidentally evaluating a
policy that has not been approved by a trusted maintainer/security group.

It does not protect against a compromised trusted private key, a malicious reviewer who already has
signing authority, a CI environment that points AgentVerify at the wrong trust root, or a repository
that disables signature verification.

## Signing unit

Sign a detached manifest of policy source digests rather than attempting to canonicalize policy JSON.
This avoids ambiguity around whitespace, key ordering, comments, or future JSON-compatible formats.

The exported signing payload includes:

- `schema_version`
- `policy_signing_payload_format`
- `policy_set`: an ordered array of `{source, sha256}`
- `root_source`
- `root_sha256`

The verifier recomputes each source digest from local bytes, compares it to the signed manifest, and
then verifies the detached signature over the exact bytes produced by
`agentverify policy --export-signing-payload`. A composed policy is signature-verified only when
every evaluated source appears in a trusted, valid signature bundle and the signed digest matches
local content.

## Signature bundle shape

Trust model name:

```text
local-key-signature
```

Detached bundle:

```json
{
  "schema_version": 1,
  "signature_format": "agentverify-policy-signature",
  "signed_at": "2026-08-26T00:00:00Z",
  "payload": {
    "policy_signing_payload_format": "AgentVerify Policy Signing Payload",
    "schema_version": 1,
    "root_source": "repository-policy.json",
    "root_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "policy_set": [
      {
        "source": "org-policy.json",
        "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      },
      {
        "source": "repository-policy.json",
        "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
      }
    ]
  },
  "signatures": [
    {
      "key_id": "security-team-2026",
      "algorithm": "ed25519",
      "signature": "base64-detached-signature"
    }
  ]
}
```

`key_id` is an identifier selected by the trust root. It is not self-authenticating.

## Local key trust root shape

The trust root stays local and explicit:

```json
{
  "schema_version": 1,
  "trust_model": "local-key-signature",
  "keys": [
    {
      "key_id": "security-team-2026",
      "algorithm": "ed25519",
      "public_key": "base64-raw-public-key",
      "trusted_for": ["policy-signing"],
      "not_before": "2026-01-01T00:00:00Z",
      "not_after": "2027-01-01T00:00:00Z"
    }
  ]
}
```

Verification should require an unexpired trusted key whose `trusted_for` includes
`policy-signing`. Key expiry should be evaluated against the signature bundle's `signed_at`, not the
current wall clock, so historical approvals remain reproducible after rotation.

## Summary reporting

The policy summary trust block remains conservative:

- `content_hashes: true` whenever source digests are reported.
- `signature_verified: true` only when every composed source has a matching signed digest and at
  least one valid trusted signature.
- `signature_verified: false` for digest-only allowlists, missing signatures, untrusted keys,
  unsupported algorithms, or partial signature coverage.

The summary also exposes machine-readable failure reasons such as `missing_sources`,
`digest_mismatches`, `payload_mismatches`, `untrusted_signatures`, `expired_signatures`,
`invalid_signatures`, and `unsupported_algorithms`.

## CLI design

Export the payload to sign:

```console
agentverify policy repository-policy.json \
  --export-signing-payload \
  --output policy-signing-payload.json
```

`--export-signing-payload` produces the exact payload bytes to sign. AgentVerify does not hold
private keys; signing is done by external tools or organizational key management.

Verify a detached signature:

```console
agentverify policy repository-policy.json \
  --signature policy-signature.json \
  --trust-root policy-key-trust-root.json \
  --require-trusted
```

The verification input schemas are discoverable:

```console
agentverify schema policy-signature --output agentverify-policy-signature.schema.json
agentverify schema policy-key-trust-root --output agentverify-policy-key-trust-root.schema.json
```

## Local dry run with an ephemeral key

For a local smoke test, you can generate an ephemeral Ed25519 key, sign the exported payload bytes,
and immediately verify the signature. This demonstrates the file shapes without creating a durable
organizational trust root. Do not commit the generated private key from a real signing workflow.

```console
tmpdir="$(mktemp -d)"
agentverify policy examples/repository-policy.json \
  --export-signing-payload \
  --output "$tmpdir/policy-signing-payload.json"
python - "$tmpdir/policy-signing-payload.json" \
  "$tmpdir/policy-signature.json" \
  "$tmpdir/policy-key-trust-root.json" <<'PY'
import base64
import json
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

payload_path, signature_path, trust_root_path = sys.argv[1:]
payload_bytes = open(payload_path, "rb").read()
payload = json.loads(payload_bytes)
private_key = Ed25519PrivateKey.generate()
signature = private_key.sign(payload_bytes)
public_key = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw,
)
json.dump(
    {
        "schema_version": 1,
        "signature_format": "agentverify-policy-signature",
        "signed_at": "2026-08-26T00:00:00Z",
        "payload": payload,
        "signatures": [
            {
                "key_id": "local-smoke-test",
                "algorithm": "ed25519",
                "signature": base64.b64encode(signature).decode("ascii"),
            }
        ],
    },
    open(signature_path, "w", encoding="utf-8"),
    indent=2,
)
json.dump(
    {
        "schema_version": 1,
        "trust_model": "local-key-signature",
        "keys": [
            {
                "key_id": "local-smoke-test",
                "algorithm": "ed25519",
                "public_key": base64.b64encode(public_key).decode("ascii"),
                "trusted_for": ["policy-signing"],
                "not_before": "2026-01-01T00:00:00Z",
                "not_after": "2027-01-01T00:00:00Z",
            }
        ],
    },
    open(trust_root_path, "w", encoding="utf-8"),
    indent=2,
)
PY
agentverify policy examples/repository-policy.json \
  --signature "$tmpdir/policy-signature.json" \
  --trust-root "$tmpdir/policy-key-trust-root.json" \
  --require-trusted \
  --format json
```

For production, replace the ephemeral key generation with your organization's signing system and
commit only the public-key trust root plus detached signature bundle that your CI policy expects.

## Migration from digest allowlists

Existing `local-content-digest-allowlist` files can remain valid. A team can migrate by:

1. Running `agentverify policy PATH --export-trust-root` to capture current source digests.
2. Producing a signing payload over the same composed source list.
3. Signing the payload with an approved key.
4. Replacing or supplementing the digest trust root with a `local-key-signature` trust root and
   detached signature bundle.

During migration, the summary should clearly distinguish:

- digest-matched but unsigned content;
- signed and trusted content;
- signed content from an untrusted key.

## Deferred design questions

- Whether to support multiple signatures with threshold policies in schema v1 or defer thresholds to
  schema v2.
- Whether signed payloads should optionally include rule-catalog schema versions so policy approvals
  can be bounded to a rule contract version.

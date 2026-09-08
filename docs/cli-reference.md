# CLI reference

[Documentation index](README.md) · [Getting started](getting-started.md)

Install from the [GitHub release](https://github.com/AgentVerify/agentverify/releases/tag/v0.1.0)
or follow the getting-started guide before using these commands.

```console
agentverify scan ./project
agentverify scan ./project --format summary
agentverify scan ./project --format json
agentverify scan ./project --format bom
agentverify scan ./project --format sarif
agentverify scan ./project --format sarif --output agentverify.sarif
agentverify schema
agentverify schema benchmark-result --output agentverify-benchmark-result.schema.json
agentverify schema benchmark-verification --output agentverify-benchmark-verification.schema.json
agentverify schema editor-contract-manifest --output agentverify-editor-contract-manifest.schema.json
agentverify schema editor-contract-verification --output agentverify-editor-contract-verification.schema.json
agentverify schema editor-diagnostics --output agentverify-editor-diagnostics.schema.json
agentverify schema engine-results --output agentverify-engine-results.schema.json
agentverify schema engine-results-verification --output agentverify-engine-results-verification.schema.json
agentverify schema holdout-manifest --output agentverify-holdout-manifest.schema.json
agentverify schema holdout-labels --output agentverify-holdout-labels.schema.json
agentverify schema report --output agentverify-report.schema.json
agentverify schema bom --output agentverify-ai-bom.schema.json
agentverify schema policy --output agentverify-policy.schema.json
agentverify schema policy-key-trust-root --output agentverify-policy-key-trust-root.schema.json
agentverify schema policy-signature --output agentverify-policy-signature.schema.json
agentverify schema policy-signing-payload --output agentverify-policy-signing-payload.schema.json
agentverify schema policy-summary --output agentverify-policy-summary.schema.json
agentverify schema policy-trust-root --output agentverify-policy-trust-root.schema.json
agentverify schema rules --output agentverify-rules.schema.json
agentverify scan ./project --policy agentverify-policy.json
agentverify scan ./project --policy repository-policy.json  # may extend local organization policy
agentverify policy repository-policy.json
agentverify policy repository-policy.json --format json
agentverify policy repository-policy.json --export-trust-root --output policy-trust-root.json
agentverify policy repository-policy.json --export-signing-payload --output policy-signing-payload.json
agentverify policy repository-policy.json --trust-root policy-trust-root.json --require-trusted
agentverify policy examples/repository-policy.json --trust-root examples/policy-trust-root.json --require-trusted
agentverify benchmark verify --require-evaluation-kind public-regression --require-all-passed
agentverify benchmark verify-engine
agentverify holdout validate --manifest benchmarks/holdout-manifest.template.json --labels benchmarks/holdout-labels.template.json
agentverify contracts --output-dir agentverify-editor-contracts --sample-root examples/safe_agent
agentverify contracts --verify-dir agentverify-editor-contracts
agentverify contracts --verify-dir agentverify-editor-contracts --format summary
agentverify scan ./project --fail-on high
agentverify scan ./project --fail-on high --fail-on-kind any
agentverify scan ./project --include-tests
agentverify scan ./project --baseline previous-agentverify.json
agentverify scan ./project --paths-from changed-files.txt
agentverify scan ./project --require-suppression-expiry --fail-on high
agentverify rules
agentverify rules AV-EXEC001
agentverify rules --format json
```

Reviewed exceptions can be suppressed only for the immediately following line, with a rule ID and
required reason:

```python
# agentverify: ignore AV-EXEC001 until 2026-12-31 -- command is selected from the fixed deployment allowlist
subprocess.run(command, shell=True)
```

JSON and text reports retain the suppression's rule, reason, directive location, and finding location.
They also retain expiry and status. JSON reports self-identify as `AgentVerify JSON Report` schema
version 1 and include a deterministic `risk_summary` by rule, severity, and result kind after inline
suppression and baseline filtering. Expired or malformed dates never suppress a finding;
`--require-suppression-expiry` also restores reason-only exceptions. Broad file-level or reason-free
inline ignores are intentionally unsupported. Expiry dates are evaluated in UTC and remain active
through the stated date.
When `--baseline` is used, reports separate new and unchanged fingerprints and count fingerprints no
longer reported by a full scan. Partial selected-path scans leave that last count unavailable.
Baselines must be a fingerprint list, an AgentVerify JSON report, a native AI BOM, or a SARIF report;
unknown JSON objects and malformed entries without AgentVerify fingerprints are rejected instead of
treated as an empty baseline.
Reports and schemas are written to standard output by default. Use `--output PATH` (or `-o PATH`)
to write them directly to a file. Output write failures return exit code 2; successful scan writes
still preserve policy and `--fail-on` exit decisions.
`agentverify schema` lists every bundled machine-readable schema.
`agentverify schema benchmark-result` prints the bundled schema for benchmark result files.
`agentverify schema benchmark-verification` validates the JSON emitted by
`agentverify benchmark verify`.
`agentverify schema editor-contract-manifest` validates the manifest emitted by
`agentverify contracts`; `agentverify schema editor-contract-verification` validates the JSON emitted
by `agentverify contracts --verify-dir`; `agentverify schema editor-diagnostics` validates
LSP-style editor diagnostic adapter payloads derived from AgentVerify JSON reports.
`agentverify schema engine-results` validates full-corpus engine metric snapshots such as
`benchmarks/engine-results.json`.
`agentverify schema engine-results-verification` validates the JSON emitted by
`agentverify benchmark verify-engine`, which checks the snapshot schema, core aggregate totals, and
flat per-repository detector metric totals.
`agentverify schema holdout-manifest` and `agentverify schema holdout-labels` validate the public
sealed-holdout sampling and adjudicated-label templates.
`agentverify holdout validate --manifest PATH --labels PATH` validates those setup files directly
with the bundled schemas, returning exit code 2 when a template or private setup file is malformed.
`agentverify schema report` prints the bundled schema for validating normal `--format json` reports;
`agentverify schema policy-summary` validates `agentverify policy --format json`,
`agentverify schema policy-signing-payload` validates deterministic source-digest manifests for
external policy signing, `agentverify schema policy-signature` and
`agentverify schema policy-key-trust-root` validate detached signature bundles and local public-key
trust roots, and `agentverify schema policy-trust-root` validates local digest allowlists for policy
summaries.
`agentverify schema rules` validates the machine-readable rule catalog.
`agentverify benchmark verify` validates benchmark result JSON against the bundled schema, recomputes
label and manifest digests, binds outcomes back to exact label ids/rules/expectations, recomputes
outcome-derived passed/failed/metrics totals, and reports failure classes separately for observation,
anchor, and source-snippet mismatches. It can fail closed on release-claim requirements such as
`--require-evaluation-kind sealed-holdout`, `--require-sealed`, `--require-manifest`, and
`--require-all-passed`. Use `agentverify benchmark verify --format summary` for compact CI logs
while keeping JSON as the default machine-readable artifact format.
`agentverify benchmark verify-engine` validates full-corpus engine metric snapshots against the
bundled engine-results schema and checks that core summary totals plus flat per-repository detector
metric totals match the packaged repository entries. Use
`agentverify benchmark verify-engine --format summary` for compact CI logs while keeping JSON as the
default machine-readable artifact format.
Use `--format summary` for compact CI logs: it reports scan totals, baseline/policy status, counts by
severity/result kind/rule, and the top evidence locations without printing the full component graph.
`agentverify rules` lists every enabled reporting rule with its result kind, default severity,
confidence, summary, and baseline remediation. Pass a rule ID for a focused explanation or
`--format json` for policy tooling and editor integrations; the bundled rules schema preserves this
contract for generated configuration and editor metadata. Policy rule filters reject unknown or
inventory-only IDs before scanning. They also reject selected rules excluded by the gate's result
kind or severity threshold, so a typo or dead filter cannot silently turn a gate into an empty match.
`agentverify policy PATH` validates a policy without scanning a repository and explains composed
gate sources and SHA-256 content digests. These digests make local inputs auditable; they are not
author signatures. A policy trust root can require every composed policy source to match an approved
local SHA-256 digest allowlist while keeping `signature_verified: false`. For author authenticity,
`agentverify policy PATH --signature policy-signature.json --trust-root policy-key-trust-root.json`
verifies a detached Ed25519 signature over the composed source-digest manifest and can be combined
with `--require-trusted` as a fail-closed CI gate. Use
`agentverify policy PATH --export-trust-root --output policy-trust-root.json` to generate a local
digest allowlist from the exact composed policy inputs, or
`agentverify policy PATH --export-signing-payload --output policy-signing-payload.json` to emit the
deterministic source-digest manifest that external signing tools should sign.
See [`docs/policy-signatures.md`](policy-signatures.md) for a local ephemeral-key dry run and
production trust-root guidance.

Example finding:

```text
HIGH AV-EXEC001 [high; finding]
  A dynamic command is executed through a system shell
  agent.py:13
  Path: agent:operator -> tool:run_task -> capability:shell-execution
  Approval coverage: unresolved
  Audit coverage: unresolved
  Remediation: Pass a fixed argv list with shell=False, or strictly validate and allowlist the command.
```

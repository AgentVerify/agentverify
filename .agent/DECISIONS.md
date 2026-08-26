# AgentVerify decisions

## Rule catalog is a machine contract

- Decision: Treat the runtime rule catalog as an externally consumable schema-versioned contract.
- Evidence: `agentverify rules --format json` already emits `schema_version: 1`; policies and SARIF
  descriptors depend on the same rule metadata. Generated CI/editor integrations need validation
  without scraping documentation.
- Alternative: Leave rules JSON self-describing only. Rejected because it creates a weaker contract
  than reports, BOMs, and policies.
- Revisit when: rule metadata needs nested examples, tags, CWE/CAPEC-style mappings, or standard
  references that require a schema version bump.

## Baselines must fail closed

- Decision: Unknown JSON objects and malformed recognized baseline entries are usage errors.
- Evidence: An empty or partially parsed baseline can silently hide the fact that known-debt
  suppression did not apply. Recent tests cover raw lists, JSON reports, native AI BOMs, and SARIF.
- Alternative: Ignore malformed entries. Rejected because CI would appear green while evaluating a
  different debt set than intended.
- Revisit when: a migration tool exists that can explicitly normalize older report artifacts.

## Policy trust roots start as local digest allowlists, not signatures

- Decision: Add `local-content-digest-allowlist` policy trust roots as a fail-closed local content
  approval mechanism while keeping `signature_verified: false`.
- Evidence: `agentverify policy` already exposes composed policy sources and SHA-256 digests.
  Teams can use those digests in CI before full author/signature infrastructure exists, but a digest
  alone only proves byte identity, not who approved or produced the file.
- Alternative: Call digest matches "signed" or "verified" provenance. Rejected because it would
  overclaim authenticity and weaken future cryptographic trust semantics.
- Revisit when: cryptographic signed policy provenance has a concrete key/trust-root design and
  migration path from digest allowlists.

## Signed policy provenance should sign source digests

- Decision: Design cryptographic policy provenance around detached signatures over a manifest
  of exact composed policy source digests, not over normalized policy objects.
- Evidence: Current policy summaries already preserve source paths and SHA-256 bytes for every
  composed policy. Signing those byte digests avoids JSON canonicalization ambiguity and lets teams
  migrate from existing digest allowlists without changing policy composition semantics.
- Alternative: Sign normalized policy JSON or only the root policy digest. Rejected because
  normalization rules are easy to drift and root-only signatures can hide unapproved base-policy
  substitutions unless the composition graph is separately pinned.
- Revisit when: threshold signatures or a rule-catalog-version binding become necessary.

## Signed policy verification uses local Ed25519 key trust roots

- Decision: Implement policy signature verification with `cryptography` Ed25519 support and a
  fail-closed `local-key-signature` trust root, keeping it separate from digest allowlists.
- Evidence: AgentVerify already exports deterministic source-digest signing payload bytes. Verifying
  detached signatures over those bytes preserves exact source-byte provenance while avoiding policy
  JSON canonicalization drift. Local public-key trust roots keep CI offline and explicit.
- Alternative: Treat digest allowlist matches as signatures or make signature verification a remote
  trust service. Rejected because digest allowlists do not prove author authenticity, and remote
  trust would weaken offline reproducibility for the first implementation.
- Revisit when: threshold signatures, remote transparency logs, hardware-backed key attestations, or
  rule-catalog-version binding become concrete requirements.

## Benchmark release claims must be verifier-gated

- Decision: Treat benchmark result metadata as a release gate, not just explanatory JSON. Release
  workflows can require public-regression or sealed-holdout results, sealed status, label scope, and
  manifest provenance with `scripts/verify_benchmark_results.py`.
- Evidence: Checked-in public truth sets are visible during scanner development and therefore only
  support regression claims. The result schema already records `evaluation_kind`, `sealed`, digests,
  and `claim_scope`; enforcing those fields prevents accidental overclaiming.
- Alternative: Keep claim boundaries in prose only. Rejected because release notes and package pages
  are easy to copy from aggregates while overlooking caveats.
- Revisit when: release automation exists and can attach verifier output artifacts directly to tags.

## Benchmark result schemas are installed contracts

- Decision: Expose the benchmark-result JSON schema through `agentverify schema benchmark-result` and
  include it in wheel verification.
- Evidence: Benchmark results are intended to be attached to release notes and downstream validation
  flows; installed users should not need a source checkout to get the exact contract. A test asserts
  the packaged schema stays byte-identical to `benchmarks/benchmark-results-v1.schema.json`.
- Alternative: Leave the schema only under `benchmarks/`. Rejected because it makes report/policy
  contracts installable while benchmark-result contracts remain source-tree-only.
- Revisit when: benchmark schemas move into a versioned package namespace or release automation
  publishes schema artifacts independently.

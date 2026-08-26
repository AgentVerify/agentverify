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

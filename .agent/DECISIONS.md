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
  workflows can require public-regression or sealed-holdout results, sealed status, label scope,
  manifest provenance, and all-labels-passed claims with `agentverify benchmark verify`; the
  source-checkout `scripts/verify_benchmark_results.py` wrapper delegates to the same verifier.
- Evidence: Checked-in public truth sets are visible during scanner development and therefore only
  support regression claims. The result schema already records `evaluation_kind`, `sealed`, digests,
  and `claim_scope`; enforcing those fields prevents accidental overclaiming. Recomputing
  outcome-derived counts and metrics prevents aggregate result fields from drifting away from
  per-label evidence. Binding outcomes back to the digested label ids, metric keys, and expected
  values prevents same-sized but unrelated outcome lists from satisfying the gate.
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

## Signed policy CI fixtures must use ephemeral keys

- Decision: Prove signed-policy verification in CI with a generated in-memory Ed25519 key and
  throwaway public artifacts, not a checked-in private key or a pretend organizational trust root.
- Evidence: The detached signature verifier only needs the exported signing payload bytes, a
  signature bundle, and a public-key trust root. A reusable helper can generate those public
  artifacts in a temporary directory, require `agentverify policy --signature --trust-root
  --require-trusted`, and report that private-key material was ephemeral-only. The default CI
  workflow and installed-wheel distribution smoke now both exercise that path.
- Alternative: Commit a sample private key or leave the walkthrough as prose only. Rejected because
  durable sample keys invite misuse, while prose-only examples can drift from the CLI behavior.
- Revisit when: real release automation has an explicit organization trust-root and detached
  signature publishing process.

## Pre-commit integration is a release artifact

- Decision: Treat the pre-commit manifest, setup guide, and copyable local config as source-release
  contract files rather than README-only convenience text.
- Evidence: The README advertises the bundled `.pre-commit-hooks.yaml` manifest and local setup path.
  If a source distribution omits either the manifest or guide, downstream users cannot reproduce the
  advertised hook workflow. The local config intentionally uses `language: system` for an installed,
  reviewed AgentVerify build before a public release URL exists, while the bundled hook uses
  `language: python` for future tagged releases.
- Alternative: Leave the manifest and guide untested. Rejected because pre-commit installation is an
  adoption path and can silently drift from the CLI threshold or repository-wide scan requirement.
- Revisit when: a public remote/tag exists and the docs switch from local-hook-first to
  tagged-release-first instructions.

## Editor integrations get generated contract bundles

- Decision: Provide a reproducible exporter for editor/CI contract artifacts instead of relying only
  on scattered CLI examples.
- Evidence: Editor extensions and review bots need the report schema, rules schema, current rule
  catalog, and representative report shape together. `agentverify schema ...` and `agentverify rules
  --format json` already expose the primitives, but a generated bundle with a digest manifest makes
  local integration and release verification easier to automate. Promoting the exporter to
  `agentverify contracts` makes the contract available from installed wheels, while the
  source-checkout script remains a wrapper. Tests validate the exported rule catalog and sample
  report against the bundled schemas, and installed-wheel smoke tests require the CLI command to
  write every expected artifact.
- Alternative: Check in generated copies of the rule catalog and schemas. Rejected because generated
  copies would drift whenever rules or schemas change unless every catalog update also regenerated
  secondary artifacts.
- Revisit when: a published package or website hosts versioned schema URLs and editor plugins can
  fetch those directly.

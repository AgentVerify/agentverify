# AgentVerify state

## Current milestone

CI and integration polish on top of the schema-backed report, policy, baseline, SARIF, and rule
catalog workflows.

## Completed recently

- Added compact scan summaries for CI logs.
- Added deterministic `risk_summary` data to JSON reports and native AI BOM governance.
- Added bundled schemas for JSON reports, native AI BOMs, and policies.
- Versioned normal JSON reports with `report_format: AgentVerify JSON Report` and
  `schema_version: 1`.
- Hardened baseline parsing so unknown JSON and malformed report entries fail closed instead of
  behaving like empty baselines.
- Aligned example policies with all current high-severity approval-review rules.
- Added and validated a bundled rules-catalog schema so `agentverify rules --format json` has a
  first-class machine contract.
- Added a reusable distribution verifier that checks built wheels for every runtime schema file.
- Added a sealed holdout benchmark design to separate public regression metrics from unbiased
  evaluation claims.
- Added public holdout manifest/label templates while keeping real sealed labels out of the repo.
- Added benchmark evaluator metadata for public-regression versus sealed-holdout outputs.
- Added a benchmark result JSON schema and tests for checked-in and synthetic sealed outputs.
- Extended distribution verification to cover the wheel console-script entry point and optional
  installed-CLI smoke tests.
- Added a benchmark result verifier that validates result JSON and recomputes label/manifest digests.
- Added `agentverify policy PATH` to validate/explain composed policy provenance without scanning a
  repository and without treating content hashes as signatures.
- Added a bundled policy-summary schema and included it in wheel/content and installed CLI checks.
- Added local policy digest trust roots for `agentverify policy`, including `--require-trusted`
  gating while still reporting `signature_verified: false`.
- Added benchmark-result release guardrails: verifier flags can require public-regression or
  sealed-holdout metadata, sealed status, manifests, and label scopes; docs now spell out claim
  boundaries before publishing benchmark numbers.
- Bundled the benchmark-result schema behind `agentverify schema benchmark-result`, with distribution
  smoke coverage and a drift test against the canonical `benchmarks/benchmark-results-v1.schema.json`.
- Added a checked-in runnable policy trust-root example for the composed organization/repository
  policy pair, and extended installed-wheel smoke tests to require that trust root to pass.
- Added `agentverify schema` discovery output so installed users can list all bundled machine
  contracts from the same schema registry used by rendering and smoke tests.
- Added `agentverify policy --export-trust-root` so teams can generate a schema-v1 local digest
  allowlist directly from composed policy inputs, with installed-wheel smoke coverage that exports
  and then requires the generated trust root.
- Added exact local package reexport-chain attribution for AgentScope/PydanticAI provider-wrapper
  symbols, including direct/transitive/wildcard provider-model positives, rebound and filtered
  negatives, imported simple wrapper-factory positives with ambiguous/rebound negatives, and
  regenerated IR truth-set results now covering 1,466 labels.
- Extended distribution verification so release checks can require a source distribution containing
  README-linked examples, policy docs, benchmark contracts, and public truth sets.

## Current findings

- The rule catalog is now the authoritative runtime source for reporting metadata and policy rule
  validation. Keeping schemas synchronized with `RULE_CATALOG` prevents generated policy/editor
  tooling from drifting.
- Baseline handling is intentionally conservative: malformed recognized artifacts are usage errors;
  partial selected-path scans do not claim no-longer-reported counts.

## Blockers

- External publishing, trust-root configuration, issue creation, and repository-access-dependent
  work are intentionally deferred until the user grants access or explicit authorization.

## Next action

Continue toward the highest-value local P1/P2 work: additional real-world framework coverage
without broad name matching, cryptographic signed policy provenance design, or release artifact
checks that attach benchmark verification outputs once release packaging is explicit.

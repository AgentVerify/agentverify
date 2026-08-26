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

Continue toward the highest-value local P1/P2 work: signed policy provenance design, additional
installed-artifact checks, benchmark-result release documentation, or additional real-world framework
coverage.

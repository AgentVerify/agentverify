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
  regenerated IR truth-set results then covering 1,466 labels.
- Added literal-`__all__` star-import resolution for selected local callables used in Python Agent
  literal tool lists, with wildcard positive/filtered-negative IR labels and regenerated IR
  truth-set results now covering 1,469 labels.
- Added literal-visibility star-import resolution for simple local provider wrapper factories, with
  exported/static positives, a filtered negative, and regenerated IR truth-set results now covering
  1,474 labels.
- Added exact local reexport-chain resolution for simple provider wrapper factories, with
  direct/wildcard reexport positives, filtered/rebound negatives, and regenerated IR truth-set
  results now covering 1,487 labels.
- Added exact Python framework agent constructor aliases and selected local reexport/star-reexport
  resolution for import-proven AgentScope/CAMEL/Marvin-style constructors, with hidden-export and
  rebound negatives, and regenerated IR truth-set results now covering 1,496 labels.
- Preserved constructor provenance attributes for those exact framework agent aliases and local
  reexports, recording the origin module, imported symbol, and exact resolution mode while keeping
  the public IR truth set at 1,496 passing labels.
- Added OpenAI Agents SDK `agents.Agent` alias, named-reexport, and star-reexport regression labels
  for the same constructor-provenance contract, bringing the public IR truth set to 1,499 passing
  labels.
- Added Google ADK `google.adk.agents.Agent` alias, named-reexport, and star-reexport regression
  labels for generic framework-prefix constructor provenance, bringing the public IR truth set to
  1,502 passing labels.
- Added exact Semantic Kernel `semantic_kernel.agents.ChatCompletionAgent` constructor provenance
  through direct aliases plus local named/star reexports, bringing the public IR truth set to 1,505
  passing labels.
- Added direct, named-reexport, and star-reexport provenance coverage for the remaining exact Python
  framework constructor table entries: Qwen-Agent `Assistant`, Lagent `AgentForInternLM`, and MetaGPT
  `Role`, bringing the public IR truth set to 1,514 passing labels.
- Added a concrete signed policy provenance design that keeps digest allowlists separate from author
  authenticity and specifies detached source-digest payloads plus local key trust roots.
- Added `agentverify policy --export-signing-payload` and a bundled policy-signing-payload schema so
  composed policy source digests can be handed to external signing tools without claiming signature
  verification.
- Added bundled policy-signature and policy-key-trust-root schemas for the planned detached
  signature bundle and local Ed25519 key trust-root contracts, still without reporting signature
  verification.
- Implemented fail-closed detached Ed25519 policy signature verification for `agentverify policy`
  with `--signature` plus a local key trust root, including signed-manifest digest coverage,
  machine-readable failure reasons, schema validation, and CLI gating via `--require-trusted`.
- Added a signed-policy dry-run walkthrough that generates an ephemeral key only in a temporary
  directory, demonstrates detached signature verification, and warns production users to rely on
  their own key-management workflow.
- Extended source-distribution verification to require `pyproject.toml`, so source releases carry
  the runtime dependency declaration that signed policy verification relies on.
- Extended installed-wheel smoke verification to install runtime dependencies and exercise a full
  ephemeral detached-policy-signature verification path through the installed `agentverify`
  executable.
- Extended distribution verification so release checks can require a source distribution containing
  README-linked examples, policy docs, benchmark contracts, and public truth sets.
- Extended source-distribution verification to require the checked public benchmark result outputs
  alongside their labels, so release artifacts carry both benchmark contracts and verifier evidence.
- Added installed CLI benchmark result verification via `agentverify benchmark verify`, backed by
  the bundled benchmark-result schema, shared with the source-checkout verifier script, and covered
  by installed-wheel smoke tests.
- Added explicit all-labels-passed benchmark verification output and a `--require-all-passed` gate,
  so public regression release checks can fail closed on honest failing-label result files while
  still allowing failed sealed-holdout metrics to be validated when intentionally published.

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
without broad name matching, CI/editor adoption polish, or release-artifact checks that attach
benchmark verifier logs once release publishing is explicit.

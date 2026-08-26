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
- Added exact module-qualified Python framework constructor provenance for top-level absolute imports
  such as AgentScope, OpenAI Agents SDK, Google ADK, Semantic Kernel, Qwen-Agent, Lagent, and MetaGPT,
  with root-rebound, constructor-attribute-rebound, and near-package negatives, bringing the public IR
  truth set to 1,525 passing labels.
- Added a narrow exact absolute star-import path for the same Python framework constructor families,
  with ambiguous-star, shadowed-name, and near-package negatives, bringing the public IR truth set to
  1,536 passing labels.
- Extended same-block local Agent factory-return resolution to exact module-qualified framework
  constructors, with AgentScope/OpenAI/Google ADK factory positives and conditional/forward/rebound
  negatives, bringing the public IR truth set to 1,545 passing labels.
- Extended native TypeScript provider typed-parameter attribution to non-exported `const` arrow
  helpers with balanced block bodies under the same call-site consensus rule, while exported,
  mixed-call-site, escaped, and expression-bodied arrows remain unresolved; regenerated public IR
  truth-set results now cover 1,552 labels.
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
- Added a reusable ephemeral signed-policy verification helper and wired default CI plus installed
  wheel smoke checks through that same helper, proving detached Ed25519 policy verification without
  committing durable private-key material.
- Extended distribution verification so release checks can require a source distribution containing
  README-linked examples, policy docs, benchmark contracts, and public truth sets.
- Extended source-distribution verification to require the checked public benchmark result outputs
  alongside their labels, so release artifacts carry both benchmark contracts and verifier evidence.
- Added installed CLI benchmark result verification via `agentverify benchmark verify`, backed by
  the bundled benchmark-result schema, shared with the source-checkout verifier script, and covered
  by installed-wheel smoke tests.
- Added a copyable local pre-commit config and tests for both the future release hook manifest and
  current local setup, and extended source-distribution verification to require those pre-commit
  adoption artifacts.
- Added an editor/CI contract exporter that writes the report schema, rules schema, current rules
  catalog, optional sample report, and digest manifest, with tests and source-distribution coverage
  for the exporter and integration guide.
- Promoted editor/CI contract export into the installed CLI as `agentverify contracts`, with the
  source-checkout script reduced to a wrapper and installed-wheel distribution smoke coverage that
  exports the schema/catalog/sample-report bundle.
- Added a checked Language Server Protocol-style editor diagnostics example derived from the
  `cases/approval_callback_bypass` report, including tests that regenerate the mapping from a real
  scan and source-distribution coverage for the linked example artifact.
- Added a copyable GitHub Actions policy-gate workflow that uses read-only repository permissions,
  validates policy composition before scanning, emits compact summary output, requires suppression
  expiry, and is now required in source-distribution verification.
- Added explicit all-labels-passed benchmark verification output and a `--require-all-passed` gate,
  so public regression release checks can fail closed on honest failing-label result files while
  still allowing failed sealed-holdout metrics to be validated when intentionally published.
- Hardened benchmark result verification to reject cross-field drift between labels, outcomes,
  passed totals, and outcome-derived metrics, so release gates cannot be satisfied by editing
  aggregate result fields without matching per-label evidence.
- Wired the default CI workflow to run the installed CLI benchmark verification gate on checked-in
  public regression results, with a workflow regression test and release-checklist guidance.
- Bound benchmark result outcomes back to the digested label file's label scope, label ids,
  rule/check ids, and expected values before accepting aggregate metrics.
- Extended TypeScript model literal binding so module-level template strings composed only from
  earlier immutable literal constants resolve as exact model ids for native OpenAI/Anthropic calls
  and official AI SDK provider calls; runtime, mutable, forward, shadowed, rebound, and unknown
  template expressions remain unresolved.
- Added a checked copyable GitHub SARIF upload workflow in `examples/github-code-scanning.yml`,
  documented it separately from policy enforcement, and made it a required source-distribution
  artifact so SARIF adoption guidance survives release packaging.
- Added two explicit TypeScript unknown-template negative model-binding labels so runtime-derived
  template interpolations remain guarded in the public IR regression set.
- Added a checked GitHub code-scanning SARIF payload example generated from
  `cases/approval_callback_bypass`, with a regression test proving it matches real renderer output
  and source-distribution verification requiring the artifact.
- Added a checked copyable GitHub benchmark-verification workflow that runs the installed
  `agentverify benchmark verify` public-regression/all-labels-passed gate, validates the JSON output,
  uploads it as a workflow artifact, and is now required in source distributions.
- Extended Python filesystem mutation detection to follow same-function, statement-ordered callable
  alias chains while every hop copies an already proven compatible `os`/`shutil` mutator. Added
  positive and negative rule/IR labels.
- Added explicit CAMEL and Marvin regression coverage for exact module-qualified and absolute
  star-import Python framework agent constructors, plus matching module-attribute-rebound and
  star-shadowed negative guards, bringing that slice of the public IR truth set to 1,567 labels.
- Extended `agentverify contracts` manifest artifacts with explicit `kind`, `contract`, and
  `required` metadata while preserving path/byte/digest fields, so editor and CI integrations can
  distinguish report schemas, rules schemas, rules catalogs, and optional sample reports without
  hard-coding filenames.
- Added a bundled `editor-contract-manifest` schema and runtime validation for `agentverify
  contracts`, with CLI schema discovery and installed-wheel smoke checks proving the schema ships
  with release artifacts.
- Added `agentverify contracts --verify-dir` to validate copied editor/CI contract bundles against
  their manifest schema, required artifact entries, recomputed byte counts and SHA-256 digests, and
  bundled rules/sample-report schemas. Installed-wheel smoke now exports and verifies a bundle.
- Hardened contract-bundle verification so malformed manifests cannot cause verification to read
  parent-relative, nested, absolute, or otherwise non-basename artifact paths.
- Added a bundled `editor-contract-verification` schema and runtime validation for
  `agentverify contracts --verify-dir`, with CLI discovery and installed-wheel smoke coverage.
- Added a malformed-manifest regression proving verifier failure output stays schema-valid and
  normalizes invalid artifact metadata instead of leaking unexpected JSON types.
- Added a bundled `benchmark-verification` schema and runtime validation for
  `agentverify benchmark verify` JSON output, and upgraded the copyable GitHub benchmark workflow to
  validate its uploaded verifier artifact against that schema.
- Extended Python registered-class network propagation to exact local module-qualified constructors,
  while preserving local module-alias shadowing as an unresolved counterexample; the current
  regenerated IR truth-set results now cover 1,574 passing labels after the later TypeScript
  CommonJS Google coverage.
- Extended native TypeScript provider SDK CommonJS proof to exact top-level direct and aliased
  `GoogleGenAI` named destructuring, with a scoped-require negative guard; regenerated IR truth-set
  results now cover 1,574 passing labels.
- Pinned native TypeScript provider SDK CommonJS named-destructuring aliases for OpenAI and
  Anthropic alongside the existing Google GenAI case, proving constructor and model attribution for
  `const { OpenAI: Alias } = require("openai")` and
  `const { Anthropic: Alias } = require("@anthropic-ai/sdk")` while keeping scoped named requires
  unresolved; regenerated IR truth-set results then covered 1,584 passing labels.
- Added TypeScript native-provider type-only negative coverage for `import type` and inline
  `import("openai").default...` annotations, reflecting a Roo Code corpus pattern where SDK types
  describe tool schemas without proving runtime provider construction.
- Pinned an MCP TypeScript quickstart-shaped lazy `Anthropic` class getter with an immutable
  module-level model literal in the local fixture, so provider and exact model attribution fail fast
  without relying only on the cached real repository; regenerated IR truth-set results then covered
  1,586 passing labels.
- Added a local negative IR label for class-field native SDK calls whose provider is proven but
  model argument is a method parameter, keeping exact model attribution unresolved when no literal or
  immutable module-level binding is available; regenerated IR truth-set results then covered 1,587
  passing labels.
- Added a named OpenAI `import type { OpenAI as ... } from "openai"` negative to the TypeScript
  native-provider type-only fixture, mirroring Roo Code's SDK type-only tool-schema pattern and
  keeping exact provider/model attribution tied to runtime value-import/constructor proof;
  regenerated IR truth-set results then covered 1,588 passing labels.
- Added a checked `examples/benchmark-verification.json` public-regression verifier artifact that is
  regenerated by the installed CLI shape, schema-validated in tests, linked from release guidance,
  and required in source distributions.
- Required `benchmarks/holdout-labels.template.json` in source distributions and README artifact
  links, so the sealed-holdout public scaffold ships both the manifest and label templates promised
  by `benchmarks/holdout-design.md`.
- Added bundled `holdout-manifest` and `holdout-labels` schemas exposed through
  `agentverify schema`, validating the checked public sealed-holdout setup templates and extending
  installed-wheel schema smoke coverage to 15 schemas.
- Added `agentverify holdout validate` so installed CLIs can validate public or private holdout
  manifest/label setup files directly against the bundled schemas, with text/JSON output, fail-closed
  exit code 2 on malformed inputs, README/checklist guidance, tests, and installed-wheel smoke
  coverage.
- Wired the default CI workflow and copyable GitHub benchmark verification workflow to run
  `agentverify holdout validate` on the checked public setup templates, with regression tests so the
  benchmark release recipe keeps validating setup files as well as result files.
- Extended benchmark result and verification contracts with derived `failed` counts and
  `failure_summary` buckets for observation, anchor, and source-snippet mismatches. Regenerating the
  public truth sets exposed and corrected a stale `AV-NET001` reporting-rule label for exact local
  module-qualified registered-class network propagation; reporting-rule labels now pass 719/719 and
  IR labels then passed 1,588/1,588 with zero mismatch summaries.
- Hardened source/wheel distribution smoke verification to preserve and require the installed CLI's
  benchmark failure summaries, so packaging checks now prove the `failed` and `failure_summary`
  contract survives installation rather than only checking label counts.
- Extended TypeScript exact model attribution to immutable module-level literal object maps, so
  native SDK and official AI SDK calls can resolve `MODEL_IDS.chat`-style model IDs while mutable
  object properties and nonliteral object values remain unresolved; regenerated public IR truth-set
  results then covered 1,595 passing labels.
- Extended that TypeScript object-map proof to exact literal bracket reads such as
  `MODEL_IDS["chat"]` while keeping dynamic bracket keys unresolved; regenerated public IR truth-set
  results then covered 1,600 passing labels.
- Extended exact literal bracket reads to quoted object-map keys such as `MODEL_IDS["chat-model"]`
  and hardened object-map stability so any bracket member write invalidates the map; regenerated
  public IR truth-set results then covered 1,605 passing labels.
- Added exact TypeScript AI SDK local named-reexport proof for supported `@ai-sdk/*` provider
  instance/factory symbols, including a bounded transitive local export hop, while ambiguous
  reexports and local shadowing remain unresolved; regenerated public IR truth-set results then covered
  1,613 passing labels.
- Added real Activepieces negative labels for its source-visible but implementation-hidden
  `@activepieces/ai-providers` `createLanguageModel({ provider, modelId })` workspace wrapper and
  Cloudflare `@ai-sdk/openai-compatible` custom endpoint branch; regenerated public IR truth-set
  results then covered 1,616 passing labels.
- Added exact official TypeScript AI SDK Azure OpenAI attribution for `@ai-sdk/azure` imports and
  `createAzure` factory/configured embedding calls, while allowing only endpoint-neutral
  `spreadIfDefined('apiVersion', ...)` spreads and keeping baseURL spreads unresolved. A real
  Activepieces Azure embedding provider is now pinned; regenerated public IR truth-set results now
  covered 1,622 passing labels.
- Extended exact local TypeScript AI SDK named-reexport regression coverage to the Azure factory
  path, including a provider/model positive and provider/model negatives for a baseURL-spread
  reexport. Regenerated public IR truth-set results then covered 1,626 passing labels.
- Added exact TypeScript AI SDK local star-reexport proof for single-symbol OpenAI/Azure barrels,
  including a local transitive Azure `export *` hop, while duplicate star-barrel provenance remains
  unresolved. Regenerated public IR truth-set results then covered 1,631 passing labels.
- Added exact TypeScript AI SDK CommonJS named-destructuring proof for top-level supported
  `@ai-sdk/*` provider symbols, including OpenAI and Azure configured embedding positives plus a
  rebound-alias negative. Regenerated public IR truth-set results then covered 1,637 passing labels.
- Added exact TypeScript OpenAI Agents sandbox inventory for `@openai/agents/sandbox`
  `SandboxAgent` direct assignments and literal `capabilities: [shell()]` entries. SDK sandbox shell
  execution is recorded separately from host-local shell execution, with local near/rebound negatives
  and two real OpenAI Agents JS example positives. Regenerated public IR truth-set results then
  covered 1,659 passing labels.
- Extended TypeScript OpenAI Agents sandbox inventory to same-file helper returns of exact
  `@openai/agents/sandbox` `SandboxAgent` constructors, preserving SDK-sandbox shell classification
  and keeping near/rebound/conditional helper forms unresolved. Local helper fixtures plus
  shared-session and memory multi-agent OpenAI Agents JS examples are pinned. Regenerated public IR
  truth-set results then covered 1,686 passing labels.
- Extended exact TypeScript OpenAI Agents sandbox capability inventory to unshadowed `filesystem()`
  and `memory()` factories in literal capability lists. The scanner records SDK-sandbox filesystem
  and memory reachability separately from host-local filesystem risk, while rebounded capability
  aliases stay unresolved. Local fixtures plus OpenAI Agents JS `memory.ts` and
  `memory-generation.ts` labels raised regenerated public IR truth-set results to 1,712 passing
  labels.
- Extended exact TypeScript OpenAI Agents sandbox capability inventory to unshadowed `skills()`
  factories in literal capability lists, recording `skill-loading` as SDK-sandbox reachability while
  leaving aggregate `Capabilities.default()` and rebounded skill aliases unresolved. Local fixtures
  plus OpenAI Agents JS sandbox coding/capability/docs examples raised regenerated public IR
  truth-set results to 1,729 passing labels.
- Added exact TypeScript OpenAI Agents sandbox runtime-client inventory for
  `@openai/agents/sandbox/local` `UnixLocalSandboxClient` and `DockerSandboxClient` constructors
  wired into `run(..., { sandbox: { client/session } })`. Direct client bindings, inline client
  construction, one exact `client.create(...)` session binding, and object-shorthand `{ session }`
  now produce agent `configured-by` `sandbox-runtime` control edges. Rebounded local-client imports
  and unknown sessions stay unresolved. Local fixtures plus four OpenAI Agents JS examples raised
  regenerated public IR truth-set results to 1,747 passing labels.
- Extended that runtime-client inventory to exact ternary client initializers whose outer expression
  is a conditional and whose branches each contain exactly one unshadowed sandbox-local
  `DockerSandboxClient`/`UnixLocalSandboxClient` constructor. The scanner records one
  `conditional-local` `sandbox-runtime` control with Docker/Unix options and carries it through
  direct `client.create(...)` session bindings into `run(..., { sandbox: { session } })`; half-known
  ternaries remain unresolved. Local positive/negative fixtures plus OpenAI Agents JS
  `examples/sandbox/basic.ts` and `examples/sandbox/resume.ts` raised regenerated public IR
  truth-set results to 1,755 passing labels.
- Extended sandbox runtime session binding through exact local `const resumableClient = client as ...`
  aliases and `resumedSession = await resumableClient.resume(...)` assignments. The resumed session
  inherits the original proven `sandbox-runtime` control rather than creating a second control;
  unknown resumable aliases remain unresolved. Local positive/negative fixtures plus OpenAI Agents JS
  `examples/sandbox/resume.ts` and `examples/sandbox/memory.ts` raised regenerated public IR
  truth-set results to 1,759 passing labels.
- Added exact OpenAI Agents JS extension sandbox runtime inventory for
  `@openai/agents-extensions/sandbox/blaxel` `BlaxelSandboxClient` and
  `@openai/agents-extensions/sandbox/cloudflare` `CloudflareSandboxClient`, including
  `new Runner({ sandbox: { client } })` bindings and `runner.run(agent, ...)` agent
  `configured-by` edges. Unknown Runner sandbox clients remain unresolved. Local fixtures plus
  Blaxel/Cloudflare OpenAI Agents JS examples raised regenerated public IR truth-set results to
  1,768 passing labels.
- Extended exact local OpenAI Agents JS sandbox session binding to inline
  `await new DockerSandboxClient(...).create(...)` and
  `await new UnixLocalSandboxClient(...).create(...)` assignments when the constructor import is
  exact and unshadowed. The created session now links `run(..., { sandbox: { session } })` back to a
  `sandbox-runtime` control, while unknown inline constructors remain unresolved. Local
  positive/negative fixtures plus OpenAI Agents JS
  `examples/docs/sandbox-agents/conversation-identity.ts` raised regenerated public IR truth-set
  results to 1,774 passing labels.
- Strengthened source-release verification for the packaged GitHub workflow examples:
  `verify_sdist()` now checks benchmark verifier output/schema/upload, policy-gate
  permission/policy/summary/expiry arguments, and code-scanning SARIF permission/upload contracts.
  Negative distribution tests prove the sdist verifier rejects removed verifier upload, missing
  policy argument, and missing SARIF upload cases.

## Current findings

- The rule catalog is now the authoritative runtime source for reporting metadata and policy rule
  validation. Keeping schemas synchronized with `RULE_CATALOG` prevents generated policy/editor
  tooling from drifting.
- Editor/CI contract export is now an installed-package behavior. Integrations can ask any
  AgentVerify installation for a digest-manifested report schema, rules schema, current rules
  catalog, and optional sample report without relying on source-tree scripts.
- Editor diagnostic integrations should preserve `result_kind`, `confidence`, `fingerprint`, and
  `ir_path` in diagnostic metadata; otherwise they lose the distinction between review signals,
  policy-gated findings, and rerun correlation.
- CI policy-gate examples should stay separate from SARIF upload workflows so deliberate policy
  failures do not prevent diagnostic ingestion.
- Baseline handling is intentionally conservative: malformed recognized artifacts are usage errors;
  partial selected-path scans do not claim no-longer-reported counts.
- TypeScript model binding now has one bounded composition rule: direct quoted constants and
  module-level backtick templates whose interpolations are all earlier immutable literal constants
  can carry exact model provenance; other expression forms are withheld rather than guessed.
- Code-scanning adoption artifacts now distinguish two local examples: SARIF upload belongs in the
  copyable `examples/github-code-scanning.yml` workflow with `security-events: write`, while
  enforcement-only gates belong in `examples/github-policy-gate.yml` without code-scanning upload
  permissions.
- The checked SARIF example preserves the same integration metadata GitHub receives from the CLI:
  rule descriptors, `agentverify/v1` partial fingerprints, source locations, result kind,
  confidence, analysis details, and Agent IR paths.
- Benchmark release-claim guardrails now have a copyable CI artifact, not just prose and this
  repository's internal CI: `examples/github-benchmark-verify.yml` uses only read permission and
  archives schema-validated installed CLI verifier JSON for release review.
- Editor/CI contract manifests now identify each artifact's role directly through `kind`,
  `contract`, and `required` fields while retaining SHA-256 digests for reproducibility.
- The editor/CI contract manifest is now itself schema-backed via `agentverify schema
  editor-contract-manifest`, matching the broader installed machine-contract pattern.
- Copied editor/CI contract bundles can now be independently verified with `agentverify contracts
  --verify-dir`, giving downstream tools a fail-closed integrity check before loading schemas or rule
  catalogs.
- Contract-bundle artifact paths are intentionally basename-only; invalid manifest paths are reported
  as verification failures before any artifact file is read.
- Contract-bundle verification output is now itself schema-backed via `agentverify schema
  editor-contract-verification`, so editor bootstrap and CI logging code can validate verifier JSON
  the same way they validate exported manifests.
- Verifier failure output should stay consumable even when manifest metadata fields are malformed;
  invalid `kind`, `contract`, and `required` values are normalized to `null` in artifact results.
- Benchmark release evidence now has two installable contracts: `benchmark-result` for measured
  result files and `benchmark-verification` for the release-gate artifact emitted after digest,
  outcome, and claim-boundary checks.
- Benchmark release tooling now has a checked verifier-output example, not only a workflow recipe:
  `examples/benchmark-verification.json` matches the current `agentverify benchmark verify
  --require-evaluation-kind public-regression --require-all-passed` output and is source-release
  required.
- Source-release verification now protects both public sealed-holdout templates:
  `holdout-manifest.template.json` for samples and `holdout-labels.template.json` for adjudicated
  label shape.
- Sealed-holdout setup templates are now machine contracts: installed CLIs expose
  `agentverify schema holdout-manifest` and `agentverify schema holdout-labels`, and the checked
  templates validate against those schemas before any private labels are introduced.
- Holdout setup validation is now an installed CLI behavior: `agentverify holdout validate` validates
  manifest and/or labels files with the bundled schemas and reports per-file schema/parse/read errors
  without claiming sealed benchmark success or trust authenticity.
- Benchmark release workflows should validate setup artifacts and result artifacts separately:
  `agentverify holdout validate` catches manifest/label shape drift, while `agentverify benchmark
  verify` checks generated result JSON, digests, outcomes, and claim-boundary gates.
- Benchmark result JSON now distinguishes detection failures from label freshness failures:
  `failure_summary.observation_mismatch` tracks expected-versus-observed scanner mismatches, while
  `anchor_mismatch` and `source_mismatch` expose stale anchors or expected source snippets that can
  otherwise be hidden by unchanged precision/recall metrics.
- Python registered-class network propagation now accepts exact `module_alias.ClassName()` calls only
  when `module_alias` resolves to one local imported module and is unrebound in the method; locally
  shadowed module aliases, mutable fields, duplicate classes, and rebound constructors remain
  unresolved.
- Python filesystem callable aliasing is deliberately narrow: local alias chains may copy already
  proven same-function callable bindings, but aliases before source proof, rebound alias targets,
  incompatible operation families, and imported wrapper helpers remain unresolved.

## Blockers

- External publishing, trust-root configuration, issue creation, and repository-access-dependent
  work are intentionally deferred until the user grants access or explicit authorization.

## Next action

Continue toward the highest-value local P1/P2 work: additional real-world framework coverage
without broad name matching, concrete CI/editor integration fixtures, or release-artifact checks that
stay local until release publishing is explicit.

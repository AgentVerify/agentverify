# AgentVerify findings

## Durable facts

- The repository contains a 71-repository pinned research corpus and schema-v123 engine benchmark
  outputs.
- The runtime catalog currently contains 24 enabled reporting rules.
- JSON reports, AI BOMs, policies, and rule-catalog JSON now have bundled schemas.
- A freshly rebuilt wheel includes all fifteen runtime schemas; a verifier script now guards that
  package artifact expectation.
- Policy evaluation occurs after baseline filtering and preserves matched findings in all report
  formats.
- Published precision/recall numbers still describe public seed/regression labels only; the holdout
  design records how to produce an unbiased sealed evaluation later.
- The evaluator already accepts alternate `--labels` paths, so sealed labels can be supplied by CI or
  a trusted maintainer without committing them publicly.
- Benchmark result JSON now records evaluation kind, label scope, input digests, sealed status, and
  claim scope, reducing the risk that public regression metrics are reused as holdout claims.
- Benchmark result JSON has a checked-in schema that validates both public rule/IR result files and
  synthetic sealed-holdout outputs.
- The benchmark-result schema is now also exposed by the installed CLI, and tests assert it remains
  byte-identical to the canonical benchmark schema in the repository.
- Distribution verification now proves the wheel declares `agentverify = agentverify.cli:main`; the
  optional smoke mode installs the wheel and exercises version, bundled schema, policy summary, and
  safe-example scan commands through the installed executable.
- Distribution verification can now also require source distributions to contain the README-linked
  example policies, safe-agent sample, policy/code-scanning docs, benchmark schema/templates, and
  public truth sets.
- Source-distribution verification now treats the public benchmark result JSON files as named release
  artifacts, so a release archive cannot include labels without their checked verifier outputs.
- Benchmark verification now recomputes `labels_sha256` and optional `manifest_sha256`, preventing
  result files from drifting away from their declared inputs.
- Benchmark verification can now fail release workflows unless result files declare the required
  evaluation kind, label scope, sealed status, and manifest provenance, reducing the chance of
  accidentally publishing public regression metrics as unbiased accuracy claims.
- Benchmark result verification is now an installed CLI behavior (`agentverify benchmark verify`)
  using the bundled benchmark-result schema; its own verifier JSON is also validated by a bundled
  benchmark-verification schema exposed through `agentverify schema`. The source-checkout script
  delegates to the same package code, and distribution smoke tests prove the command works from a
  built wheel.
- Benchmark verification distinguishes artifact validity from benchmark success: verification JSON
  now reports `all_labels_passed`, and release workflows can require `--require-all-passed` when
  claiming that public regression labels all pass.
- Benchmark verification now treats benchmark result aggregates as derived evidence: it rejects
  mismatches between `labels` and outcome count, `passed` and per-outcome pass status, or `metrics`
  and the expected/observed outcome matrix.
- Benchmark outcomes are now tied to their declared label file, not just the label count: verifier
  checks reject changed label scopes, outcome ids, rule/check ids, or expected values that do not
  match the digested labels.
- A checked verifier-output example now covers the release-gate artifact shape:
  `examples/benchmark-verification.json` is expected to match current public-regression
  `agentverify benchmark verify` output, validate against the bundled benchmark-verification schema,
  and ship in source distributions.
- The sealed-holdout public scaffold depends on two templates, not only the manifest: source
  releases must include both `benchmarks/holdout-manifest.template.json` and
  `benchmarks/holdout-labels.template.json` so private-label workflows can start from the same
  reviewed shape described in `benchmarks/holdout-design.md`.
- The public sealed-holdout scaffold is now schema-backed without exposing private labels:
  `agentverify schema holdout-manifest` validates sample-manifest shape and
  `agentverify schema holdout-labels` validates adjudicated-label shape for the checked templates.
- Installed CLIs now provide `agentverify holdout validate` as the direct setup-file check for public
  templates or private holdout manifest/label files; it validates against the bundled holdout schemas
  and returns per-file errors without treating setup validity as sealed-result validity.
- The default CI workflow and copyable benchmark-verification workflow now run setup validation
  separately from benchmark result verification, so public holdout template drift is caught before
  release-note tooling consumes result metrics.
- The checked-in GitHub CI workflow now exercises `agentverify benchmark verify
  --require-evaluation-kind public-regression --require-all-passed`, so public regression artifact
  drift is caught during normal pull-request checks rather than only during manual release review.
- Pre-commit adoption artifacts are now part of the release contract: `.pre-commit-hooks.yaml`,
  `docs/pre-commit.md`, and `examples/pre-commit-config.yaml` are required source-distribution
  files, while tests assert that the bundled release hook uses `language: python` and the local
  copyable config uses `language: system` with repository-wide `pass_filenames: false` scanning.
- Editor/CI integrations can now consume a generated local contract bundle from an installed
  AgentVerify package instead of copying commands from prose or depending on a source checkout:
  `agentverify contracts` validates and exports report/rules schemas, the current `agentverify rules
  --format json` payload, an optional sample report, and a digest manifest. Manifest artifact entries
  now include `kind`, `contract`, and `required` metadata in addition to path/byte/SHA-256 fields, so
  integrations can consume the bundle without inferring semantics from filenames. The manifest is
  itself validated by a bundled `editor-contract-manifest` schema exposed through `agentverify
  schema`; copied bundles can be checked with `agentverify contracts --verify-dir`, which recomputes
  byte counts and SHA-256 digests and validates the rules catalog/sample report against the schemas
  in the bundle. The verifier rejects parent-relative, nested, absolute, NUL-containing, and
  otherwise non-basename artifact paths before reading artifact files. The verifier JSON is also
  validated by a bundled `editor-contract-verification` schema exposed through `agentverify schema`.
  The source script is a compatibility wrapper, the guide remains a required source-distribution
  artifact, and distribution smoke tests prove the built wheel exports, verifies, and schema-checks
  the bundle contracts.
- The editor integration guide now includes a checked LSP-style diagnostic mapping example derived
  from `cases/approval_callback_bypass`. Tests regenerate the example from `agentverify scan
  --format json`, proving the documented mapping preserves evidence paths, zero-based ranges,
  severity mapping, fingerprints, result kinds, confidence, and IR paths.
- GitHub Actions policy gates now have a checked, source-distribution-required workflow example:
  `examples/github-policy-gate.yml` uses only `contents: read`, validates policy composition before
  scanning, emits summary output, and requires suppression expiry. Tests assert those guardrails and
  docs link to the workflow from both policy and code-scanning guidance.
- Policy composition can now be inspected without scanning. The policy summary intentionally reports
  `signature_verified: false`, preserving the distinction between content integrity and author trust.
- Policy summary JSON is now schema-backed and included in distribution verification, matching the
  existing report/BOM/policy/rules machine-contract pattern.
- Policy digest trust roots can now make local composition approval fail closed without pretending to
  verify signatures; this is a useful precursor, not a replacement, for cryptographic provenance.
- The checked-in example policy trust root turns the digest-allowlist workflow into a copyable,
  installed-wheel-smoked command rather than a prose-only feature.
- Schema discovery is now an installed CLI behavior (`agentverify schema`), reducing documentation
  dependence when new machine contracts are added.
- Policy digest trust roots are now generated by the CLI from the same composed source/digest list
  used by `agentverify policy`, reducing manual hash-copy errors while preserving the non-signature
  trust model.
- Signed policy provenance should verify detached signatures over exact composed policy source
  digests, preserving byte-level reproducibility and avoiding JSON canonicalization drift.
- Policy signing payload export now provides that exact source-digest manifest as an installed,
  schema-backed CLI artifact, while still leaving `signature_verified: false`.
- Detached Ed25519 policy signatures now verify against local key trust roots over the exact
  exported source-digest signing payload bytes. Digest allowlists remain a separate content
  approval workflow and still report `signature_verified: false`.
- The signed-policy CI path can be tested without durable secrets: the reusable smoke helper exports
  the signing payload, signs the exact bytes with an in-memory ephemeral Ed25519 key, writes only the
  detached signature bundle and public-key trust root, and then requires `agentverify policy
  --signature --trust-root --require-trusted` to pass.
- Python provider-wrapper attribution now follows exact selected local package reexport chains for
  AgentScope/PydanticAI symbols when every alias hop is unrebound; star imports from proven local
  reexport modules respect literal `__all__`/non-underscore visibility; simple imported local wrapper
  factories can carry literal/parameter model attribution when they have one proven return path, and
  those factory summaries now survive exact local reexport chains plus literal-visibility star
  imports; rebound, ambiguous, and generic same-named wrapper forms remain unresolved.
- Python framework agent constructor attribution now carries exact import-proven constructor aliases
  through selected local reexport and star-reexport facades when names remain unrebound and visible
  under literal `__all__` rules, including OpenAI Agents SDK `agents.Agent` and Google ADK
  `google.adk.agents.Agent`, plus exact Semantic Kernel
  `semantic_kernel.agents.ChatCompletionAgent`, Qwen-Agent `Assistant`, Lagent `AgentForInternLM`,
  and MetaGPT `Role`. Top-level absolute module imports of those frameworks now also prove
  module-qualified constructor calls when the imported root is unique/unrebound and the constructor
  attribute is not reassigned, including explicit CAMEL and Marvin module-qualified positives plus
  attribute-rebound negatives. A narrow absolute star-import path now proves the same exact constructor
  families, including CAMEL and Marvin, only when one supported framework module can export the
  constructor name and the consumer does not shadow it; explicit CAMEL/Marvin shadowing negatives
  pin that boundary. Same-block local function factories now preserve those exact
  framework constructor identities through direct returns, including module-qualified returns such
  as `adk_agents.Agent(...)`, while conditional, forward, and rebound factories remain unresolved.
  Agent components for those proven aliases now include constructor module, imported symbol, and
  resolution-mode provenance; hidden exports, rebound imports, rebound constructor attributes,
  ambiguous star imports, and same-named ordinary local constructors remain unresolved.
- TypeScript native provider SDK model attribution now follows non-exported `const` arrow helpers
  with balanced block bodies through the same same-file typed-parameter call-site consensus used for
  function declarations. Exported arrows, mixed constructor/non-provider call sites, escaped
  callbacks, and expression-bodied arrows remain unresolved so the scanner does not infer provider
  identity from type annotations alone.
- TypeScript model literal binding supports direct immutable module string constants and one bounded
  template form: a module-level backtick literal may resolve only when every `${...}` expression is a
  simple identifier bound to an earlier stable immutable literal constant. Runtime expressions,
  unknown template expressions, forward constants, mutable/rebound constants, imported names, and
  shadowed constants remain unresolved.
- Python filesystem mutation attribution now supports same-function, statement-ordered local alias
  chains for already proven compatible `os`/`shutil` mutator callables. Calls before the source
  alias is proven, rebound alias targets, incompatible operation families, imported wrappers, and
  arbitrary same-named functions remain unresolved.
- Python imported literal tool-list attribution now resolves star imports from selected local
  callable modules when the callable is visible through literal `__all__`/non-underscore exports and
  the Agent use is not locally shadowed.
- Python registered-class network propagation now follows exact local module-qualified constructor
  calls such as `parsers.UrlParser().call(...)` when the module alias resolves to one local file and
  is not rebound in the method. A local shadowed-module fixture keeps the boundary pinned, and the IR
  truth set later moved to 1,574 passing labels after TypeScript CommonJS Google coverage, while
  `IR-PY-IMPORTED-CLASS-NETWORK` remains pinned at 11 positives and 4 negatives.
- Native TypeScript provider SDK CommonJS proof now accepts exact top-level named destructuring for
  Google GenAI, including direct and aliased bindings, under the same immutable default-endpoint
  constraints as other native SDK constructors. Scoped named requires remain unresolved, and the IR
  truth set now covers 1,574 passing labels.

## Hypotheses

- Schema-backed machine contracts reduce adoption friction for CI, editor, and governance tooling
  more effectively than prose-only documentation.
- A separately sampled sealed holdout benchmark will become the next credibility bottleneck once the
  public regression corpus continues to grow.

## Implications

- Keep every contract change covered by runtime/schema consistency tests.
- Avoid external trust/authenticity claims until there is an explicit trust-root design.
- Keep reexport support narrow and symbol-proven; do not fall back to generic `Client`, `Agent`, or
  same-named wrapper classes without package provenance.

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
- Benchmark result and verifier artifacts now include derived `failed` counts plus
  `failure_summary` buckets for `observation_mismatch`, `anchor_mismatch`, and `source_mismatch`.
  The verifier recomputes these from outcomes, which catches both detector regressions and stale
  source-location/source-snippet labels before release metrics are published.
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
  `IR-PY-IMPORTED-CLASS-NETWORK` remains pinned at 11 positives and 4 negatives. The reporting-rule
  truth set now also treats the same exact `parsers.UrlParser()` case as a positive `AV-NET001`
  label; it had been a stale negative left behind after the scanner gained module-qualified
  registered-class propagation.
- Native TypeScript provider SDK CommonJS proof now accepts exact top-level named destructuring for
  Google GenAI, including direct and aliased bindings, under the same immutable default-endpoint
  constraints as other native SDK constructors. Scoped named requires remain unresolved, and the IR
  truth set now covers 1,574 passing labels.
- Native TypeScript provider SDK CommonJS named destructuring is now pinned for OpenAI and Anthropic
  aliases as well as Google GenAI: exact top-level `const { OpenAI: Alias } = require("openai")` and
  `const { Anthropic: Alias } = require("@anthropic-ai/sdk")` carry constructor and model attribution
  only while the binding remains top-level and stable, with scoped named requires kept unresolved;
  the public IR truth set then covered 1,584 passing labels.
- TypeScript SDK type references are intentionally not provider evidence: `import type OpenAI from
  "openai"` and inline `import("openai").default...` annotations can describe message/tool schemas in
  real agent code without proving a runtime native SDK client, so provider/model attribution still
  requires value-import or stable constructor proof.
- Native TypeScript provider lazy getters can safely carry provider and exact model attribution when
  the getter is private, caches through a single `??=` write to a private backing field, constructs a
  default-endpoint SDK client, and the SDK call uses an earlier immutable module-level literal model.
  The local regression mirrors the MCP TypeScript quickstart shape, and the public IR truth set then
  covers 1,586 passing labels.
- Native TypeScript provider class fields can prove provider-call provenance without proving the
  exact model id. Method parameters such as `modelName` remain unresolved model evidence unless they
  can be tied to a direct literal or earlier immutable module-level literal binding; the public IR
  truth set then covered 1,587 passing labels.
- Type-only named OpenAI imports in TypeScript are also non-evidence: `import type { OpenAI as T }
  from "openai"` can describe SDK-shaped tool/message types in Roo Code-style code without proving a
  runtime SDK client. Native provider/model attribution remains restricted to exact value imports or
  stable constructor proof, and the public IR truth set then covered 1,588 passing labels.
- TypeScript exact model attribution now accepts immutable module-level literal object maps such as
  `MODEL_IDS.chat` and `MODEL_IDS["chat-model"]` for native SDK request objects and official AI SDK
  first-argument calls. The proof is deliberately limited to top-level `const` objects with direct
  literal string properties, exact dot-member or literal bracket reads, and no object or member
  reassignment; mutable object properties, nonliteral object values, dynamic bracket keys, dynamic
  bracket member writes, and unknown template values remain unresolved. The public IR truth set now
  then covered 1,605 passing labels.
- TypeScript AI SDK provider attribution now follows exact local named reexports only when the
  consumer import resolves to a local module whose named export chain reaches exactly one supported
  official `@ai-sdk/*` instance or factory symbol. Direct local and bounded transitive reexports
  preserve the official module/imported-symbol provenance; ambiguous reexports, parameter shadowing,
  star barrels, and module-object access remain unresolved. The public IR truth set then covered 1,613
  passing labels.
- Activepieces' `createLanguageModel({ provider, modelId })` workspace wrapper remains unresolved
  for exact TypeScript provider/model attribution in the pinned corpus because the
  `@activepieces/ai-providers` implementation is not present and the same helper includes a
  Cloudflare `@ai-sdk/openai-compatible` custom endpoint branch. The public IR truth set then covered
  1,616 passing labels.
- Official TypeScript AI SDK Azure attribution is source-proven only for `@ai-sdk/azure` imports and
  `createAzure` factory/model calls that use the default Azure endpoint shape. Endpoint-neutral
  `spreadIfDefined('apiVersion', ...)` is accepted because the real Activepieces call uses it for
  API-version selection, while baseURL spreads, arbitrary object spreads, and dynamic model IDs remain
  unresolved. The public IR truth set then covered 1,622 passing labels.
- The same exact local named-reexport machinery now has Azure coverage: reexported `createAzure`
  preserves provider/model attribution only for default-endpoint embedding calls, while a reexported
  factory with a baseURL spread remains unresolved for both provider and model evidence. The public
  IR truth set then covered 1,626 passing labels.
- Exact TypeScript AI SDK local reexport proof now includes star barrels when the requested provider
  name resolves to a single supported official `@ai-sdk/*` symbol, including one local transitive
  star hop. Duplicate star candidates remain unresolved, preserving the existing ambiguity boundary.
  The public IR truth set then covered 1,631 passing labels.
- Exact TypeScript AI SDK CommonJS named destructuring now feeds the same provider-import proof as
  static and dynamic imports when the `require()` is top-level and the destructured symbol is a
  supported official provider export. Rebound destructured aliases remain unresolved. The public IR
  truth set then covered 1,637 passing labels.
- TypeScript OpenAI Agents sandbox inventory now recognizes exact `@openai/agents/sandbox`
  `SandboxAgent` direct assignments and literal `capabilities: [shell()]` entries. The shell
  capability is recorded as `execution_environment: sdk-sandbox`, preserving capability visibility
  without treating it as host-local shell execution. Near imports and rebound constructors remain
  unresolved. The public IR truth set then covered 1,659 passing labels.
- The same TypeScript OpenAI Agents sandbox inventory now also recognizes same-file helper returns
  of exact `@openai/agents/sandbox` `SandboxAgent` constructors, using the helper name when the
  agent name is dynamic. Local near/rebound/conditional helper negatives and three real OpenAI Agents
  JS helper-returned sandbox agents are pinned. The public IR truth set then covered 1,686 passing
  labels.
- Exact TypeScript OpenAI Agents sandbox capability inventory now also covers unshadowed
  `filesystem()` and `memory()` factories in literal `capabilities` lists, marking both as
  SDK-sandbox reachability rather than host-local filesystem/memory risk. Rebounded capability
  aliases remain unresolved, and real OpenAI Agents JS memory examples pin same-line and multiline
  factory evidence. The public IR truth set then covered 1,712 passing labels.
- Exact TypeScript OpenAI Agents sandbox skill-loading inventory now covers unshadowed `skills()`
  factories in literal `capabilities` lists, without expanding aggregate `Capabilities.default()`
  contents. Rebounded skill aliases remain unresolved, and real OpenAI Agents JS coding/docs examples
  pin `skill-loading` edges. The public IR truth set then covered 1,729 passing labels.
- Exact TypeScript OpenAI Agents sandbox runtime-client inventory now records SDK sandbox runtime
  selection without reclassifying it as host-local execution. Exact
  `@openai/agents/sandbox/local` `UnixLocalSandboxClient` and `DockerSandboxClient` constructors
  become `sandbox-runtime` controls when wired through direct run client config, inline client
  construction, or one exact `client.create(...)` session binding, including `{ session }`
  shorthand. Exact ternary client initializers whose outer expression is the conditional also prove a
  `conditional-local` `sandbox-runtime` control only when both branches contain exactly one
  unshadowed supported local sandbox client constructor; half-known or rebound ternaries remain
  unresolved. The public IR truth set then covered 1,755 passing labels. Resumed sandbox sessions now
  inherit the proven runtime control through exact local `client as ...` aliases and `.resume(...)`
  assignments, while unknown resumable aliases remain unresolved; the public IR truth set now covers
  1,759 passing labels.
- OpenAI Agents JS extension sandbox backends are now inventory evidence when the client constructor
  is imported exactly from `@openai/agents-extensions/sandbox/blaxel` or
  `@openai/agents-extensions/sandbox/cloudflare` and wired into an exact `Runner` sandbox config.
  The scanner records `blaxel-cloud` and `cloudflare-workers` runtime controls and links
  `runner.run(agent, ...)` calls back to those controls; unknown Runner sandbox clients remain
  unresolved. The public IR truth set then covered 1,768 passing labels.
- Inline-created OpenAI Agents JS local sandbox sessions are now exact runtime evidence when the
  session assignment immediately calls `.create(...)` on an unshadowed
  `@openai/agents/sandbox/local` constructor, e.g. `await new UnixLocalSandboxClient(...).create(...)`.
  The resulting session variable links later `run(..., { sandbox: { session } })` calls back to the
  `sandbox-runtime` control. Unknown same-named constructors remain unresolved, and the public IR
  truth set then covered 1,774 passing labels.
- Variables initialized by direct calls to already-proven same-file
  `return new SandboxAgent(...)` helpers now inherit the helper agent identity for sandbox session
  edge attribution. This recovers shared-session OpenAI Agents JS examples where helper-returned
  agents are stored in local variables before `run(..., { sandbox: { session } })`; generic or
  unknown helper factories remain unresolved. The public IR truth set then covered 1,781 passing
  labels.
- Exact imported OpenAI Agents JS `Runner` instances now support option-level sandbox session
  attribution: `runner.run(agent, ..., { sandbox: { session } })` links the agent to the proven
  `sandbox-runtime` control, separate from Runner-constructor sandbox config. The session binding
  also accepts TypeScript type annotations when the initializer remains an exact proven
  `client.create(...)` call. Unknown option sessions remain unresolved, and the public IR truth set
  then covered 1,785 passing labels.
- Inline `SandboxAgent.asTool({ runConfig: { sandbox: { session } } })` entries now attach the
  proven `sandbox-runtime` control to the delegated sandbox agent, not just to the orchestrator's
  delegation edge. This recovers OpenAI Agents JS nested sandbox-agent-as-tool examples while
  unknown runConfig sessions remain unresolved. The public IR truth set now covers 1,789 passing
  labels.
- Literal numeric `exposedPorts` arrays on exact unshadowed OpenAI Agents JS local sandbox-client
  constructors are sandbox network-exposure evidence. They are represented as
  `sandbox-network-exposure` controls linked from the corresponding `sandbox-runtime`, so reviewers
  can see deliberate sandbox port publication without conflating it with host-local network
  execution. Unknown same-named constructors and nonliteral port arrays remain unresolved, and the
  public IR truth set now covers 1,795 passing labels.
- `Manifest({ extraPathGrants: [...] })` entries in OpenAI Agents JS are sandbox filesystem-sharing
  policy evidence when parsed from exact unshadowed `@openai/agents/sandbox` `Manifest`
  constructors. The current proof accepts direct string paths or earlier immutable module-level
  literal string bindings plus literal boolean `readOnly`, and records `sandbox-path-grant`
  controls. Unknown Manifest constructors, dynamic path construction, and nonliteral `readOnly`
  remain unresolved; the public IR truth set now covers 1,798 passing labels.
- Manifest `environment` entries in OpenAI Agents JS are sandbox runtime-configuration evidence
  under the same exact unshadowed Manifest proof. Direct literal string values and earlier immutable
  module-level literal string bindings become `sandbox-environment-variable` controls. Secret-like
  variable names such as `*_TOKEN` retain the variable name but redact the literal value in IR
  attributes; unknown Manifest constructors and dynamic values remain unresolved. The public IR truth
  set now covers 1,803 passing labels.
- Manifest `entries` in OpenAI Agents JS are sandbox workspace-seed/source evidence under the same
  exact unshadowed Manifest proof. Exact imported `file(...)` and direct `{ type: "file" }` entries
  become literal-file `sandbox-manifest-entry` controls that record only content presence, not file
  contents; exact `gitRepo(...)` entries record literal repository/ref metadata; exact `localDir(...)`
  entries record direct or earlier immutable module-level literal source paths. Unknown Manifest
  constructors and dynamic local directory expressions remain unresolved. The public IR truth set now
  covers 1,810 passing labels.
- Literal `sandbox.concurrencyLimits` in OpenAI Agents JS runtime options is sandbox manifest/source
  materialization policy evidence when attached to an already proven exact sandbox runtime option.
  Direct integer literal limit objects become `sandbox-concurrency-limit` controls linked from the
  corresponding `sandbox-runtime`; unknown clients and nonliteral limit values remain unresolved.
  The public IR truth set now covers 1,815 passing labels.
- Manifest `root` in OpenAI Agents JS is sandbox workspace-root policy evidence under the same exact
  Manifest proof. Direct literal strings and earlier immutable module-level literal string bindings
  become `sandbox-workspace-root` controls; dynamic root expressions and unknown Manifest
  constructors remain unresolved. The public IR truth set now covers 1,819 passing labels.
- Local sandbox `snapshot` options in OpenAI Agents JS are sandbox state-persistence evidence when
  attached to exact unshadowed `@openai/agents/sandbox/local` clients. Literal `type: "local"` plus
  direct or earlier immutable module-level literal `baseDir` become `sandbox-state-persistence`
  controls linked from the corresponding `sandbox-runtime`; unknown constructors and dynamic
  snapshot directories remain unresolved. The public IR truth set now covers 1,825 passing labels.
- Source-release verification now treats packaged GitHub workflow examples as content contracts, not
  only required filenames. The sdist verifier checks that the benchmark workflow emits, validates,
  and uploads verifier JSON while staying read-only; the policy gate keeps its policy/summary/expiry
  arguments without code-scanning write permission; and the code-scanning workflow keeps SARIF upload
  permission without becoming a policy gate.
- Exact OpenAI Agents JS sandbox memory policy configuration is now IR evidence when an unshadowed
  `@openai/agents/sandbox` `memory(...)` capability has literal option values. AgentVerify records
  generation disabled/enabled configuration, read live-update settings, memory/session layout
  directories, max raw memories, literal generation model IDs, and extra generation prompts as
  `sandbox-memory-policy` controls linked from the memory tool. Dynamic memory option values and
  unknown same-named factories remain unresolved. The public IR truth set then covered 1,838 passing
  labels.
- Exact OpenAI Agents JS nested Manifest directory trees are now sandbox workspace-seed evidence
  when both the directory entry and its `children` map are literal. AgentVerify recursively emits
  `sandbox-manifest-entry` controls for visible seeded paths such as `memories/gtm/notes.md` without
  recording file contents; dynamic child maps and unknown same-named Manifest constructors remain
  unresolved. The public IR truth set then covered 1,849 passing labels.
- Exact OpenAI Agents JS `sandbox.cwd` values are now per-run sandbox working-directory evidence
  only after an exact sandbox runtime is already proven. Direct literal strings and earlier
  immutable module-level string bindings become `sandbox-working-directory` controls linked from the
  runtime; dynamic cwd expressions remain unresolved. The public IR truth set now covers 1,856
  passing labels.
- Exact OpenAI Agents JS Manifest composition now preserves policy-control provenance across direct
  consumers. `client.create(manifest)`, `client.create({ manifest })`, and
  `SandboxAgent({ defaultManifest: manifest })` add `configured-by` edges from the proven
  `sandbox-runtime` or agent to the exact Manifest controls; same-file helper calls are accepted
  only when one helper has one `return new Manifest(...)`, allowing real `buildManifest()`
  examples without guessing through ambiguous composition. A helper with multiple Manifest returns
  still emits exact controls for each return but does not link callers to either candidate. The
  public IR truth set now covers 1,872 passing labels.
- Focused truth-set evaluation can now produce schema-valid, verifier-checked development artifacts.
  The evaluator records `label_filter` metadata for `--check-id`, `--rule-id`, and
  `--label-id-prefix`; the verifier reapplies the filter before checking outcome/label invariants,
  so partial results are explicit and cannot be mistaken for full public-regression artifacts.
  A focused `IR-TS-OPENAI-SANDBOX` run covered 235 labels and passed locally in seconds.
- Evaluator `--progress` timing is intentionally stderr-only and opt-in, preserving the
  benchmark-result JSON schema while making scan-cost attribution visible during local development.
  A focused `IR-TS-OPENAI-SANDBOX` run printed three target timings: the cached
  `openai/openai-agents-js` checkout took about 3.5 seconds, while the two local sandbox fixtures
  were below 0.3 seconds each.
- Full public IR truth-set profiling with `--progress` scanned 133 targets and reported about 482.5
  seconds of timed scan work, with the slowest cached repositories being Roo Code (~71.4s), Flowise
  (~39.7s), PydanticAI (~35.6s), Cline (~23.7s), and Skyvern (~23.4s). The top offenders are large
  real repositories with comparatively few labels, so broad traversal/parsing dominates benchmark
  iteration cost.
- `--scan-label-paths` is a useful focused-development shortcut, not a replacement for repository
  scans. It reduced the full public IR timed scan total to about 57.5 seconds but passed only
  1,587/1,872 labels because many Python import/reexport/helper and TypeScript composition labels
  intentionally require cross-file summaries. The OpenAI sandbox slice is self-contained enough to
  pass 235/235 with selected label paths, reducing the cached `openai/openai-agents-js` target from
  roughly 3.5 seconds to 0.9 seconds.
- Python `SyntaxWarning`s from third-party source parsing are not useful AgentVerify diagnostics and
  can bury benchmark progress output. Wrapping repository scans in a `SyntaxWarning` filter keeps
  scanner stderr clean while preserving AgentVerify IR errors for parse failures and skipped files.
- OpenAI Agents JS `MemorySession({ sessionId })` is exact conversation-state governance evidence
  when `MemorySession` is an unshadowed value import from `@openai/agents` and `sessionId` is a
  direct literal or earlier immutable module-level literal binding. AgentVerify records this as a
  `conversation-session` control and links direct `run(..., { session })` and
  `Runner.run(..., { session })` options from the agent to that control. Dynamic session IDs,
  rebound imports, unknown same-named constructors, and sandbox runtime sessions remain unresolved
  as conversation-session evidence. Real pinned `openai/openai-agents-js` examples
  `conversation-identity.ts` and `memory-multi-agent-multiturn.ts` validate 3 controls and 5
  composition edges; the public IR truth set now covers 1,887 passing labels.
- OpenAI Agents JS server-managed `conversationId` is also conversation-session evidence, but only
  when the identifier comes from an exact native `openai` SDK client constructed with the default
  endpoint and destructured from `client.conversations.create(...)`. AgentVerify links direct
  `run(..., { conversationId })` and `Runner.run(..., { conversationId })` options to that control;
  unknown clients, rebound `OpenAI` constructors, reassigned conversation IDs, and loose string IDs
  remain unresolved. The real pinned `examples/docs/running-agents/conversationId.ts` example
  validates 1 control and 2 composition edges; the public IR truth set now covers 1,897 passing
  labels.
- OpenAI Agents JS `previousResponseId` is conversation-continuity evidence only when it is derived
  from `.lastResponseId` on a stable local variable that was assigned from an exact imported
  `run(agent, ...)` call. AgentVerify records a `conversation-continuity` control and links a later
  `run(..., { previousResponseId })` option back to it. Loose string IDs, unknown run functions,
  and reassigned result bindings remain unresolved. The real pinned
  `examples/docs/running-agents/previousResponseId.ts` example validates 1 control and 1
  composition edge; the public IR truth set now covers 1,904 passing labels.
- OpenAI Agents JS `result.history` can prove conversation continuity when a stable history input
  binding is assigned from a stable exact `run(agent, ...)` result and then consumed by a later
  direct `run(agent, input)` or `runner.run(agent, input)` before reassignment. AgentVerify records a
  `conversation-continuity` control and a `configured-by` edge from the consuming agent to that
  control. Loose arrays, unknown run functions, and reassigned history inputs remain unresolved.
  Real pinned `openai/openai-agents-js` examples `examples/tools/web-search.ts` and
  `examples/agent-patterns/llm-as-a-judge.ts` validate 2 controls and 2 composition edges; the
  public IR truth set now covers 1,916 passing labels.
- OpenAI Agents JS `result.state` proves run-state resume continuity only when the state comes from
  an exact prior SDK run result. AgentVerify now records inline `run(agent, result.state)` and named
  state handoffs such as `const state = stream.state; run(agent, state, ...)` as
  `conversation-continuity` controls, including same-statement `result = await run(agent,
  result.state)` resumes that read the old state before replacing the result binding. Loose state
  objects, unknown run functions, stale result bindings, and reassigned named state inputs remain
  unresolved. Real pinned examples `examples/mcp/hosted-mcp-on-approval.ts`,
  `examples/docs/mcp/hostedHITL.ts`, `examples/mcp/hosted-mcp-human-in-the-loop.ts`, and
  `examples/agent-patterns/human-in-the-loop-stream.ts` validate 5 controls and 5 composition edges;
  the public IR truth set now covers 1,937 passing labels.

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

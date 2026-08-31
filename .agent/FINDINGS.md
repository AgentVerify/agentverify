# AgentVerify findings

## Durable facts

- OpenAI Agents JS tool guardrails can safely inherit helper predicate metadata through stable
  boolean result bindings. When a reject-content branch is guarded by a local `const`/`let` whose
  initializer is an exact helper call and the binding is not reassigned before the branch, the IR
  can retain the helper name/source and literal reject-condition evidence without broadening into
  arbitrary boolean data flow.
- OpenAI Agents JS tool guardrails can safely inherit reject-condition literals from exact imported
  helper predicates when exported function identity is unique. The existing
  `typescript_imported_function_body_bindings` resolver handles relative named imports and exact
  local reexports/star reexports; imported guardrail helper calls now preserve the local call name,
  source shape such as `imported-local-function`, and literal evidence while ambiguous or shadowed
  helpers remain unresolved.
- OpenAI Agents JS tool guardrails can safely inherit reject-condition literals from exact same-file
  helper predicates. Unique helper functions with direct return expressions such as
  `String(value ?? "").includes("classified")` now summarize to
  `guardrail_reject_condition_helpers` plus the inherited literal/source metadata, but only when a
  reject-content branch is guarded by an exact helper call. This keeps helper calls visible in the
  IR while avoiding broad predicate/data-flow claims.
- OpenAI Agents JS imported guarded tools now carry tool-guardrail governance to consumer Agents
  when identity is exact. The pinned SDK and local fixture expose reusable guarded
  `tool({ inputGuardrails, outputGuardrails })` exports that are imported into another file's
  `new Agent({ tools: [...] })`; repository-level IR already contains both the producer-file
  `tool-guardrail-policy` controls with `source_tool_id` and the consumer-file Agent-to-tool
  `uses` edge, so a conservative join can add Agent `governed-by` edges without reinterpreting
  dynamic tool lists. Confidence is high for exact relative imports/reexports and existing exact
  tool IDs, while dynamic/mutated tool arrays and opaque guardrail factories remain bounded.
- OpenAI Agents JS Realtime input guardrails are not modeled at the pinned SDK revision. The pinned
  OpenAI Agents JS corpus exposes Realtime output guardrail APIs and examples, but no stable
  `RealtimeInputGuardrail` / RealtimeSession `inputGuardrails` surface. Avoid inventing a Realtime
  input-guardrail rule until the SDK adds a concrete API shape or the corpus carries real examples.
- Editor diagnostic projections are now schema-backed installed contracts:
  `agentverify schema editor-diagnostics` validates both plain LSP-style diagnostics and
  policy-aware diagnostic groups, while `agentverify contracts` exports the schema as a required
  artifact in copied editor/CI bundles. This keeps editor examples and third-party adapter payloads
  tied to the native JSON report's stable fingerprints and policy summaries without introducing a
  second analyzer report format.
- Editor/review-bot integrations now have a checked policy-aware diagnostic grouping example:
  `examples/editor-policy-diagnostics.json` is regenerated in tests from the real
  `approval_callback_bypass` scan plus composed example policy. It demonstrates joining
  `policy_summary.gates[].matched_fingerprints` back to diagnostic fingerprints, preserving normal
  per-finding diagnostics while exposing gate-level policy groups and per-diagnostic
  `policy_gate_ids`.
- `agentverify contracts --verify-dir ... --format summary` now provides compact editor-contract
  verification logs: pass/fail status, manifest validity, required-artifact presence, artifact file,
  digest, byte-count, and content-validation counts, plus errors when present. JSON remains the
  default schema-backed verifier artifact for editor and CI integrations.
- `agentverify benchmark verify-engine` is now the installed validation path for full-corpus engine
  snapshots. It validates the engine-results schema, checks core summary aggregate consistency,
  recomputes every flat summary metric total represented by successful repository entries, and emits
  JSON governed by `agentverify schema engine-results-verification`.
- Installed-wheel smoke verification now validates the checked engine-results snapshot with the
  schema exported by the installed `agentverify` executable, proving the packaged schema and source
  evidence artifact agree in a built artifact workflow.
- Source-distribution verification now validates packaged `benchmarks/engine-results.json` against
  `src/agentverify/schemas/agentverify-engine-results-v1.schema.json`; malformed release archives
  fail even when the expected filename is present.
- The engine benchmark generator now validates the complete payload against the installed
  `engine-results` schema before writing an output file, so future full-corpus or filtered benchmark
  refreshes fail early if the release evidence artifact shape drifts.
- Engine-result snapshots are now schema-backed installed machine contracts:
  `agentverify schema engine-results` validates the top-level full-corpus benchmark artifact shape
  while intentionally allowing metric maps to grow as detectors add new slices. Distribution checks
  require both the wheel schema file and the source-distribution `benchmarks/engine-results.json`
  evidence artifact.
- The repository contains a 71-repository pinned research corpus and schema-v159 engine benchmark
  outputs. The refreshed full-corpus summary records 2,975 relationships and 10,848 symbolized
  components. It includes dedicated Vercel AI runtime evidence for Code Mode's public tool surface
  and host-tool approval runtime plus WorkflowAgent's framework-level approval pause,
  request-chunk, and revalidation continuation path. It now also includes a dedicated
  `typescript_openai_run_streaming` metric with 17 source-proven OpenAI Agents JS streaming-run
  controls from one repository and a dedicated `typescript_openai_codex_tool` metric with eight
  source-proven Codex extension tool/policy components from one repository.
- The runtime catalog currently contains 25 enabled reporting rules.
- OpenAI Agents JS `codexTool(...)` from
  `@openai/agents-extensions/experimental/codex` is now source-proven IR when the tool is passed
  directly, through an immutable same-file binding, or through an exact relative imported/named
  reexported/unambiguous star-reexported binding into an exact `@openai/agents` `Agent` literal
  `tools` array. The scanner records Codex thread options such as `approvalPolicy: "never"`,
  sandbox mode, network/web-search toggles, stream callbacks, and run-context thread reuse; ambiguous
  two-source barrels and mutated bindings remain unresolved. The public Codex-tool slice now passes
  38/38 labels, and the full public IR truth set passes 2,560/2,560 after the later safety-check
  refresh. The engine benchmark exposes the real same-file OpenAI examples as
  `typescript_openai_codex_tool`: four Codex tools, four policy controls, three explicit
  `approvalPolicy: "never"` controls, one default thread-options control without explicit approval
  policy, four agent-tool edges, and four configured-by edges. This is inventory for a
  model-visible delegated Codex runtime, not a reporting finding or a claim that all Codex
  executions are unsafe.
- Vercel `WorkflowAgent` has a source-proven framework approval runtime in
  `packages/workflow/src/workflow-agent.ts`: the run loop checks `tool.needsApproval` before
  executable tool calls, pauses approval-needed calls, writes `tool-approval-request` chunks for
  `useChat`, and routes approval responses through `validateApprovedToolApprovals(...)` before
  either executing approved tools or producing `execution-denied` tool results. AgentVerify now
  inventories this as approval-flow IR; app-level approval UI quality remains separate evidence.
- Vercel AI Code Mode's public `codeModeTool()` surface is now inventoried as a model-visible
  `experimental_toolCaller` that routes the model-provided `js` field into
  `runCodeMode({ js: input.js, tools })`. The IR records a sandboxed TypeScript code-execution
  capability, late-bound `tools.*` host-tool access, the generated tool-description prompt that
  declares `tools.name(input)` and unavailable `fetch`, and the edge to the existing Code Mode
  approval runtime. The full public IR truth set now passes 2,446/2,446 labels.
- Vercel `WorkflowAgent.model` provider-call detection can safely pass through narrow trailing
  TypeScript-only `as ...` and `satisfies ...` assertions for direct model properties, same-file
  const bindings, imported bindings, and exact reexports. Runtime wrappers, fallback expressions,
  mutated bindings/exports, and ambiguous star reexports remain unresolved. The focused
  WorkflowAgent-model truth set passes 17/17 labels, and the full public IR truth set passes
  2,472/2,472 labels.
- Vercel `WorkflowAgent` observability hooks are now inventoried when the constructor import is
  exact. Constructor-level and same-file `agent.stream({ ... })` `telemetry:
  createTelemetryOptions(...)` options emit `workflow-agent-telemetry` controls, and lifecycle/tool
  callback properties such as `onEnd`, `experimental_onStart`, `onToolExecutionStart`, and stream
  `onError` emit `workflow-agent-callbacks` controls linked to the source agent. The pinned Vercel
  AI `agent-chat.ts` and `telemetry-agent.ts` examples supply ten real public labels. These
  controls prove configured instrumentation hooks only; durable storage, actor attribution, and
  delivery guarantees remain separate audit evidence.
- Vercel AI Code Mode's host-tool approval runtime is now inventoried as a framework approval flow:
  `invokeHostTool(...)` checks `hostTool.needsApproval` before `executeHostTool(...)`, interrupt
  mode returns the `ai-sdk-code-mode/tool-approval` payload, callback denial throws before execution,
  and `continueCodeModeApproval(...)` validates response shape plus approval-id matching before
  resuming. The full public IR truth set passed 2,440/2,440 labels for that slice.
- Exact Vercel AI WorkflowAgent model configuration is now visible for direct AI SDK provider calls:
  `WorkflowAgent({ model: anthropic("claude-sonnet-4-20250514") })` emits a
  `model-settings-policy` control linked back to the source agent. Stable same-file `const` model
  bindings and imported sibling model bindings now also resolve when the initializer is exactly one
  immutable AI SDK provider model call, including direct named imports, exact named reexports, and
  unambiguous star reexports for sibling modules. Cast or otherwise wrapped provider expressions,
  mutated bindings/exports, and ambiguous star reexports remain unresolved by design. The full
  public IR truth set now passes 2,470/2,470 labels.
- Direct imported Vercel AI WorkflowAgent execute helpers now carry concrete capability evidence
  back to their object tools when provenance is exact. A local fixture with
  `execute: importedCalculate` imports a stable exported helper containing `new Function(...)`, and
  AgentVerify emits a `tool importedCalculate uses capability code-execution` edge at the helper
  body line. A second fixture branch uses the same imported helper in two object tools; those shared
  helper uses remain unlinked so one helper body is not over-attributed to multiple tools. Exact
  named reexports and unambiguous star reexports of the same stable helper body now preserve that
  tool-to-capability link, while ambiguous two-source helper barrels remain unresolved.
- OpenAI Agents SDK MCP approval metadata now covers TypeScript hosted `hostedMcpTool`
  `requireApproval` policies, Python hosted `HostedMCPTool` tool configs, and Python non-hosted
  MCP server `require_approval` call sites. The TypeScript hosted check now has 16 public IR labels
  (14 positive, 2 over-resolution/lookalike negatives), including imported local const-object
  policies, aliased imports, named local reexports, inline literal `onApproval` decisions, and real
  OpenAI JS result-binding callback call-source metadata plus same-file readline prompt-helper
  source-shape metadata while imported/reexported-mutated bindings remain dynamic. The Python hosted
  check has 25 public IR labels (24 positive, 1 lookalike negative), including imported,
  named-reexported, producer-star-reexported, and consumer-star-imported whole `tool_config`
  dictionaries while mutated configs remain dynamic. Ordered local multi-star imports resolve to the
  later visible literal source, and same-file direct approval callbacks returning
  `{"approve": request... <literal>}` now record exact handler predicate metadata. Same-function
  result-binding callbacks such as the pinned OpenAI hosted MCP `on_approval.py` example now record
  the approval result binding, approve binding, and call source, without claiming the called helper's
  internals when its source is absent. The Python non-hosted server check has 21
  public IR labels (19 positive, 2 lookalike negatives), including imported, named-reexported,
  producer-star-reexported, and consumer-star-imported local literal approval policies and redacted
  remote auth/header/client-factory metadata, with ordered local multi-star imports resolving to the
  later visible literal source; the full public IR truth set passes 2,429/2,429.
- TypeScript OpenAI local builtin tools now preserve `onApproval` callback result shape for exact
  approval-object returns on `shellTool` and `applyPatchTool`. The pinned OpenAI JS `local-shell.ts`
  example records the `promptShellApproval` call, same-file readline question source, yes/yes-string
  comparison, and `SHELL_AUTO_APPROVE` bypass metadata. The pinned `apply-patch.ts` example records a
  conditional `promptApplyPatchApproval` call with fallback rejection, the same readline
  prompt/yes-comparison source shape, and `APPLY_PATCH_AUTO_APPROVE` bypass metadata.
- TypeScript OpenAI run-state approval decisions now record direct prompt-review source shape when a
  proven `RunState.approve(...)` branch is guarded by a stable binding returned from a same-file
  readline confirmation helper. Pinned OpenAI JS `human-in-the-loop.ts`,
  `human-in-the-loop-stream.ts`, and `hosted-mcp-human-in-the-loop.ts` approval branches now preserve
  the helper name, readline question source, and yes/yes-string comparison while existing
  auto-approval environment-bypass metadata remains separate.
- TypeScript OpenAI helper-parameter run-state approvals now propagate exact same-file readline
  prompt-review metadata from the helper body into call-site-expanded approval controls without
  overwriting per-call source-agent provenance. The pinned OpenAI JS
  `examples/tools/computer-use-hitl.ts` approval control records both `AUTO_APPROVE_HITL` bypass
  evidence and the `confirm` readline yes/no prompt source shape, and the public IR truth set remains
  2,429/2,429 passing.
- Vercel AI WorkflowAgent examples use plain object tool definitions, not only factory-call tools.
  The pinned `examples/next-workflow/workflow/agent-chat.ts` `deleteFile` object has top-level
  `inputSchema`, `execute`, and `needsApproval: true as const`; AgentVerify now inventories this as
  a generic `object-tool` with static approval enabled. The public IR truth set now passes
  2,430/2,430 labels.
- Exact Vercel AI WorkflowAgent topology is now partially visible: an unshadowed
  `@ai-sdk/workflow` `WorkflowAgent` import creates an agent component, and stable local `tools`
  object bindings produce `agent uses tool` edges to already-inventoried entries. The pinned
  `agent-chat.ts` example now links the WorkflowAgent to its approval-protected `deleteFile`
  object-tool entry, and the public IR truth set passes 2,432/2,432 labels.
- Imported Vercel WorkflowAgent tool sets can be resolved without widening constructor matching:
  `tools: toolsFromModule` now links to object-tool component IDs in the original sibling module
  when `toolsFromModule` is a unique, unshadowed relative named import, exact named barrel reexport,
  or unambiguous star-barrel reexport of an immutable exported const object whose entries are
  concrete object tools. Local tool-set property mutation now invalidates same-file edges before
  construction, preventing stale `WorkflowAgent.tools` relationships. This is covered by local
  scanner regression tests; the pinned Vercel corpus still only proves the same-file tool-set shape.
- Vercel AI WorkflowAgent tools can delegate their actual behavior into same-file step helpers.
  The pinned `agent-chat.ts` `calculate` object tool points `execute` at a helper with
  `new Function(...)`; AgentVerify previously detected the code-execution capability but left it
  disconnected from the tool/agent path. Unique stable same-file execute-helper mapping links
  `calculate -> code-execution` and keeps shared helpers unresolved; it passed the then-current
  reporting and public IR checks.
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
- Benchmark-result artifacts now also carry optional top-level `all_labels_passed` when generated by
  `scripts/evaluate_truthset.py`. The benchmark-result schema allows the field for current
  artifacts while preserving compatibility with older result files, and verifier invariant checks
  reject the field if it disagrees with per-outcome pass status.
- Editor/review-bot contract export now has a checked GitHub Actions example. The workflow uses only
  read-only repository permissions, exports contracts with the installed CLI, validates both manifest
  and verifier JSON against bundled schemas, verifies the artifact bundle before upload, and is
  enforced by source-distribution workflow-fragment checks.
- Benchmark verifier JSON now mirrors the aggregate all-pass claim at per-result granularity. Each
  result entry emitted by `agentverify benchmark verify` includes a derived `all_labels_passed`
  boolean, while the schema allows the field and the checked example fixture covers the shape.
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
- `--expand-local-imports` is now a safer focused-development companion to `--scan-label-paths`:
  selected label files are expanded through local Python imports and TypeScript/JavaScript
  import/export, dynamic-import, and `require(...)` dependencies before scanning. The evaluator and
  verifier mark these artifacts with `scan_path_expansion: local-import-closure`; a real
  `IR-TS-TOOL-GRAPH` run passed 16/16 labels after including imported helper and barrel files, but
  release evidence remains repository-wide.
- Full public IR selected-path expansion is better but still intentionally incomplete: an expanded
  run passed 2,350/2,522 labels. Remaining false negatives concentrate in Cline subagent approval
  (48), Letta default tools (30), Continue plan approval (20), Roo command approval (18), Agno MCP
  confirmation (9), Semantic Kernel MCP sampling (9), and OpenAI MCP approval-default (8 across
  Python/TypeScript). These detectors need non-import-neighbor architecture files, sidecar policy
  files, runtime summaries, or scanner-wide context, so generic import closure alone should not be
  treated as the final benchmark acceleration strategy.
- `scripts/evaluate_truthset.py --format summary` now keeps long development runs readable by
  printing pass/fail counts, benchmark scope/filter metadata, mismatch summary, and failed-check
  metrics to stdout while preserving the full benchmark-result JSON file for schema verification and
  detailed outcome inspection.
- `scripts/evaluate_truthset.py --scan-cache-dir` provides the safer benchmark-iteration path when
  a slice needs full repository-wide semantics. Cache entries are source-digest-validated and
  AgentVerify-package-source-digest-validated before `RepositoryIR` is rehydrated from JSON.
  A real two-pass `IR-TS-TOOL-GRAPH` run showed initial cache misses, then cache hits under roughly
  0.05 seconds per target, with result JSON equal except for `generated_at`. Summary-format
  evaluator output reports aggregate cache hits and misses, which makes long cached development runs
  reviewable without parsing per-target progress lines.
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
  direct `run(agent, input)` or `runner.run(agent, input)` before reassignment. It can also prove a
  weaker feedback-loop continuity edge when the same exact call visibly consumes a caller/loop-owned
  history binding and refreshes that binding from its own `result.history`. AgentVerify records a
  `conversation-continuity` control and a `configured-by` edge from the consuming agent to that
  control. Direct same-file agent aliases are accepted only when they point to an exact local agent
  before reassignment. Loose arrays, unknown run functions, reassigned history inputs, rebound
  aliases, and dynamic `result.currentAgent` handoffs remain unresolved. Real pinned
  `openai/openai-agents-js` examples
  `examples/tools/web-search.ts`, `examples/agent-patterns/llm-as-a-judge.ts`, and
  `examples/docs/running-agents/chatLoop.ts`, plus routed alias evidence in
  `examples/agent-patterns/routing.ts`, validate 4 controls and 4 composition edges.
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
- OpenAI Agents JS generic `tool({ needsApproval })` approval metadata is now inventoried for exact
  unshadowed `@openai/agents` imports. Literal `needsApproval: true` records
  `approval_policy: enabled` and emits the existing `human-approval` edge; callback-valued
  `needsApproval` records `approval_policy: callback-controlled` while risky-action coverage remains
  unresolved unless a concrete human-approval control is proven. Real pinned examples
  `examples/docs/human-in-the-loop/toolApprovalDefinition.ts`, `examples/nextjs/src/agents.ts`,
  `examples/agent-patterns/human-in-the-loop.ts`, and
  `examples/agent-patterns/human-in-the-loop-stream.ts` validate 5 generic-tool approval components
  and 2 literal human-approval edges; the public IR truth set now covers 1,949 passing labels.
- OpenAI Agents JS delegated-agent `asTool({ needsApproval })` approval metadata is now inventoried
  on exact adapter relationships. Evidence is anchored to the `agent.asTool(...)` call line, which
  prevents repeated adapters to the same target agent from collapsing and allows each tool name and
  approval policy to remain visible. Local fixtures validate omitted, literal true, and
  callback-valued delegated-agent approval forms; real pinned OpenAI Agents JS HITL examples
  validate callback-controlled `weatherAgent.asTool` delegation in both standard and streaming
  flows. The public IR truth set now covers 1,954 passing labels.
- OpenAI Agents JS SDK-native approval decisions are now distinct IR evidence. Direct
  `result.state.approve/reject` and bound-state `state.approve/reject` calls become
  `approval-decision` controls only when the receiver state is sourced from an exact OpenAI Agents
  run result; loose, unknown, stale, and rebound state receivers remain unresolved. Real pinned
  examples validate both streaming HITL state decisions and hosted MCP HITL result-state decisions.
  The public IR truth set now covers 1,965 passing labels.
- OpenAI Agents JS serialized run-state restoration is now covered for simple same-file persistence
  chains. A restored `RunState.fromString(agent, storedState)` state becomes conversation-continuity
  evidence only when `storedState` is traced back to a proven SDK `result.state` serialization and
  the restored agent matches the original run agent; approval decisions on that restored state are
  then inventoried normally. The real standard HITL example validates the file write/read restore
  path, and the public IR truth set now covers 1,974 passing labels.
- OpenAI Agents JS approval-capable builtin tools use the same `needsApproval` semantics as generic
  SDK tools for policy metadata. Callback-valued `computerTool({ needsApproval: async ... })` in the
  real `examples/tools/computer-use-hitl.ts` singleton and per-request flows is source-proven
  callback-controlled approval policy evidence, not an unresolved handler; AgentVerify still withholds
  full human-approval coverage until predicate/action quality is analyzed. The public IR truth set
  now covers 1,977 passing labels.
- OpenAI Agents JS built-in local shell and patch tools are pinned as reachable approval-governed
  tools, not only as approval-bypass examples. The docs `localBuiltInTools.ts` example contributes
  approval-enabled `shellTool` and `applyPatchTool` components, `human-approval` governed-by edges,
  `Local tools agent`/`Patch Assistant` reachability edges, and editor-backed local filesystem write
  capability evidence for literal `applyPatchTool({ editor, ... })` options, raising the public IR
  truth set to 2,062 labels.
- TypeScript same-class filesystem helper methods now expose weak string-prefix checks without
  treating them as strong path boundaries. A method that returns a path after
  `candidate.startsWith(this.root)` with a throwing rejection marks downstream same-class writes
  assigned from `await this.method(...)` with `path_prefix_check: true` and a `path-prefix-check`
  control; the OpenAI Agents JS workspace-editor apply-patch example contributes four real
  governed-by edges.
- OpenAI Agents JS approval predicates can be made visible without overclaiming full approval
  coverage when the callback body is a shallow literal field predicate. AgentVerify now records
  prefix, contains, and literal-set predicate metadata for exact `needsApproval` callbacks across
  generic tools, delegated-agent tools, and approval-capable builtin tools. Real OpenAI docs/HITL
  and computer-use examples validate these forms, and the public IR truth set now covers 1,987
  passing labels.
- OpenAI Agents JS computer-use safety checks are a separate control surface from generic
  `needsApproval`. The official `examples/tools/computer-use-hitl.ts` per-request flow
  auto-acknowledges every pending safety check through `onSafetyCheck`, while the singleton
  computer-use tool has no safety-check handler. AgentVerify now inventories exact
  `onSafetyCheck` callbacks that return `true` or return the full `pendingSafetyChecks` list as
  `safety_check_policy: auto-acknowledge-all`, and reports reachable cases through
  `AV-APPROVAL011`. Exact callbacks that return `[]` or
  `pendingSafetyChecks.slice(0, 0)` through an acknowledgement field now record
  `safety_check_policy: acknowledge-none` and remain non-findings, improving the boundary between
  pass-through acknowledgement and explicit non-acknowledgement without claiming full human review.
- OpenAI Agents Python `ComputerTool(on_safety_check=...)` now participates in the same
  `AV-APPROVAL011` safety-control vocabulary when exact auto-acknowledgement is proven. Inline
  `lambda ...: True` callbacks and same-file callbacks with a single final `return True` are
  recorded as `safety_check_policy: auto-acknowledge-all`; conditional callbacks remain unresolved.
  The pinned OpenAI Agents Python SDK tests validate two same-name nested callback cases in separate
  lexical scopes. The public IR truth set then covered 1,999 passing labels.
- OpenAI Agents JS run-state approval decisions now preserve source-visible auto-approval bypass
  provenance without converting it into a standalone rule finding. A `RunState.approve(...)` control
  records `approval_bypass_environment_names` only when the call is inside a braced `if` whose
  condition is a direct proven confirmation helper call or an unreassigned boolean bound to that
  helper. The real HITL examples prove `AUTO_APPROVE_HITL` on approve branches; reject branches and
  reassigned boolean guards stay unannotated.
- OpenAI Agents Python run-state approval decisions are now source-proven IR evidence. Exact
  `Runner.run(...)`/`Runner.run_streamed(...)` results that flow through `result.to_state()`, plus
  exact `RunState.from_json/from_string(...)` restored states tied to a proven agent, emit
  `approval-decision` controls for `state.approve(...)` and `state.reject(...)`. Loose state-like
  objects and rebound state variables remain unresolved.
- OpenAI Agents Python sticky approval decisions are now visible as control metadata. Exact
  `always_approve` and `always_reject` keyword arguments on proven SDK run-state decisions preserve
  the keyword name, a stable same-function boolean binding when present, and whether the decision is
  `always`, `per-call`, or `dynamic`. The real shell HITL example uses a prompt-derived dynamic
  binding, while SDK tests contain literal sticky decisions.
- OpenAI Agents run-state reject decisions can carry custom rejection messages. Python exposes this
  as `rejection_message=...`; TypeScript exposes the equivalent as a reject-options object
  `{ message: ... }`. AgentVerify now records only presence and source class, not message text. The
  pinned Python custom-rejection HITL example is source-proven; the TypeScript
  `computer-use-hitl.ts` custom-message example is now also source-proven through a narrow
  helper-parameter model.
- OpenAI Agents JS helper-parameter run-state decisions can be proven without broad name matching
  when a non-exported same-file async helper takes an exact SDK `Agent`-typed first parameter and
  each call site supplies a lexically resolved Agent binding from the same enclosing function. The
  real `computer-use-hitl.ts` `runWithHitl(agent, ...)` calls now emit separate controls for the
  singleton and per-request browser agents, including `AUTO_APPROVE_HITL` approval-bypass metadata
  and template custom-rejection-message provenance.
- The same exact helper-parameter model can prove OpenAI Agents JS run-state resume continuity when
  the helper stores `result.state` and later calls `run(agentParam, state)`. The scanner now emits
  distinct call-line-qualified `conversation-continuity` controls and configured-by edges for each
  lexical caller. The real `computer-use-hitl.ts` helper contributes two helper-parameter state
  resumes; schema-v131 engine results report 8 TypeScript OpenAI run-state continuity controls and
  8 configured-by resume edges overall.
- OpenAI Agents JS trace correlation is now visible without conflating it with conversation memory.
  Exact imported `withTrace(..., { groupId })` calls that wrap a source-proven
  `run(agent, ...)` callback emit `trace-group` controls and configured-by edges; exact
  `withTrace(..., { traceId })` calls emit separate `trace-id` controls. The pinned
  `examples/agent-patterns/routing.ts` example links `triage_agent` to a dynamic
  `conversationId` trace group, while `examples/tools/codex.ts` links two Codex-agent runs to a
  generated trace ID with a logged OpenAI platform trace URL. The public IR truth set now covers
  2,086 passing labels.
- OpenAI Agents JS Runner-level `groupId` is the same trace-correlation family but a different SDK
  surface from `withTrace`. Exact imported `new Runner({ groupId })` instances now emit a
  `trace-group` control only when the Runner binding is stable and a later same-instance
  `.run(agent, ...)` call supplies a source-proven agent. The pinned
  `examples/sandbox/memory-generation.ts` example links `Sandbox Memory Generation Demo` to its
  literal `sandbox-memory-generation-example` trace group; a local reassigned Runner remains
  unresolved.
- OpenAI Agents JS Runner-level `tracingDisabled: true` is explicit observability policy evidence.
  Exact stable `new Runner({ tracingDisabled: true })` instances now emit `tracing-disabled`
  controls and configured-by edges for source-proven `.run(agent, ...)` calls, while explicit false
  values and rebound Runner variables remain unresolved. The pinned SDK testing examples disable
  tracing for `Weather assistant` and `Workspace assistant`, demonstrating why this belongs in IR
  policy evidence rather than as an unconditional finding. The public IR truth set now covers 2,099
  passing labels.
- OpenAI Agents JS delegated `asTool` run configurations can also disable tracing for the delegated
  agent execution. Exact `agent.asTool({ runConfig: { tracingDisabled: true } })` calls now emit
  `tracing-disabled` controls on the delegated agent with parent-agent and tool-name provenance,
  while explicit false values remain unresolved. The pinned sandbox agents-as-tools example disables
  tracing for `Pricing Packet Reviewer` and `Rollout Risk Reviewer`, bringing the public IR truth
  set to 2,106 passing labels.
- OpenAI Agents JS delegated `asTool` run options can bound delegated execution. Exact
  `agent.asTool({ runOptions: { maxTurns: <integer> } })` calls now emit `agent-turn-limit`
  controls on the delegated agent with parent-agent, tool-name, and literal `max_turns` provenance.
  The pinned agents-as-tools translator and sandbox reviewer examples contribute three real
  delegated turn-limit controls, bringing the public IR truth set to 2,115 passing labels.
- OpenAI Agents JS delegated `asTool` run configurations can override the delegated execution model.
  Exact `agent.asTool({ runConfig: { model: ... } })` calls now emit `agent-model-override`
  controls on the delegated agent with parent-agent, tool-name, provider, model, and shallow literal
  reasoning/verbosity settings. The pinned agents-as-tools translator example contributes real
  delegated model override evidence, bringing the public IR truth set to 2,120 passing labels.
- OpenAI Agents JS delegated `asTool` run configurations can name delegated trace workflows.
  Exact `agent.asTool({ runConfig: { workflowName: ... } })` calls now emit `trace-workflow`
  controls on the delegated agent with parent-agent, tool-name, and literal workflow-name
  provenance. The pinned sandbox agents-as-tools example contributes pricing and rollout reviewer
  workflow evidence, bringing the public IR truth set to 2,127 passing labels.
- OpenAI Agents JS Runner configurations can also name trace workflows for later source-proven
  runs. Stable exact `new Runner({ workflowName: ... })` instances now emit per-run
  `trace-workflow` controls and configured-by edges when a later same-instance `.run(agent, ...)`
  call supplies a source-proven agent; reassigned runners remain unresolved. The pinned Blaxel and
  Cloudflare sandbox extension examples contribute normal and streaming branch evidence, bringing
  the public IR truth set to 2,142 passing labels.
- OpenAI Agents JS direct and stable Runner runs can bound the concrete run site with `maxTurns`.
  Exact imported `run(agent, input, { maxTurns: <integer> })` and stable exact
  `runner.run(agent, input, { maxTurns: <integer> })` calls now emit `agent-turn-limit` controls
  and configured-by edges on source-proven agents. The pinned sandbox capability and hosted MCP
  human-in-the-loop examples contribute real direct-run and Runner-run turn-limit evidence, bringing
  the public IR truth set to 2,155 passing labels.
- OpenAI Agents JS Agent-level `modelSettings.toolChoice` is now source-agent governance evidence.
  Exact `new Agent({ modelSettings: { toolChoice: <literal> } })` settings now emit
  `tool-choice-policy` controls and configured-by edges, while mutable local choices remain
  unresolved. The pinned forcing-tool-use and programmatic tool-calling examples contribute
  `required` and `programmatic_tool_calling` evidence, bringing the public IR truth set to 2,162
  passing labels.
- OpenAI Agents JS Runner-level `modelSettings.toolChoice` can now be reviewed at the concrete run
  site. Stable exact `new Runner({ modelSettings: { toolChoice: <literal> } })` instances now emit
  per-run `tool-choice-policy` controls and configured-by edges when the later `.run(agent, ...)`
  call supplies a source-proven agent; rebound runners remain unresolved. The pinned hosted MCP HITL
  example contributes `required` initial-run and `auto` resume-run policy evidence, bringing the
  public IR truth set to 2,169 passing labels.
- OpenAI Agents JS `computerTool({ computer })` backend lifecycle is now visible alongside
  approval and safety-check metadata. Exact object factories with both `create` and `dispose`
  callbacks record `create-dispose-per-run`; create-only factories record
  `factory-without-dispose`, and shorthand/external computer bindings remain external-binding
  metadata. The pinned computer-use HITL and basic computer-use examples contribute per-request
  create/dispose evidence, while the singleton HITL example remains external-binding, bringing the
  public IR truth set to 2,175 passing labels.
- OpenAI Agents JS Agent-level literal model settings are now reviewable beyond `toolChoice`.
  Exact `new Agent({ modelSettings: { reasoning: { effort }, text: { verbosity } } })` values emit
  `model-settings-policy` controls and configured-by edges on the source agent, while mutable nested
  values remain unresolved. The pinned web-search filters and apply-patch examples contribute real
  low-reasoning/verbosity evidence, bringing the public IR truth set to 2,182 passing labels.
- OpenAI Agents JS hosted web-search scope is now reviewable when it is literal. Exact
  `webSearchTool({ filters: { allowedDomains }, searchContextSize, userLocation })` values emit
  `web-search-policy` controls on the source tool and copy the same allowlist/context metadata onto
  the `external-action` capability. Exact literal `Agent.modelSettings.providerData.include` arrays
  emit `provider-data-policy` controls and mark `web_search_sources_included` when source URLs are
  requested. Mutable domain arrays, mutable context sizes, and dynamic provider-data include arrays
  remain unresolved; dynamic `userLocation` bindings remain unresolved as well. The local fixture
  plus pinned OpenAI Agents JS `web-search-filters.ts`, `web-search.ts`, and hosted-tools examples
  bring the public IR truth set to 2,201 passing labels.
- OpenAI Agents JS Agent-level `parallelToolCalls` concurrency is now reviewable when literal.
  Exact `new Agent({ modelSettings: { parallelToolCalls: true|false } })` values emit
  `model-settings-policy` controls and configured-by edges on the source agent, while dynamic
  bindings remain unresolved. The local fixture plus pinned OpenAI Agents JS `tool-search.ts`
  examples bring the public IR truth set to 2,210 passing labels.
- OpenAI Realtime session-level model selection, `parallelToolCalls` concurrency,
  `config.reasoning.effort`, literal `config.outputModalities`, audio input/output formats, and
  audio transcription model/delay/languages plus transcription prompt/keywords are now separately
  reviewable when source-proven. Exact prompt content is not retained; controls record literal
  prompt presence and length plus literal keyword arrays/counts. Exact
  `RealtimeSession(agent, { model })` and
  `RealtimeSession(agent, { model, config: { parallelToolCalls, outputModalities, audio, reasoning } })`
  settings emit `realtime-session-config-policy` controls linked to the resolved `RealtimeAgent`;
  dynamic scalar and array values remain unresolved. The local fixture plus pinned OpenAI Agents JS
  `configureSession.ts` and `sendMessage.ts` voice-agent examples bring the public IR truth set to
  2,233 passing labels.
- OpenAI Realtime turn-detection behavior is now visible when literal and source-proven. Exact
  `config.audio.input.turnDetection.type/eagerness/createResponse/interruptResponse` values emit
  `realtime-session-config-policy` attributes, dynamic turn-detection bindings remain unresolved,
  and a narrow named sibling import such as `import { agent } from './agent'` resolves only when the
  target exports one exact `RealtimeAgent`. The pinned OpenAI Agents JS `turnDetection.ts` example
  links back to `agent.ts#agent:agent`, bringing the public IR truth set to 2,239 passing labels.
- OpenAI Realtime typed session-options spreads are now reviewable only for narrow exact cases.
  `const sessionOptions: Partial<RealtimeSessionOptions> = { ... }` can feed
  `new RealtimeSession(agent, { ...sessionOptions })` when there is one recognized spread, no direct
  `model`/`config` override, and no later reassignment or mutation of the options binding. The
  pinned OpenAI Agents JS `sipTransport.ts` example contributes spread-derived model and
  turn-detection policy evidence, bringing the public IR truth set to 2,244 passing labels.
- OpenAI Realtime tool-approval event decisions are now source-proven governance evidence. The
  scanner records `approval-decision` controls for exact
  `session.on("tool_approval_requested", (..., request) => session.approve(request.approvalItem))`
  or `session.reject(request.approvalItem)` flows only when `session` is a proven
  `RealtimeSession`; imported sessions resolve through a narrow sibling export proof that links back
  to the exported `RealtimeAgent`. Wrong events, lookalike objects, and approval calls using another
  object’s `approvalItem` remain unresolved. The pinned OpenAI Agents JS
  `examples/docs/voice-agents/toolApprovalEvent.ts` example contributes imported-session approval
  evidence, bringing the public IR truth set to 2,251 passing labels and the 71-repository engine
  benchmark to 2,870 relationships / 10,654 symbolized components.
- OpenAI Realtime session auth/connect configuration is now inventory evidence. Exact
  `session.connect({ apiKey })` calls on proven `RealtimeSession` bindings emit
  `realtime-session-auth-policy` controls, redact key values, and classify literal placeholders,
  literal `ek_` ephemeral client secrets, `process.env.OPENAI_API_KEY` server-key environment usage,
  fetch-derived ephemeral-key bindings, and unresolved dynamic bindings. When session options
  provide literal or constructor transport context, the same auth control records `websocket` or
  custom transport constructors such as `OpenAIRealtimeSIP`. Lookalike `.connect(...)` objects remain
  unresolved. The pinned OpenAI Agents JS `createSession.ts`, `helloWorld.ts`,
  `websocketSession.ts`, `sipTransport.ts`, and readme voice-agent example now contribute real auth
  evidence, bringing the public IR truth set to 2,264 passing labels and the 71-repository engine
  benchmark to 2,878 relationships / 10,662 symbolized components.
- OpenAI Realtime output guardrails are now reviewable when source-proven. Exact
  `new RealtimeSession(agent, { outputGuardrails, outputGuardrailSettings })` options emit
  `realtime-session-guardrail-policy` controls linked to the resolved `RealtimeAgent`. Inline arrays
  and typed `RealtimeOutputGuardrail[]` const arrays expose guardrail source/count and literal
  guardrail names; `outputGuardrailSettings.debounceTextLength` records direct signed integers such
  as `500` and `-1`. Comment-only placeholder arrays count as zero, mutable guardrail arrays fall
  back to binding-only metadata, dynamic debounce values remain unresolved, and lookalike objects
  are ignored. The local fixture plus pinned OpenAI Agents JS `guardrails.ts` and
  `guardrailSettings.ts` examples bring the public IR truth set to 2,276 passing labels and the
  71-repository engine benchmark to 2,880 relationships / 10,664 symbolized components.
- OpenAI RealtimeSession output guardrails now expose conservative tripwire metadata when a direct
  guardrail `execute` body returns an object containing `tripwireTriggered`. Inline arrays,
  typed `RealtimeOutputGuardrail[]` const arrays, and typed `RealtimeSessionOptions` spreads can
  contribute dynamic-expression or literal tripwire source counts; mutated arrays and settings-only
  sessions remain unresolved. The local fixture plus pinned OpenAI Agents JS
  `examples/docs/voice-agents/guardrails.ts` bring the Realtime guardrail truth-set slice to
  18/18 labels within the then-current 2,387-label public IR truth set.
- OpenAI RealtimeSession output guardrails now resolve exact relative imported typed
  `RealtimeOutputGuardrail[]` arrays. Direct imports and exact named local reexports used through
  typed `RealtimeSessionOptions` spreads preserve literal names, direct `tripwireTriggered`
  metadata, debounce settings, and source-agent governance edges, while ambiguous same-name barrels
  remain binding-only. The local Realtime guardrail fixture raised the slice to 25/25 labels in the
  then-current public IR refresh.
- OpenAI Agents JS Agent-level input/output guardrails are now reviewable when source-proven.
  Exact `new Agent({ inputGuardrails })` and `new Agent({ outputGuardrails })` constructor options
  emit `agent-guardrail-policy` controls linked to the source agent, including
  `new Agent<unknown, typeof schema>(...)` generic constructors. Inline arrays expose guardrail
  counts and literal names; typed `InputGuardrail`/`OutputGuardrail` object bindings, including
  generic `OutputGuardrail<typeof schema>`, contribute literal names when stable. Mutated guardrail
  objects fall back to binding-only metadata, dynamic guardrail arrays remain binding-only, and
  lookalike objects are ignored. The local fixture plus pinned OpenAI Agents JS
  `input-guardrails.ts`, `output-guardrails.ts`, and `exceptions1.ts` examples bring the public IR
  truth set to 2,292 passing labels and the 71-repository engine benchmark to 2,894 relationships /
  10,683 symbolized components.
- OpenAI Agents JS tool-level input/output guardrails are now reviewable when source-proven. Exact
  `tool({ inputGuardrails })` and `tool({ outputGuardrails })` factory options emit
  `tool-guardrail-policy` controls linked to the source tool. Inline arrays expose guardrail counts;
  `defineToolInputGuardrail`/`defineToolOutputGuardrail` const bindings contribute literal names
  when stable; `ToolGuardrailFunctionOutputFactory.allow/rejectContent` and literal
  `{ behavior: { type } }` returns contribute action metadata. Mutated definitions and dynamic
  guardrail arrays fall back to binding-only metadata, and lookalike objects are ignored. The local
  fixture plus pinned OpenAI Agents JS `examples/basic/tools.ts` and
  `examples/docs/guardrails/toolGuardrails.ts` bring the public IR truth set to 2,308 passing labels
  and the 71-repository engine benchmark to 2,898 relationships / 10,687 symbolized components.
- OpenAI Agents JS post-construction Agent guardrail assignments are now reviewable when
  source-proven. Stable same-file `agent.inputGuardrails = [...]` and
  `agent.outputGuardrails = [...]` assignments emit `agent-guardrail-policy` controls with
  `guardrail_update: property-assignment`; inline arrays expose counts and stable typed guardrail
  object bindings expose literal names. Dynamic assignment expressions stay binding-only, rebound
  Agent bindings are unresolved, and lookalike objects are ignored. The local fixture plus pinned
  OpenAI Agents JS `examples/docs/running-agents/exceptions1.ts` fallback assignments bring the
  public IR truth set to 2,321 passing labels; a later full engine refresh now records
  2,975 relationships / 10,848 symbolized components.
- OpenAI Agents JS Agent guardrails now expose conservative tripwire metadata when the guardrail
  `execute` body directly returns an object containing `tripwireTriggered`. Literal `true`/`false`
  values are counted separately from computed expressions, and the metadata propagates to the
  agent-to-control governance edge. Mutated guardrail bindings and dynamic guardrail arrays do not
  expose stale tripwire metadata. The local fixture plus pinned OpenAI Agents JS
  `input-guardrails.ts`, `output-guardrails.ts`, and `exceptions1.ts` examples bring the public IR
  truth set to 2,362 passing labels; a later full engine refresh now records 2,975 relationships /
  10,848 symbolized components.
- OpenAI Agents JS Agent guardrails now expose conservative direct-throw execution metadata when a
  stable inline or typed guardrail binding has an `execute` body whose first direct statement is
  `throw`. The local fixture and pinned OpenAI Agents JS `examples/docs/running-agents/exceptions1.ts`
  unstable input/output guardrails now distinguish guardrail failure/fallback setup from normal
  tripwire predicates, bringing the Agent guardrail truth-set slice to 43/43 labels.
- OpenAI Agents JS Agent guardrails now resolve exact relative imported typed guardrail arrays.
  Stable exported `InputGuardrail[]` / `OutputGuardrail[]` const arrays imported directly, or via
  exact named local reexports, preserve guardrail names and direct `tripwireTriggered` metadata on
  `new Agent({ inputGuardrails, outputGuardrails })` controls and governance edges. Ambiguous
  barrels that can export the same guardrail binding from multiple modules remain binding-only, so
  AgentVerify does not over-attribute names or literal tripwires across conflicting sources. The
  local guardrail fixture raises the Agent guardrail truth-set slice to 49/49 labels and the full
  public IR truth set to 2,528/2,528 labels.
- OpenAI Agents JS tool guardrails now expose exact shallow reject-condition metadata when an
  `if` branch directly returns `rejectContent` behavior and the predicate uses a literal
  `.includes(...)` or literal string non-equality check. Local dynamic and mutated guardrail
  configurations remain bounded, while pinned OpenAI Agents JS `examples/basic/tools.ts` and
  `examples/docs/guardrails/toolGuardrails.ts` raise the tool guardrail truth-set slice to 23/23
  labels.
- OpenAI Agents JS tool guardrails now resolve exact relative imported typed guardrail arrays.
  Stable exported `ToolInputGuardrailDefinition[]` / `ToolOutputGuardrailDefinition[]` arrays
  imported directly, or via exact named local reexports, preserve names, allow/reject-content action
  metadata, shallow reject predicate literals, tool governance edges, and Agent-to-tool-guardrail
  bridge edges. Ambiguous barrels exporting the same guardrail array name from multiple modules stay
  binding-only. The local tool guardrail fixture established the typed-array slice before the later
  imported guarded-tool Agent bridge expansion.
- OpenAI Agents JS Agents now get exact governance edges to tool guardrail controls when their
  `tools` array references a same-file tool binding with proven guardrails. Dynamic and mutated tool
  guardrails remain bounded through their existing tool controls, while a lookalike object negative
  prevents non-`tool(...)` guardrail-looking properties from becoming Agent governance. This raises
  the tool guardrail truth-set slice to 30/30 labels.
- OpenAI Agents JS `Agent.clone(...)` is now visible as Agent lineage when the clone source is a
  stable same-file Agent, an exact imported sibling export, or an exact named/star reexport that
  resolves to one OpenAI `Agent`. The IR records the source binding/agent, emits a `derived-from`
  edge, preserves the original source-agent ID through barrels, and distinguishes explicitly
  overridden SDK list properties from omitted `tools`, `handoffs`, `mcpServers`,
  `inputGuardrails`, and `outputGuardrails` lists that share source-agent arrays per the SDK docs.
  Dynamic clone configs, rebound clone sources, ambiguous/conflicting reexports, and lookalike
  imported `.clone(...)` methods remain unresolved. The clone truth-set slice now covers 17/17
  labels from local fixtures plus pinned OpenAI docs and financial-research examples, bringing the
  public IR truth set to 2,451 passing labels before later WorkflowAgent model-label additions.
- OpenAI Agents JS `hostedMcpTool({...})` approval settings are now visible as hosted-MCP-specific
  IR metadata instead of being flattened into generic tool approval. Omitted `requireApproval`
  records a disabled default, literal `"never"` records explicit disablement, inline object
  policies, stable same-file const object policies, exact imported local const object policies, and
  exact named local reexported const object policies record exact `never`/`always` tool-name
  branches and read-only hints, and configured `onApproval` callbacks are marked as
  callback-controlled. Mutated policy objects, imported/reexported-mutated policy bindings,
  shorthand values without stable object proof, and other dynamic `requireApproval` bindings remain
  binding-only dynamic metadata. The local fixture plus pinned OpenAI hosted MCP examples cover
  16/16 labels, bringing the public IR truth set to 2,409 passing labels.
- Python OpenAI Agents SDK `HostedMCPTool(tool_config={...})` approval settings are now visible as
  hosted-MCP-specific IR metadata on exact imported tool and capability nodes. Direct `"never"`
  policies record explicit disablement, direct or same-block literal `"always"` policies record
  always-required approval, shallow dict policies expose exact `always`/`never` tool-name lists and
  read-only hints, exact imported, named-reexported, producer-star-reexported, or
  consumer-star-imported local literal policies and imported, named-reexported,
  producer-star-reexported, or consumer-star-imported local literal whole `tool_config`
  dictionaries retain source resolution,
  configured `on_approval_request` callbacks are callback-controlled, and
  dynamic/imported/reexported-mutated approval or `tool_config` bindings remain binding-only
  metadata. In-place mutations such as `CONFIG["require_approval"] = ...` are treated as dynamic
  rather than over-resolved. The local fixture plus pinned OpenAI Agents Python and Composio hosted
  MCP examples cover 25/25 labels, bringing the public IR truth set to 2,429 passing labels.
- Python OpenAI Agents SDK non-hosted MCP server `require_approval` call sites are now visible on
  exact `agents.mcp.MCPServerStdio` components and imported subclasses whose base is exactly
  `agents.mcp.MCPServer` / `agents.mcp.server.MCPServer`. Literal `"never"`/`False` records
  disabled approval, literal `"always"`/`True` records always-required approval, same-block literal
  bindings and exact imported, named-reexported, producer-star-reexported, or
  consumer-star-imported local literal policies retain source resolution,
  shallow selective dict policies expose exact always/never tool-name lists and read-only hints,
  remote URLs are sanitized, literal `Authorization` header names and `auth`/`httpx_client_factory`
  bindings are recorded without copying secret values, dynamic bindings stay dynamic, and OpenAI-shaped imports
  from other MCP modules do not inherit OpenAI-specific approval semantics. The local fixture plus
  pinned OpenAI SDK remote transport examples now cover 21/21 labels, bringing the public IR truth
  set to 2,429 passing labels.
- OpenAI Agents JS streaming run mode is now represented as event-surface inventory when literal
  `stream: true` appears on exact direct `run(...)` or stable `Runner.run(...)` calls with a
  source-proven agent. The local conversation fixture and pinned hosted MCP human-in-the-loop
  example prove both direct and Runner-run forms, raising the new
  `IR-TS-OPENAI-RUN-STREAMING` slice to 8/8 labels in the then-current public IR refresh. The
  refreshed engine benchmark exposes this as
  `typescript_openai_run_streaming`: 17 controls, 11 direct `run(...)`, six stable
  `Runner.run(...)`, and 17 configured-by edges in one repository. This intentionally does not
  claim audit persistence, actor attribution, or human review quality; those require separate
  stream-consumer evidence.

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

## OpenAI Agents Python ComputerTool safety callback boundary

- Finding: In the Python SDK, `ComputerTool.on_safety_check` returns a boolean acknowledgement
  decision for an individual pending safety check, unlike the TypeScript SDK path where callbacks
  can return explicit acknowledgement arrays. Exact Python `return False` callbacks are therefore
  non-acknowledgement evidence, not empty-list evidence.
- Confidence: High for the pinned SDK revision and local fixture shapes.
- Implication: `AV-APPROVAL011` should continue to report only exact auto-acknowledgement
  (`return True`) while the IR preserves exact `return False` metadata as
  `safety_check_policy: acknowledge-none` for downstream reviewers and frontends.

## Warm public-regression scan cache is no longer the benchmark bottleneck

- Finding: After the Python ComputerTool scanner change and full artifact refresh, a warm-cache full
  IR truth-set run hit all then-current labels with `scan_cache: hit=157 miss=0` in about 2.8
  seconds wall time, and a warm-cache full reporting-rule run passed 733/733 labels with
  `scan_cache: hit=118 miss=0` in about 2.1 seconds wall time.
- Confidence: High for the current local corpus/cache layout.
- Implication: More near-term benchmark performance work should focus on cold-cache invalidation
  cost after scanner changes or selected-path dependency gaps, not on warm-cache hit overhead.

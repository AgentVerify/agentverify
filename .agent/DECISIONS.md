# AgentVerify decisions

## Editor diagnostics are an adapter schema, not a new scan format

- Decision: Expose `agentverify schema editor-diagnostics` and include
  `agentverify-editor-diagnostics-v1.schema.json` in `agentverify contracts` as the schema for
  LSP-style editor/review-bot adapter payloads derived from native AgentVerify JSON reports. Keep
  `agentverify scan --format json` as the authoritative analyzer output; editor diagnostics are a
  projection that preserves finding fingerprints, result kind, confidence, IR path, and optional
  policy gate joins.
- Evidence: The checked `examples/editor-diagnostics.json` and
  `examples/editor-policy-diagnostics.json` fixtures are regenerated in tests from real scan output,
  and now validate against the installed schema. The contract exporter validates and ships the
  adapter schema alongside the report and rules schemas so editor integrations can validate their
  projection without a source checkout.
- Alternative: Add an `agentverify scan --format editor-diagnostics` output now. Rejected because
  the native JSON report remains the richer, stable source of truth, while editor adapters may need
  host-specific URI/range conventions. A schema-backed adapter contract gives integration authors a
  precise target without prematurely freezing a CLI output mode.
- Revisit when: Multiple editor integrations converge on the same adapter payload and users need a
  built-in CLI renderer for it.

## Editor contract verification keeps JSON default with opt-in summary logs

- Decision: Keep `agentverify contracts --verify-dir` JSON as the default output and add
  `--format summary` only as an explicit human-facing log mode. Export mode still emits the JSON
  manifest; requesting summary without `--verify-dir` fails with a usage error.
- Evidence: Editor extensions, review bots, and CI bootstrap jobs need stable schema-backed JSON
  governed by `agentverify schema editor-contract-verification`, while GitHub Actions users benefit
  from the same compact pass/fail log style already added for benchmark verifiers. The copyable
  editor-contract workflow now writes the JSON verifier artifact, then prints the summary from a
  second verification pass.
- Alternative: Change the default output to summary or add summary fields to the verifier schema.
  Rejected because downstream automation should not lose the machine-readable artifact by default,
  and the existing JSON schema already carries the structured evidence needed by integrations.
- Revisit when: A downstream editor or CI consumer needs a stable text-summary contract rather than
  best-effort human logs.

## Engine-results schema validates artifact structure while allowing metric growth

- Decision: Expose `benchmarks/engine-results.json` through an installed structural schema via
  `agentverify schema engine-results`. The schema validates the snapshot envelope, sampling
  defaults, required core counts, repository result shape, counters, and category-coverage
  containers, but it does not freeze every individual detector metric key.
- Evidence: The full 71-repository engine benchmark already functions as a durable release evidence
  artifact, and `benchmarks/engine-results.json` currently validates against the new bundled
  schema. Distribution verification now requires the wheel schema file and requires source
  distributions to include the checked engine-results artifact.
- Alternative: Leave the benchmark snapshot as an undocumented JSON blob, or require a strict
  per-metric schema for every current detector slice. Rejected because no schema makes downstream
  tooling fragile, while strict metric-key freezing would create churn as validated detectors add
  new benchmark dimensions.
- Revisit when: Engine metrics become a stable public API or downstream integrations need
  compatibility guarantees for specific per-detector metric names.

## Vercel Code Mode tool-surface IR requires public tool-caller proof

- Decision: Emit Vercel AI Code Mode model-visible tool-surface IR only when `codeModeTool()`
  source-provenly wraps `createCodeModeTool(...)` in `experimental_toolCaller(...)`, and
  `createCodeModeTool(...)` routes the model-provided `js` field into `runCodeMode({ js: input.js,
  tools })`. Record the sandboxed TypeScript code-execution capability, late-bound `tools.*` host
  tool access, generated prompt control-setting, and edge to the Code Mode approval runtime.
- Evidence: Vercel AI's pinned `packages/code-mode/src/code-mode-tool.ts` exposes
  `codeModeTool()` and `createCodeModeTool(...)`; `packages/code-mode/src/tool-prompt.ts` declares
  the isolated sandbox, `tools.name(input)` host-tool API, and unavailable `fetch`. A local
  regression pins the positive source shape and rejects a wrapper that no longer uses
  `experimental_toolCaller(...)`.
- Alternative: Treat any function named `createCodeModeTool` or any `runCodeMode({ js })` call as a
  model-visible tool. Rejected because direct runtime calls can be host-internal; the public
  AI-SDK-facing `experimental_toolCaller(...)` wrapper is the evidence that a generation call can
  expose the surface to a model.
- Revisit when: Real applications use `codeModeTool()` with concrete host tools so AgentVerify can
  link model-visible code-mode calls to exact downstream host-tool capabilities and approval UX.

## Vercel Code Mode approval-flow IR requires full gate/continuation proof

- Decision: Emit Vercel AI Code Mode approval-flow controls only when the scanned source uniquely
  proves the runtime gate, payload kind, and continuation contract together: `invokeHostTool(...)`
  must check `hostTool.needsApproval` before `executeHostTool(...)`, interrupt mode must return the
  `ai-sdk-code-mode/tool-approval` payload, callback denial must throw before execution, and
  `continueCodeModeApproval(...)` must validate response shape plus approval-id equality before
  resuming in interrupt mode.
- Evidence: Vercel AI's pinned `packages/code-mode/src/tool-invocation.ts`,
  `packages/code-mode/src/approval.ts`, and `packages/code-mode/src/approval-continuation.ts`
  provide the exact runtime path. AgentVerify now records a framework component, approval-kind
  setting, `tool-approval-policy` control, `approval-continuation` control, and the key governed-by /
  continues-through edges. A local regression pins the positive multi-file shape and rejects a
  lookalike where execution happens before the approval gate.
- Alternative: Treat any `needsApproval` property or approval callback as equivalent runtime
  enforcement. Rejected because libraries can expose approval metadata without proving the execution
  order, denial behavior, or continuation replay contract.
- Revisit when: Concrete applications using Code Mode can link individual tool definitions,
  approval responses, or user-facing approval UX back into this runtime path without losing
  tool-call identity.

## Vercel WorkflowAgent model controls require provider-call proof plus static TS assertions only

- Decision: Emit a `model-settings-policy` control for `WorkflowAgent.model` only when a
  source-proven `@ai-sdk/workflow` `WorkflowAgent` constructor has a top-level `model` property whose
  expression is exactly one direct AI SDK provider model call, such as
  `anthropic("claude-sonnet-4-20250514")`, optionally followed only by a narrow trailing TypeScript
  `as ...` or `satisfies ...` type assertion. Stable same-file const bindings and relative named
  imports may resolve through direct export, exact named reexport, or unambiguous star reexport when
  the underlying initializer is exactly one immutable AI SDK provider model call plus the same
  static-only assertion suffix. Link the control back to the WorkflowAgent with an
  `agent configured-by control` edge and preserve the model binding/resolution mode.
- Evidence: Vercel AI's pinned `examples/next-workflow/workflow/agent-chat.ts` constructs a
  WorkflowAgent with a direct Anthropic model call. AgentVerify now records the provider, provider
  module, imported provider symbol, call, model string, model method, and source-agent identity in
  the control, and the public IR truth set pins both the control and relationship labels. A local
  imported-model fixture now covers stable same-file const bindings, direct import, named reexport,
  star reexport, simple trailing casted model, mutated binding/export, and ambiguous star-barrel
  cases. Focused regression also covers direct `as any` and `satisfies LanguageModel` suffixes.
- Alternative: Resolve arbitrary wrapper expressions or runtime continuations around provider
  calls. Rejected because those forms can transform the model value before the agent receives it.
  Runtime expressions such as fallback operators or helper wrappers still require separate
  source-proven semantics.
- Revisit when: Real repositories show recurring safe model wrapper helpers or richer type
  assertion syntax that can be proven without broadening into arbitrary expression resolution.

## TypeScript object-tool execute helper bodies map only under unique stable proof

- Decision: When a generic TypeScript tool object has a direct `execute: helperName` property, map
  capability detections inside the helper body back to that tool only if exactly one tool references
  the helper and either exactly one same-file free/static/block-arrow helper body exists with an
  unreassigned identifier, or `helperName` is a direct relative named import, exact named reexport,
  or unambiguous star reexport of one stable exported function/const-arrow helper body. The same
  helper may not be shared by multiple tools for this inference.
- Evidence: Vercel AI's pinned `examples/next-workflow/workflow/agent-chat.ts` defines a plain
  object `calculate` tool with `execute: calculate`; the delegated helper contains
  `new Function(...)`. Before this slice AgentVerify detected a floating `code-execution`
  capability but could not connect it to the WorkflowAgent's tool graph. The scanner now emits
  `calculate uses code-execution`, and AV-EXEC002 reports the reachable
  `agent -> calculate -> code-execution` path. Local regressions pin the positive same-file helper
  case, inline execute support, direct/imported/reexported helper capability propagation, and
  negative shared-helper and ambiguous-barrel cases.
- Alternative: Resolve any same-named function used by `execute`, including shared or reassigned
  helpers. Rejected because many tool registries reuse helpers or wrappers; capability ownership
  should remain source-proven rather than guessed from a name.
- Revisit when: Framework-specific step decorators or alias chains can
  be resolved with comparable mutation guards and call-site provenance.

## Vercel WorkflowAgent observability controls are instrumentation inventory, not audit proof

- Decision: Emit `workflow-agent-telemetry` and `workflow-agent-callbacks` controls only for
  source-proven `@ai-sdk/workflow` `WorkflowAgent` constructor properties and same-file
  `agent.stream({ ... })` options on unreassigned source-proven bindings. Top-level `telemetry`
  properties record inline, binding, factory-call, or configured-expression telemetry options,
  while known lifecycle/tool callback properties record the configured callback names and any
  direct handler call names that can be read without resolving arbitrary expressions. Link both
  controls back to the source agent with `configured-by` edges.
- Evidence: Vercel AI's pinned `examples/next-workflow/workflow/agent-chat.ts` configures an
  `onEnd` callback for model-facing tool output observability. Its
  `examples/next-workflow/workflow/telemetry-agent.ts` configures
  `telemetry: createTelemetryOptions(...)` plus `experimental_onStart`,
  `experimental_onStepStart`, `onToolExecutionStart`, `onToolExecutionEnd`, and `onEnd` callbacks
  that record telemetry events. The same file later calls `agent.stream({ ... })` with
  `telemetry: createTelemetryOptions(...)` and an `onError` callback. The public IR truth set pins
  ten real observability labels.
- Alternative: Treat these hooks as durable audit coverage or infer sink quality from callback
  names. Rejected because callback presence proves instrumentation hooks, not retention,
  attribution, or delivery guarantees.
- Revisit when: Real WorkflowAgent projects show source-proven telemetry sinks, persisted event
  schemas, actor identifiers, or approval/resume events that can support stronger audit controls or
  reporting rules.

## Vercel WorkflowAgent framework approval runtime is IR evidence, not an app approval finding

- Decision: Emit `typescript-vercel-workflow-agent-approval-flow` components only when one
  source file uniquely proves the `WorkflowAgent` run loop checks `tool.needsApproval`, pauses
  approval-needed calls before execution, emits writable-stream `tool-approval-request` chunks,
  and revalidates approval responses through `validateApprovedToolApprovals(...)` before approved
  execution or `execution-denied` results. Link the framework runtime to the policy, request chunk,
  and continuation controls.
- Evidence: Vercel AI's pinned `packages/workflow/src/workflow-agent.ts` has the full approval
  path: `approvalNeeded` is computed from boolean or callback `tool.needsApproval`, paused calls
  are selected from that result, `writeApprovalRequests(...)` emits approval IDs derived from tool
  call IDs, and the continuation path validates approved responses before executing tools or
  emitting denied results. Seven real public IR labels pin these facts.
- Alternative: Report a Vercel approval finding for every WorkflowAgent tool with
  `needsApproval`. Rejected because the framework runtime proves pause/resume semantics, not that a
  consuming app presents trustworthy human review, preserves actor identity, or records durable
  approval decisions.
- Revisit when: App-level Vercel examples or projects expose source-proven approval UI handlers,
  persistent approval records, authenticated actors, or unsafe bypasses that justify reportable
  findings.

## Vercel WorkflowAgent tool edges require exact constructor and stable tool-set binding

- Decision: Treat `new WorkflowAgent(...)` as an agent only when `WorkflowAgent` is an unshadowed
  named import from `@ai-sdk/workflow`. Resolve `WorkflowAgent({ tools })` or `tools: <identifier>`
  into `agent uses tool` edges only when the referenced tool-set object is declared before the agent,
  contains already-inventoried tool entries, and is not reassigned or property-mutated before
  construction. A direct relative named import, named reexport, or unambiguous star reexport reached
  through a relative barrel may also resolve when it points to one immutable exported const tool-set
  object whose entries are concrete object tools; the edge target remains the original sibling
  module's tool component ID and records `tool_set_resolution` as `imported-local-tools-object`,
  `imported-local-reexported-tools-object`, or `imported-local-star-reexported-tools-object`. Inline
  tools objects may link only to already-inventoried direct entries.
- Evidence: Vercel AI's pinned `examples/next-workflow/workflow/agent-chat.ts` imports
  `WorkflowAgent` from `@ai-sdk/workflow`, declares a stable `tools` object containing `getWeather`,
  `calculate`, and approval-protected `deleteFile`, then constructs `const agent = new
  WorkflowAgent({ ..., tools, ... })`. AgentVerify now emits the WorkflowAgent component and
  `WorkflowAgent.tools` edges to the stable object-tool entries, including the approval-protected
  `deleteFile` edge. A local cross-file regression covers `import { workflowTools as
  toolsFromModule } from "./tools"`, a named barrel reexport, and `export *` star barrel resolving
  to `ts:tools.ts#tool:*`, including a delegated helper-mapped code-execution tool, but the pinned
  public corpus does not yet contain this cross-file Vercel shape.
- Alternative: Recognize any same-named `WorkflowAgent` constructor or any `tools` object
  structurally. Rejected because the Vercel API semantics should come from import provenance and a
  stable binding, not from ordinary object names.
- Revisit when: Imported/reexported WorkflowAgent constructors, model helper modules, or
  approval-resumption flows can be resolved with comparable provenance and mutation guards.

## TypeScript plain object tools require execute plus schema evidence

- Decision: Inventory a TypeScript object property as a generic `object-tool` only when its object
  literal has top-level `execute` plus top-level `inputSchema` or `parameters`. Treat
  `needsApproval: true as const` as the same static approval literal as bare `true`; keep callback
  or absent approval metadata out of the always-enabled approval path.
- Evidence: Vercel AI's `examples/next-workflow/workflow/agent-chat.ts` defines a WorkflowAgent
  `deleteFile` plain object tool with `inputSchema`, `execute: deleteFileStep`, and
  `needsApproval: true as const`. Before this slice AgentVerify saw only factory-call tools and
  missed that approval-bearing object tool. A local regression pins the positive object-tool shape
  and a negative object missing `execute`.
- Alternative: Treat any object inside a `tools` object, or any object with `needsApproval`, as a
  tool. Rejected because containers and partial config fragments can contain nested tool-like
  properties; requiring top-level executable plus schema evidence keeps this broad TypeScript path
  conservative.
- Revisit when: WorkflowAgent-specific agent/tool graph edges or framework-import provenance can be
  added without conflating generic object literals with executable tools.

## TypeScript helper-parameter run-state prompt review preserves call-site provenance

- Decision: Let exact TypeScript OpenAI Agents SDK helper-parameter run-state approval summaries
  carry `approval_review_*` metadata only when the helper's approve branch is guarded by a
  same-file readline yes/no prompt helper or a stable binding returned from one. Merge that immutable
  helper-review payload into each call-site-expanded approval control while deriving
  `source_agent`, `source_agent_id`, `result_binding`, and `state_binding` from the exact helper call
  site. Keep reject branches free of approval-review metadata except for their own rejection-message
  evidence.
- Evidence: The pinned OpenAI Agents JS `examples/tools/computer-use-hitl.ts` helper
  `runWithHitl(agent, input)` prompts through `confirm(...)`, branches on `approved`, calls
  `state.approve(interruption)` in the truthy branch, and resumes with `run(agent, state)`. The
  helper is called from two exact `Browser user` Agent call sites; both call-site-expanded approvals
  now retain the per-call source agent and the helper's `confirm` readline question/
  yes-string-comparison source shape. A focused synthetic regression also covers named
  `createInterface` imports from `node:readline/promises` appearing after an unrelated named import.
- Alternative: Treat helper prompt-review metadata as direct helper-body metadata only, or infer it
  generically from helper names such as `confirm`. Rejected because the first loses evidence on the
  reportable call-site-expanded control, while the second would overclaim arbitrary boolean helpers.
- Revisit when: Real repositories show exact imported/reexported prompt helpers, prompt APIs beyond
  readline, or helper aliases that can be resolved without conflating multiple source agents.

## TypeScript run-state approval prompt review started as direct-branch metadata

- Decision: Record `approval_review_*` metadata for OpenAI Agents JS `RunState.approve(...)` controls
  only when the approve call is inside a braced `if` branch whose condition is either a direct
  same-file prompt-helper call or a stable local binding assigned from that helper before the branch.
  Keep rejection branches clean unless they have rejection-message evidence. Superseded in part:
  exact helper-parameter run-state summaries may now propagate prompt-review metadata when the
  emitted call-site control preserves exact source-agent provenance.
- Evidence: The pinned OpenAI JS `human-in-the-loop.ts` and `human-in-the-loop-stream.ts` examples
  assign `confirmed` / `ok` from a same-file `confirm(...)` helper, then call `state.approve(...)`
  only in the truthy branch. The helper creates a readline interface, asks the user a yes/no
  question, and returns a literal yes/yes-string comparison. The pinned hosted MCP human-loop example
  uses the same branch shape with `result.state.approve(...)`. Existing `AUTO_APPROVE_HITL` bypass
  metadata remains separate where the helper also contains an auto-approval environment branch.
- Alternative: Infer prompt-review quality for any nearby approval helper or propagate it through all
  helper summaries. Rejected for this slice because helper-parameter propagation needs call-site
  source-agent identity and can be handled separately without weakening this direct-branch contract.
- Revisit when: Additional helper/prompt forms appear that can be proven without conflating multiple
  call sites or losing source-agent provenance.

## TypeScript builtin-tool onApproval prompt helpers are source-shape inventory

- Decision: For OpenAI Agents JS `shellTool` and `applyPatchTool`, record exact inline `onApproval`
  callbacks that return approval objects from a stable block-local `approve` binding. When that
  binding is a same-file prompt helper call, record the helper call, readline question source, and
  literal yes/yes-string comparison. If the binding is guarded by a shallow ternary with `false`
  fallback, record conditional call-result plus fallback rejection instead of treating the callback
  as unconditional approval.
- Evidence: The pinned OpenAI JS `examples/tools/local-shell.ts` callback stores
  `approve = await promptShellApproval(commands)` and returns `{ approve }`; the helper dynamically
  imports `node:readline/promises`, awaits `rl.question(...)`, normalizes the answer, and returns
  `approved === 'y' || approved === 'yes'`. The pinned `examples/tools/apply-patch.ts` callback
  stores `approve = op ? await promptApplyPatchApproval(op) : false`, returns `{ approve }`, and uses
  the same readline yes/yes-string prompt-helper shape. Both examples also retain existing
  environment-bypass metadata for `SHELL_AUTO_APPROVE` or `APPLY_PATCH_AUTO_APPROVE`.
- Alternative: Treat `needsApproval: true` plus any `onApproval` callback as sufficient human-review
  evidence. Rejected because callbacks can approve automatically, reject, delegate to opaque helpers,
  or include environment bypasses; source-shape inventory is more faithful than a blanket control
  claim.
- Revisit when: Additional exact callback/helper shapes appear in real repositories and can be
  modeled without resolving arbitrary approval logic.

## TypeScript hosted MCP onApproval return shape is inventory, not full HITL proof

- Decision: Record exact inline `hostedMcpTool({ onApproval })` callbacks that return literal
  approval objects or one stable block-local approval binding as handler metadata. When that binding
  comes from a unique same-file helper that structurally creates a readline prompt, awaits
  `rl.question(...)`, and returns a literal yes/yes-string comparison, record that prompt-helper
  source shape as review metadata; keep generic callback configuration separate from human-review
  proof.
- Evidence: The local hosted MCP fixture includes `onApproval: async () => ({ approve: false })`,
  which is exact enough to classify as an always-reject callback. The pinned OpenAI Agents JS
  `hosted-mcp-on-approval.ts` example stores `approval = await promptApproval(item)` and returns
  `{ approve: approval, reason: undefined }`; AgentVerify can preserve the approve binding,
  `promptApproval` call source, and now the helper's readline question plus
  `answer.toLowerCase().trim() === 'y'` decision source shape. The same real callback also has
  existing environment-bypass evidence for `AUTO_APPROVE_MCP` / `AUTO_APPROVE_HITL`, so reporting both
  prompt-source and bypass metadata is more honest than collapsing the callback into a single
  "approved" concept.
- Alternative: Treat `onApproval` callbacks as human-in-the-loop controls whenever present. Rejected
  because callbacks can always approve/reject, consult environment flags, or delegate to helpers with
  unknown semantics.
- Revisit when: Additional helper bodies, prompt APIs, and negative auto-approval branches can be
  connected to actual user-confirmation quality without overclaiming arbitrary callback behavior.

## Python hosted MCP callback predicates are inventory, not human-review proof

- Decision: Record exact same-file `HostedMCPTool.on_approval_request` callbacks that directly
  return an approval result dictionary, or same-function result dictionaries whose `approve` value
  comes from one stable earlier binding, as handler metadata; do not treat generic configured
  callbacks as human-review controls.
- Evidence: A local Python hosted MCP fixture returns `{"approve": request.data.name !=
  "delete_page"}`, which is source-visible enough to record the request-field predicate and
  conditional decision. The pinned OpenAI hosted MCP `on_approval.py` example stores
  `approved = confirm_with_fallback(...)`, returns `result = {"approve": approved}`, and mutates
  only `result["reason"]` on denial. AgentVerify can preserve the result binding, approve binding,
  and call source, but the imported `examples.auto_mode` helper source is absent in the cached
  checkout, so helper internals remain unverified.
- Alternative: Mark every configured hosted MCP approval callback as a human approval edge. Rejected
  because callbacks can unconditionally approve, reject, consult environment flags, or delegate to
  opaque helpers; configuration alone is not control quality.
- Revisit when: The scanner can prove prompt/user-confirmation helper flows, imported helper source,
  or classify unconditional approval/rejection callbacks from real repositories without broad
  interprocedural inference.

## Python OpenAI MCP server approval remains IR inventory until risk-scoped reporting evidence exists

- Decision: Record exact non-hosted OpenAI Agents Python MCP server `require_approval` call-site
  semantics as IR metadata, not a new user-facing reporting rule yet.
- Evidence: The SDK implementation and tests show `require_approval` can be disabled, always
  required, selective, or callable/dynamic. The scanner can now prove direct `MCPServerStdio`,
  `MCPServerSse`, and `MCPServerStreamableHttp` calls plus imported subclasses of exact
  `agents.mcp.MCPServer`, while keeping `local_mcp` lookalikes out of OpenAI-specific approval
  semantics. Same-block literal bindings and exact imported, named-reexported,
  producer-star-reexported, or consumer-star-imported local literal approval policies are resolved
  while mutated imports/reexports and unresolved later star imports remain dynamic. Ordered local
  multi-star imports resolve to the later visible literal source. Remote URLs are sanitized, and remote
  auth/header/client-factory evidence is recorded as source-shape metadata without copying secret
  values. Current validated labels combine local/source-shape coverage with pinned OpenAI SDK
  integration-test remote transport examples; a noisy review rule for examples or tests would
  overstate production risk without additional real production cases.
- Alternative: Immediately flag disabled/non-always MCP server approval as a high-severity rule.
  Rejected because explicit `"never"` can be appropriate for trusted/read-only servers and because
  a user-facing finding should be scoped to reachable risky capabilities or production evidence.
- Revisit when: AgentVerify can connect these call-site policies to discovered mutating MCP
  capabilities or when pinned production repositories show disabled approval on reachable local MCP
  tools.

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

## Selected-label-path benchmark scans are development evidence only

- Decision: Allow `scripts/evaluate_truthset.py --scan-label-paths` to scan only files referenced by
  the evaluated labels, but record `benchmark.scan_scope: selected-label-paths` and surface that
  scope from benchmark verification. When explicitly paired with `--expand-local-imports`, expand
  those selected files through local Python and TypeScript/JavaScript import/export closures and
  record `benchmark.scan_path_expansion: local-import-closure`; keep repository-wide scans as the
  only release-comparable benchmark path. `scripts/evaluate_truthset.py --format summary` is a
  stdout presentation option only; it does not change the benchmark-result JSON file written to
  `--output`.
- Evidence: Full public IR profiling showed roughly 482.5 seconds of timed scan work, mostly from
  large cached repositories with few labels. The selected-label-path experiment reduced timed scan
  work to roughly 57.5 seconds, and focused OpenAI sandbox labels still passed 235/235, but the full
  all-IR run failed 285 labels that require cross-file helper, import, reexport, or composition
  summaries. The opt-in local-import closure restored the cross-file `IR-TS-TOOL-GRAPH` development
  slice to 16/16 passing while keeping the scan scope and expansion explicit in result metadata. A
  full expanded selected-path run passed 2,350/2,522 labels and showed the remaining misses are
  concentrated in detectors needing non-import-neighbor sidecars or scanner-wide summaries.
- Alternative: Treat selected label paths as a drop-in benchmark acceleration. Rejected because that
  would silently weaken cross-file evidence and could make release claims incomparable with
  repository-wide scans.
- Revisit when: broader public IR slices show whether local import/export closure is sufficient, or
  scanner result caching can preserve repository-wide evidence while avoiding repeated parse work.

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
  write every expected artifact. A checked editor-diagnostics example derived from a real fixture
  documents how integrations should map evidence lines, severities, fingerprints, result kinds,
  confidence, and IR paths into LSP-style diagnostics.
- Alternative: Check in generated copies of the rule catalog and schemas. Rejected because generated
  copies would drift whenever rules or schemas change unless every catalog update also regenerated
  secondary artifacts.
- Revisit when: a published package or website hosts versioned schema URLs and editor plugins can
  fetch those directly.

## Policy-gate workflows are checked adoption artifacts

- Decision: Keep a copyable GitHub Actions policy-gate workflow under `examples/` and require it in
  source distributions.
- Evidence: Policy enforcement should be separate from SARIF upload so deliberate gate failures do
  not prevent diagnostic ingestion. A minimal workflow can use only `contents: read`, validate policy
  composition before scanning, emit compact summary output, and require expiry dates on inline
  suppressions. Tests now assert those properties and docs link to the workflow.
- Alternative: Leave the workflow as prose snippets in policy/code-scanning docs. Rejected because
  snippets are easy to copy incompletely and are not caught by release artifact verification.
- Revisit when: a hosted GitHub Action, reusable workflow, or release-pinned installation path
  replaces manual workflow copying.

## OpenAI MemorySession is conversation-state evidence, not sandbox runtime evidence

- Decision: Model exact OpenAI Agents JS `MemorySession({ sessionId })` as a
  `conversation-session` control and link agents to it from top-level `session` run options, while
  keeping sandbox `{ session }` bindings under `sandbox-runtime` only when they derive from a proven
  sandbox client/session.
- Evidence: Pinned `openai/openai-agents-js` examples use both concepts together:
  `conversation-identity.ts` passes a `MemorySession` through top-level `session` while also passing
  a sandbox runtime session through `sandbox.session`; `memory-multi-agent-multiturn.ts` uses two
  named `MemorySession` instances across repeated sandboxed runs. Treating both as one control would
  blur durable conversation memory with execution-environment selection.
- Alternative: Reuse `sandbox-state-persistence` or `sandbox-runtime` controls. Rejected because
  those controls describe sandbox filesystem/session behavior, not agent conversation identity or
  continuity.
- Revisit when: OpenAI Agents JS exposes additional session implementations with materially
  different persistence or external storage semantics that deserve separate control names or
  attributes.

## OpenAI server conversation IDs require source proof from the OpenAI SDK

- Decision: Treat top-level `conversationId` run options as `conversation-session` evidence only
  when the identifier is destructured from `client.conversations.create(...)` and `client` is a
  stable default-endpoint `new OpenAI()` instance from the exact `openai` package.
- Evidence: The pinned OpenAI Agents JS `examples/docs/running-agents/conversationId.ts` example
  creates a server-managed conversation via the native SDK and passes the same `conversationId` to
  repeated `run(...)` calls. A variable named `conversationId` alone is too weak: it could be an
  arbitrary string, reassigned value, or unrelated application ID.
- Alternative: Accept any `conversationId` property passed to `run(...)`. Rejected because that
  would turn naming convention into provider-state evidence and likely create false positives in
  applications with their own conversation IDs.
- Revisit when: additional official examples show safe, exact aliases such as object-property
  conversation results (`conversation.id`) that can be tied back to `conversations.create(...)`
  without broad flow analysis.

## OpenAI previousResponseId requires proof from a prior run result

- Decision: Treat OpenAI Agents JS `previousResponseId` options as conversation-continuity evidence
  only when the ID binding is derived from `.lastResponseId` on a stable result variable assigned by
  an exact imported `run(agent, ...)` call.
- Evidence: The pinned `examples/docs/running-agents/previousResponseId.ts` example creates
  `first = await run(agent, ...)`, then derives `previousResponseId = first.lastResponseId`, then
  passes that value to a later `run(...)`. This proves continuity through SDK result state without
  relying on arbitrary identifier names.
- Alternative: Accept any literal/string variable passed as `previousResponseId`. Rejected because
  a string-shaped ID does not prove it belongs to the OpenAI Agents SDK's previous-response
  continuity mechanism.
- Revisit when: official examples show exact inline forms such as
  `{ previousResponseId: first.lastResponseId }` or continuity through saved run state that can be
  modeled without broad interprocedural flow.

## OpenAI run history continuation requires local result-history proof

- Decision: Treat OpenAI Agents JS `result.history` handoff as `conversation-continuity` evidence
  only when an input binding is assigned from `.history` on a stable or locally latest result
  variable returned by an exact imported `run(agent, ...)` call, and either a later same-file
  `run(agent, inputBinding)`/`runner.run(agent, inputBinding)` consumes that binding before
  reassignment or the same exact call visibly feeds a caller/loop-owned history binding that it then
  refreshes from its own `result.history`.
- Evidence: Pinned OpenAI Agents JS examples include `examples/tools/web-search.ts`, where
  `messages = result.history` is extended and passed to a second `run`, and
  `examples/agent-patterns/llm-as-a-judge.ts`, where `inputItems = storyOutlineResult.history` is
  passed to an evaluator run. The pinned `examples/docs/running-agents/chatLoop.ts` helper now
  validates the weaker `run-history-feedback-input` shape, where `thread.concat(...)` is consumed
  and `thread = result.history` refreshes the caller-owned history for subsequent helper calls. The
  pinned `examples/agent-patterns/routing.ts` example validates a direct same-file agent alias
  (`let agent: Agent<...> = triageAgent`) feeding `run(agent, inputs)` before `inputs =
  result.history`.
  Local positives cover direct imported `run`, `Runner.run`, loop feedback, concat feedback, and
  direct agent aliases; local negatives pin loose arrays, unknown run functions, reassigned history
  inputs, and rebound aliases.
- Alternative: Treat any array passed as the second `run` argument as conversation continuity.
  Rejected because OpenAI Agents run inputs can also be fresh user messages; continuity requires
  proof that the input was returned by SDK history.
- Revisit when: dynamic routed-agent handoffs such as `agent = result.currentAgent ?? agent` can be
  modeled without treating arbitrary mutable aliases as exact agent provenance.

## OpenAI run-state resume requires prior SDK run-state proof

- Decision: Treat OpenAI Agents JS `result.state` resume as `conversation-continuity` evidence only
  when the state expression or state binding is sourced from a prior exact OpenAI Agents `run(...)`
  or `Runner.run(...)` result in the same file and the source is not made stale before use. A
  same-statement assignment such as `result = await run(agent, result.state)` is accepted because the
  right-hand side reads the old result state before replacing the result binding.
- Evidence: Pinned OpenAI Agents JS HITL/MCP examples use this exact resume shape:
  `examples/mcp/hosted-mcp-on-approval.ts`, `examples/docs/mcp/hostedHITL.ts`, and
  `examples/mcp/hosted-mcp-human-in-the-loop.ts` resume with inline `result.state`, while
  `examples/agent-patterns/human-in-the-loop-stream.ts` assigns `const state = stream.state` and
  resumes with that binding. Local negatives pin loose state objects, unknown run functions, stale
  result bindings, and reassigned named state inputs.
- Alternative: Treat any object named `state` or any `.state` property as run-state continuity.
  Rejected because many libraries and applications use generic state objects unrelated to OpenAI
  Agents SDK run resumption.
- Revisit when: approval-quality analysis is added on top of this resume backbone, especially to
  distinguish manual human approval, automatic approval, rejected-state handling, and missing
  approval callbacks.

## OpenAI generic tool approval inventory is exact-import and policy-level

- Decision: Record OpenAI Agents JS `tool({ needsApproval })` approval metadata only when `tool` is
  an exact unshadowed value import from `@openai/agents`. Literal `needsApproval: true` remains the
  only generic-tool form that creates a `human-approval` control edge; callback-valued
  `needsApproval` is recorded as `approval_policy: callback-controlled` without claiming always-on
  approval coverage.
- Evidence: Pinned examples show both official forms: `examples/docs/human-in-the-loop/toolApprovalDefinition.ts`
  contains `sensitiveTool` with literal approval and `sendEmail` with a callback; `examples/nextjs/src/agents.ts`
  contains a literal-approved generic tool; `examples/agent-patterns/human-in-the-loop.ts` and
  `examples/agent-patterns/human-in-the-loop-stream.ts` contain conditional callbacks.
- Alternative: Treat callback-valued `needsApproval` as full `human-approval` coverage. Rejected
  because the callback can approve only some calls and AgentVerify has not proven the predicate
  covers every risky operation.
- Revisit when: predicate-aware tool-risk analysis can relate callback conditions to specific tool
  inputs, or when `agent.asTool({ needsApproval })` delegated-tool approval gets a distinct IR shape.

## OpenAI delegated-agent asTool approval inventory belongs on exact adapter edges

- Decision: Record OpenAI Agents JS `agent.asTool({ needsApproval })` approval metadata on the
  `agent delegates-to agent` adapter relationship, using the exact `asTool(...)` call line as
  evidence. Literal `needsApproval: true` records `approval_policy: enabled`,
  `approval_handler: none`, and `approval_decision: always`; callback-valued `needsApproval`
  records `approval_policy: callback-controlled`, `approval_handler: needsApproval-callback`, and
  `approval_decision: dynamic-callback`; omitted or explicit false approval stays unclaimed.
- Evidence: Local `cases/typescript_structured_tools` now has three `worker.asTool(...)` entries to
  the same target agent, proving that parent-constructor evidence would collapse distinct adapter
  policies. Pinned OpenAI Agents JS HITL examples use `weatherAgent.asTool({ toolName:
  "ask_weather_agent", needsApproval: async ... })` in both standard and streaming flows.
- Alternative: Create a synthetic tool component for each delegated agent adapter. Deferred because
  the current IR already has a source/target agent relationship, and adding delegated-tool
  components would be a larger schema/semantics choice. Edge attributes preserve identity now
  without overclaiming approval coverage.
- Revisit when: predicate-aware approval-quality analysis needs a first-class delegated-tool node,
  or reporting rules need to reason about delegated-agent tools independently of the source/target
  agent relationship.

## OpenAI run-state approval decisions require proven SDK state receivers

- Decision: Record OpenAI Agents JS manual approval/rejection handling as `approval-decision`
  controls only when `state.approve(...)`, `state.reject(...)`, `result.state.approve(...)`, or
  `result.state.reject(...)` can be tied to a proven exact OpenAI Agents `run(...)` or
  `Runner.run(...)` result state. Link the source agent to each decision control with
  `governed-by`, and keep approval decisions separate from conversation-continuity resume controls.
- Evidence: Local fixtures cover bound state, inline result state, loose approval-shaped objects,
  unknown run results, stale result bindings, and rebound state bindings. Pinned OpenAI Agents JS
  examples prove both bound-state decisions in
  `examples/agent-patterns/human-in-the-loop-stream.ts` and inline `result.state` decisions in
  `examples/mcp/hosted-mcp-human-in-the-loop.ts`.
- Alternative: Treat every `.approve(...)`/`.reject(...)` receiver or every variable named `state`
  as approval evidence. Rejected because ordinary application state and same-named helper objects
  can have unrelated methods.
- Revisit when: `RunState.fromString(agent, storedState)` can be linked back to serialized
  `result.state` without broad string/dataflow inference, or when approval predicate analysis can
  classify whether decisions cover specific risky tool calls.

## OpenAI RunState.fromString continuity requires a proven serialized SDK state chain

- Decision: Treat `RunState.fromString(agent, serializedState)` as OpenAI Agents JS run-state
  continuity only when `RunState` is an exact unshadowed import from `@openai/agents`, the first
  argument resolves to the same local agent used by the original exact SDK `run(...)`, and the
  serialized-state argument is sourced from a same-file `result.state.toString()` or literal
  `writeFile`/`readFile` chain around `JSON.stringify(result.state, ...)`.
- Evidence: The real OpenAI Agents JS `examples/agent-patterns/human-in-the-loop.ts` example writes
  `JSON.stringify(result.state, ...)` to `result.json`, reads it back into `storedState`, restores
  with `RunState.fromString(agent, storedState)`, then calls `state.approve/reject` before resuming
  `run(agent, state)`. Local negatives cover loose serialized strings, unknown run results, and
  stale result bindings before serialization.
- Alternative: Accept any string passed to `RunState.fromString`. Rejected because a string can be
  arbitrary application data and does not prove OpenAI SDK run-state continuity or approval
  handling.
- Revisit when: cross-function or nonliteral persistence flows can be modeled with source-proven
  dataflow without accepting unrelated file/string state.

## OpenAI builtin approval callbacks are callback-controlled policy evidence

- Decision: Treat callback-valued `needsApproval` on exact OpenAI Agents JS approval-capable
  builtin tool constructors, such as `computerTool({ needsApproval: async ... })`, as
  `approval_policy: callback-controlled` with `approval_handler: needsApproval-callback` and
  `approval_decision: dynamic-callback`. Keep separate `onApproval`/handler-like options as
  unresolved-handler evidence unless a `needsApproval` policy expression is present.
- Evidence: The pinned OpenAI Agents JS `examples/tools/computer-use-hitl.ts` example configures
  `computerTool` with callback-valued `needsApproval` in both singleton and per-request computer
  flows. Local `cases/typescript_structured_tools` now includes the same shape beside literal
  approval and delegated-agent approval cases, and the public IR truth set regenerates at 1,977/1,977
  passing labels.
- Alternative: Continue classifying builtin callback approval as `unresolved-handler`. Rejected
  because the callback is attached to the SDK-native `needsApproval` policy key and has the same
  meaning as generic `tool({ needsApproval: async ... })`: dynamic policy selection, not an
  unrelated handler.
- Revisit when: predicate-aware approval-quality analysis can inspect callback bodies and relate
  action/input predicates to risky builtin operations, especially automatic approvals or narrow
  action allowlists.

## OpenAI applyPatchTool literal options imply local filesystem editing

- Decision: Treat exact OpenAI Agents JS `applyPatchTool({ editor, ... })` calls with literal object
  options as `execution_environment: local` and propagate that environment to the associated
  filesystem capability with `write_access: true`. Keep nonliteral `applyPatchTool(options)` calls
  unresolved because runtime-provided options can hide editor, approval, or environment policy.
- Evidence: The OpenAI Agents JS SDK models `applyPatchTool` as an editor-backed builtin patch
  tool, the docs `examples/docs/tools/localBuiltInTools.ts` example passes a local editor alongside
  `needsApproval: true`, and `examples/tools/apply-patch.ts` constructs a `WorkspaceEditor` from a
  workspace root before passing it to `applyPatchTool`. Local scanner tests now pin the literal
  positive and the nonliteral-options negative, and the public IR truth set adds the real docs
  filesystem-capability label.
- Alternative: Leave all `applyPatchTool` execution environments unresolved, or mark every
  `applyPatchTool(...)` call local. Rejected because literal object options prove the SDK-native
  editor-backed filesystem surface while nonliteral options are intentionally opaque.
- Revisit when: the SDK introduces hosted or remote editor implementations, or examples expose
  explicit execution-environment options that need finer-grained classification.

## TypeScript same-class startsWith path helpers are weak prefix checks

- Decision: Record exact TypeScript same-class helper methods that return a `path.resolve(...)`
  candidate after a throwing `candidate.startsWith(this.root)` rejection as `path-prefix-check`
  controls, not as strong `path-boundary` controls. Propagate the weak check only to same-class
  filesystem writes whose path argument is assigned from `await this.helper(...)`; leave unchecked
  same-class writes unresolved.
- Evidence: OpenAI Agents JS' `examples/tools/apply-patch.ts` `WorkspaceEditor.resolve` helper
  checks `resolved.startsWith(this.root)` before returning `resolved`, and its create/update/delete
  methods write paths assigned from `await this.resolve(operation.path)`. The local
  `cases/typescript_path_boundary/class-helper.ts` fixture pins the positive propagation and an
  unchecked same-class write negative; the public IR truth set adds six local/real labels.
- Alternative: Treat `startsWith(this.root)` as a constrained path boundary, or ignore same-class
  TypeScript helpers entirely. Rejected because raw string prefixes admit sibling-prefix paths such
  as `/workspace-escape`, but ignoring the helper loses useful review evidence.
- Revisit when: separator-aware TypeScript same-class helpers, `path.relative`/`path.matchesGlob`
  patterns, or constructor-bound literal root scopes can be modeled without broad name matching.

## OpenAI approval predicate inventory starts with shallow literal predicates

- Decision: Record only exact shallow literal `needsApproval` predicates in OpenAI Agents JS
  approval metadata: `field.startsWith("literal")`, `field.includes("literal")`, and
  `["literal", ...].includes(action.field)`. Apply the same vocabulary to generic `tool(...)`,
  delegated `agent.asTool(...)`, and approval-capable builtin constructors.
- Evidence: Pinned OpenAI Agents JS examples cover all three shapes: `command.startsWith(...)` in
  the local CLI fixture, `subject.includes("spam")` in the docs tool definition,
  `city.includes("Oakland")` and `input.includes("San Francisco")` in HITL examples, and
  `["click", "type", "keypress"].includes(action.type)` in the computer-use HITL examples.
  Focused approval-control labels passed 51/51 and the full public IR truth set regenerated at
  1,987/1,987 passing labels.
- Alternative: Interpret arbitrary callback bodies or helper calls as approval-quality evidence.
  Rejected because callback semantics can invert, combine, or delegate decisions in ways that need
  a real expression model; shallow literal predicates add useful review metadata without claiming
  complete risky-action coverage.
- Revisit when: compound boolean predicates, helper-return summaries, or action-specific risk
  mapping can be modeled and regression-labeled without accepting broad same-named fields.

## OpenAI Agents JS computer safety checks are separate from human approval

- Decision: Inventory exact `computerTool({ onSafetyCheck })` callbacks as safety-check metadata,
  not generic human-approval metadata. Report `AV-APPROVAL011` only when a reachable
  computer-control capability auto-acknowledges all pending safety checks by returning `true` or by
  returning the full `pendingSafetyChecks` list through the SDK-supported
  `acknowledgedSafetyChecks` or `acknowledged_safety_checks` result key, including ordinary
  block-body returns and parenthesized expression-bodied object returns.
- Evidence: The pinned OpenAI Agents JS `examples/tools/computer-use-hitl.ts` file contains a
  singleton computer tool with `needsApproval` but no `onSafetyCheck`, and a per-request computer
  tool whose `onSafetyCheck` callback returns the full pending safety-check list as acknowledged.
  Local focused rule and IR labels passed 14/14 before full benchmark regeneration, including the
  SDK-supported snake_case acknowledgement key and expression-bodied object return shape.
- Alternative: Treat any configured safety-check callback as safe or unsafe. Rejected because
  callback existence alone does not prove review quality, while exact pass-through and return-true
  callbacks prove auto-acknowledgement without modeling arbitrary helper logic.
- Revisit when: richer safety-check callback semantics, safety-check type matching, or explicit
  policy/user-review handoff patterns can be source-proven and labeled.

## OpenAI Agents Python computer safety auto-ack stays scope-proven

- Decision: Extend `AV-APPROVAL011` to exact OpenAI Agents Python
  `ComputerTool(on_safety_check=...)` callbacks only when auto-acknowledgement is source-proven:
  inline `lambda ...: True`, or a callback name that resolves in the current lexical scope or safe
  module fallback to one same-file function with no earlier return/raise and a final `return True`.
- Evidence: The local Python fixture covers no handler, inline lambda, module-level callback,
  conditional callback negative, and inline tool construction. The pinned OpenAI Agents Python
  `tests/test_tool_approval_call_id_reuse.py` file has two same-named nested
  `acknowledge_safety_check` functions in different tests; scope-keyed resolution keeps both exact
  and avoids collapsing duplicate module names.
- Alternative: Resolve callback names module-globally or treat any `on_safety_check` callback as a
  review finding. Rejected because duplicate nested functions in the real SDK tests prove that
  module-global name matching is unsafe, and callback existence does not prove pass-through or
  explicit review behavior.
- Revisit when: callback helpers with explicit safety-code allowlists or user-review calls can be
  modeled without accepting arbitrary boolean expressions.

## OpenAI Agents JS run-state approval bypass remains control metadata

- Decision: Record environment-backed approval bypass provenance on exact OpenAI Agents JS
  `RunState.approve(...)` controls, but do not introduce a new reporting rule yet.
- Evidence: The pinned OpenAI Agents JS HITL examples call `state.approve(interruption)` only after
  a confirmation helper. That helper has an `AUTO_APPROVE_HITL` true-return branch before the
  readline prompt. Local fixtures prove both an unreassigned boolean guard and direct
  `await confirm(...)` guard, while reject branches and reassigned booleans stay unannotated.
- Alternative: Report every env-backed approval decision as an approval-bypass finding. Rejected for
  now because these examples still contain an explicit reject path and the current evidence is best
  treated as governance metadata until a rule can model whether the bypass is enabled in production
  defaults or CI.
- Revisit when: reporting policy can distinguish intentional test/demo auto-approval from
  production approval bypasses on restored run-state decisions.

## OpenAI Agents Python approval decisions require proven SDK run state

- Decision: Record Python OpenAI Agents SDK `state.approve(...)` and `state.reject(...)` as
  `approval-decision` controls only when the receiver state is source-proven from an exact SDK run
  result via `result.to_state()` or from an exact `RunState.from_json/from_string(...)` restore tied
  to a proven agent.
- Evidence: Local regression fixtures cover direct `Runner.run`, module-qualified
  `agents.Runner.run_streamed`, loose state lookalikes, and rebound state variables. Pinned OpenAI
  Agents Python HITL examples validate restored JSON state, streaming state, and hosted MCP
  approve/reject handling.
- Alternative: Treat any `.approve(...)` or `.reject(...)` call as approval evidence. Rejected
  because real Python repositories and tests contain arbitrary helper names and state-like objects;
  the IR should preserve SDK provenance instead of granting generic method-name trust.
- Revisit when: richer Python serialized-state chains can tie file or database persistence back to
  a specific `result.to_state()` without broad name matching.

## OpenAI Agents Python sticky approval persistence stays metadata

- Decision: Preserve OpenAI Agents Python `always_approve` and `always_reject` keyword arguments as
  `approval-decision` control and governed-edge metadata, classifying literal or stable
  same-function boolean values as `always` or `per-call` and unresolved prompt/runtime values as
  `dynamic`.
- Evidence: The local approval-decision fixture covers literal `always_approve=True`, stable
  same-function `always_reject=always` with `always = True`, and stable
  `always_approve=once` with `once = False`. The pinned OpenAI Agents Python shell HITL example
  passes a prompt-derived `always` variable to both approve and reject calls, which is preserved as
  dynamic persistence rather than over-resolved.
- Alternative: Treat any `always_*` keyword as a reporting finding or infer arbitrary boolean
  expressions. Rejected because sticky approval can be intentional SDK behavior, and prompt/runtime
  expressions do not prove a default bypass statically.
- Revisit when: a reporting rule can distinguish production-default sticky approval from explicit
  user-selected persistence, or when richer local constant propagation can stay exact without
  crossing mutable module/global state.

## OpenAI Agents run-state rejection messages preserve provenance, not text

- Decision: Record custom rejection-message presence and source classification on source-proven
  OpenAI Agents run-state `reject` decisions, but do not store the message text in Agent IR.
  Python `rejection_message=` and TypeScript `{ message }` options are classified as `literal`,
  `literal-binding`, `template`, or `dynamic`.
- Evidence: The OpenAI Agents Python `RunState.reject(...)` signature includes
  `rejection_message`; the pinned `human_in_the_loop_custom_rejection.py` example passes a literal
  custom message on a source-proven state. Local Python and TypeScript fixtures pin literal,
  literal-binding, template, and dynamic message sources. The visible TypeScript
  `computer-use-hitl.ts` custom message is not labeled because its reject call receives the agent
  through a helper parameter, which the current exact run-state detector intentionally does not
  infer.
- Alternative: Store full rejection strings or report custom messages as findings. Rejected because
  full message text is unnecessary for governance inventory and may expose sensitive developer
  policy text, while custom rejection messaging is not itself unsafe.
- Revisit when: rejection-message provenance needs richer policy classification; the first narrow
  TypeScript helper-parameter state model is now tracked separately below.

## OpenAI Agents JS helper-parameter approval decisions require exact call-site agents

- Decision: Resolve TypeScript OpenAI Agents SDK approval/rejection decisions through non-exported
  same-file `async function` helpers only when the first helper parameter is typed as the exact SDK
  `Agent` import, the helper body proves `run(agentParam, ...) -> result.state ->
  state.approve/reject`, and each helper call supplies an exact Agent binding from the same lexical
  function scope. Helper-derived control IDs include the call line so repeated scoped `const agent`
  bindings do not collapse.
- Evidence: The local `cases/typescript_openai_helper_hitl` fixture has two sibling functions that
  both declare `const agent` and call the same `runWithHitl(agent, ...)` helper; AgentVerify emits
  two separate template-message rejection controls tied to `agent@4` and `agent@9`. Near misses
  cover a helper called with an unresolved caller parameter and an untyped helper. The pinned
  OpenAI Agents JS `examples/tools/computer-use-hitl.ts` example now proves both `state.approve`
  and custom template-message `state.reject` controls for the singleton and per-request browser
  agents, preserving `AUTO_APPROVE_HITL` metadata on the approval branches.
- Alternative: Treat any helper parameter named `agent`, any same-file helper call, or any global
  same-named `agent` binding as source proof. Rejected because the real file already has repeated
  scoped `const agent` bindings, and arbitrary helper parameters would turn state-like methods into
  false approval evidence.
- Revisit when: a similarly narrow model can prove exported helper calls without accepting
  mixed/unproven call sites.

## OpenAI Agents JS helper-parameter state resumes require exact helper-local state provenance

- Decision: Resolve TypeScript OpenAI Agents SDK run-state resume continuity through the same
  same-file helper-parameter model only when the helper proves `run(agentParam, ...) ->
  result.state` and later passes that exact unreassigned state binding as the second argument to
  imported SDK `run(agentParam, state)`. Helper-derived continuity control IDs include the helper
  call line, and configured-by resume edges keep `helper_resume_line` and `helper_state_line`
  provenance.
- Evidence: The local `cases/typescript_openai_helper_hitl` fixture now emits two separate
  `conversation-continuity` controls and resume edges for two sibling lexical `const agent` call
  sites. The pinned OpenAI Agents JS `examples/tools/computer-use-hitl.ts` helper emits two
  real-corpus helper-parameter state resumes tied to the singleton and per-request browser agents.
- Alternative: Infer continuity for arbitrary helper parameters, exported helpers, or state-like
  variables passed to helper calls. Rejected because that would collapse caller identity and turn
  helper implementation details into cross-procedural claims without exact source-agent proof.
- Revisit when: a broader interprocedural call-state model can retain per-call-site identity,
  reject mixed/unproven call sites, and prove exported/imported helper bodies without repository-wide
  name matching.

## OpenAI Agents JS trace identifiers are audit correlation, not memory

- Decision: Represent exact TypeScript OpenAI Agents SDK `withTrace(..., { groupId })` calls as
  distinct `trace-group` controls and `withTrace(..., { traceId })` calls as distinct `trace-id`
  controls only when the imported `withTrace` helper wraps a callback containing a source-proven
  exact SDK `run(agent, ...)` call. Preserve static IDs when literal, direct identifier group IDs as
  dynamic bindings, and direct trace IDs from imported `generateTraceId()` as generated bindings.
- Evidence: The local conversation fixture covers a literal `groupId` positive and a missing
  trace option negative, plus a generated `traceId` positive. The pinned OpenAI Agents JS
  `examples/agent-patterns/routing.ts` example wraps `run(agent, inputs, ...)` inside
  `withTrace(..., { groupId: conversationId })`; the scanner links the alias-resolved
  `triage_agent` to a `trace-group` configured-by edge. The pinned `examples/tools/codex.ts`
  example calls `generateTraceId()`, logs the OpenAI platform trace URL, and passes `{ traceId }`
  around two Codex-agent runs.
- Alternative: Fold trace identifiers into `conversation-session` or `conversation-continuity`.
  Rejected because trace `groupId` and `traceId` are observability/audit correlation evidence, not
  proof that the SDK persists or reuses conversation state.
- Revisit when: trace exports, processors, or durable trace sinks can be proven and linked to the
  same source-agent identity.

## OpenAI Agents JS Runner group IDs are trace correlation, not Runner memory

- Decision: Represent exact TypeScript OpenAI Agents SDK `new Runner({ groupId })` configuration as
  `trace-group` controls only when the `Runner` constructor is an unshadowed exact SDK import, the
  Runner variable is stable, and a later `.run(agent, ...)` call on the same variable supplies a
  source-proven Agent. Keep this as a separate `typescript-openai-agents-runner-trace-group`
  analysis from `withTrace(..., { groupId })`.
- Evidence: The local conversation fixture adds an immutable module literal `runnerTraceGroupId`
  positive and a reassigned Runner negative. The pinned OpenAI Agents JS
  `examples/sandbox/memory-generation.ts` example constructs
  `new Runner({ groupId: 'sandbox-memory-generation-example' })` and immediately runs
  `Sandbox Memory Generation Demo`; AgentVerify links that agent to the Runner-level trace group.
- Alternative: Treat any object named `runner` or any `.run(...)` receiver with a `groupId`-looking
  constructor nearby as trace evidence. Rejected because Runner-level metadata only follows the run
  when the exact SDK constructor and stable instance identity are proven.
- Revisit when: exported Runner factories or shared Runner instances can be resolved without
  collapsing source-agent identity across unrelated `.run(...)` receivers.

## OpenAI Agents JS Runner tracing disablement is explicit observability policy

- Decision: Represent exact TypeScript OpenAI Agents SDK `new Runner({ tracingDisabled: true })`
  configuration as a `tracing-disabled` control only when the `Runner` constructor is an
  unshadowed exact SDK import, the Runner variable is stable, and a later `.run(agent, ...)` call on
  the same variable supplies a source-proven Agent. Do not emit for `tracingDisabled: false` or
  rebound Runner variables.
- Evidence: The local conversation fixture covers a direct true positive, an explicit false
  negative, and a reassigned Runner negative. The pinned OpenAI Agents JS
  `examples/docs/testing/toolWorkflow.ts` and `examples/docs/testing/sandboxWorkflow.ts` examples
  both disable tracing to avoid exporter/network behavior in scripted tests; AgentVerify links the
  `Weather assistant` and `Workspace assistant` agents to those controls.
- Alternative: Treat disabled tracing as an audit finding by default. Rejected for now because
  examples often disable tracing intentionally in tests; the IR should preserve the governance fact
  and let policy decide whether disabled tracing is acceptable for the repository scope.
- Revisit when: run-level `runConfig.tracingDisabled` or exported Runner/delegated-tool factories
  can be attributed to exact source agents without collapsing adapter/tool semantics.

## OpenAI Agents JS delegated asTool tracing disablement belongs to the delegated agent

- Decision: Represent exact TypeScript OpenAI Agents SDK
  `agent.asTool({ runConfig: { tracingDisabled: true } })` configuration as a
  `tracing-disabled` control on the delegated/source agent, not on the parent orchestrator or on a
  synthetic tool. Preserve the parent agent, delegated agent, and literal `toolName` when proven,
  and emit only for literal `true`; literal `false`, missing values, and ambiguous targets stay
  unresolved.
- Evidence: The local sandbox-runtime fixture covers a positive delegated tool and an explicit
  false negative. The pinned OpenAI Agents JS
  `examples/sandbox/sandbox-agents-as-tools.ts` example disables tracing for both the
  `Pricing Packet Reviewer` and `Rollout Risk Reviewer` delegated reviewers while the parent
  remains `Revenue Operations Coordinator`.
- Alternative: Attach delegated `runConfig.tracingDisabled` to the parent agent's
  `delegates-to` edge only. Rejected because the SDK run configuration applies to the delegated
  agent execution, and policy review needs that source-agent identity even when the parent is the
  caller.
- Revisit when: broader `runConfig` trace metadata or exported delegated-tool factories can be
  proven without weakening the exact `asTool` source/target attribution.

## OpenAI Agents JS delegated asTool turn limits are bounded execution controls

- Decision: Represent exact TypeScript OpenAI Agents SDK
  `agent.asTool({ runOptions: { maxTurns: <integer> } })` configuration as an
  `agent-turn-limit` control on the delegated/source agent. Preserve the parent agent and literal
  `toolName` when proven, and emit only for literal integer `maxTurns`; missing and nonliteral
  values stay unresolved.
- Evidence: The local structured-tools fixture proves the `worker_tool` delegated agent limit and
  a sibling delegated tool without `maxTurns` remains negative. The pinned OpenAI Agents JS
  `examples/agent-patterns/agents-as-tools.ts` translator limits the Spanish delegated agent to
  three turns, while `examples/sandbox/sandbox-agents-as-tools.ts` limits both sandbox reviewer
  delegated agents to eight turns.
- Alternative: Treat `maxTurns` as generic run metadata on the parent orchestrator. Rejected
  because the bounded execution applies to the delegated agent invocation and should be reviewable
  with the delegated agent's own capabilities and sandbox/tracing controls.
- Revisit when: direct `run(..., { maxTurns })`, Runner defaults, or exported delegated-tool
  factories can be linked to exact source-agent identity without broad receiver/name matching.

## OpenAI Agents JS delegated asTool model overrides are delegated execution policy

- Decision: Represent exact TypeScript OpenAI Agents SDK
  `agent.asTool({ runConfig: { model: ... } })` configuration as an `agent-model-override` control
  on the delegated/source agent. Accept direct literal model strings and earlier immutable
  module-level literal bindings, preserve provider inference, parent agent, tool name, and shallow
  literal `modelSettings.reasoning.effort` / `modelSettings.text.verbosity` when present. Do not
  emit for missing, mutable, or nonliteral model expressions.
- Evidence: The local structured-tools fixture proves a delegated `worker_tool` override to
  `gpt-5.4` with low reasoning and low verbosity while a sibling delegated tool without a model
  override remains negative. The pinned OpenAI Agents JS
  `examples/agent-patterns/agents-as-tools.ts` translator example sets the Spanish delegated agent's
  model and model settings in `runConfig`.
- Alternative: Treat delegated model strings as generic model components only. Rejected because
  policy review needs the relationship between the parent orchestrator, delegated agent, tool name,
  and the model override that applies only to that delegated invocation.
- Revisit when: direct `run(..., { model/modelSettings })`, Runner defaults, or exported
  delegated-tool factories can be linked to exact source-agent identity without broad config/name
  matching.

## OpenAI Agents JS delegated asTool workflow names are trace workflow provenance

- Decision: Represent exact TypeScript OpenAI Agents SDK
  `agent.asTool({ runConfig: { workflowName: ... } })` configuration as a `trace-workflow` control
  on the delegated/source agent. Accept direct literal workflow names and earlier immutable
  module-level literal bindings, preserve parent agent and tool name, and do not emit for missing,
  mutable, or nonliteral workflow-name expressions.
- Evidence: The local structured-tools fixture proves delegated `worker_tool` workflow naming as
  `Worker delegation` while a sibling delegated tool without `workflowName` remains negative. The
  pinned OpenAI Agents JS sandbox agents-as-tools example names the delegated pricing and rollout
  reviewer workflows in `runConfig`.
- Alternative: Treat delegated workflow names as generic trace metadata on the parent orchestrator.
  Rejected because the workflow name applies to the delegated invocation and needs to be reviewed
  with the delegated agent's own model, sandbox, tracing, and turn-limit policy.
- Revisit when: direct `run(..., { workflowName })`, Runner defaults, exported delegated-tool
  factories, or broader trace metadata can be linked to exact source-agent identity without broad
  config/name matching.

## OpenAI Agents JS Runner workflow names are per-run trace workflow provenance

- Decision: Represent exact TypeScript OpenAI Agents SDK stable
  `new Runner({ workflowName: ... })` configuration as a `trace-workflow` control for each later
  same-instance `.run(agent, ...)` call with source-proven agent identity. Accept direct literal
  workflow names and earlier immutable module-level literal bindings, preserve the runner binding,
  and do not emit when the Runner binding is reassigned or the workflow expression is nonliteral.
- Evidence: The local conversation fixture reuses a stable `runner` across conversation, history,
  and state-resume calls, producing distinct run-site workflow edges. The negative fixture rebinding
  keeps a mutable Runner workflow name unresolved. The pinned OpenAI Agents JS Blaxel and Cloudflare
  sandbox extension examples declare Runner workflow names and call `runner.run(...)` in both normal
  and streaming branches.
- Alternative: Collapse the Runner workflow to one component per constructor. Rejected because
  existing Runner trace-group provenance is per exact run site, and policy review benefits from the
  same callsite-level edge for workflow names.
- Revisit when: direct `run(..., { workflowName })`, exported Runner factories, or inherited Runner
  defaults can be linked to exact source-agent identity without broad receiver/name matching.

## OpenAI Agents JS run-call maxTurns are agent-run execution controls

- Decision: Represent exact TypeScript OpenAI Agents SDK direct
  `run(agent, input, { maxTurns: <integer> })` calls and stable exact
  `runner.run(agent, input, { maxTurns: <integer> })` calls as `agent-turn-limit` controls on the
  source-proven run agent. Emit only for literal integer `maxTurns` values in the third options
  argument, preserve the imported direct-run local binding or stable Runner binding, and do not
  infer through missing, nonliteral, or reassigned options.
- Evidence: The local conversation fixture proves both direct imported `run(...)` and
  stable `Runner.run(...)` turn caps while its unrelated previous-response path remains negative.
  The pinned OpenAI Agents JS sandbox capability examples contribute direct `run(..., { maxTurns })`
  controls, and the hosted MCP human-in-the-loop example contributes stable Runner-run controls.
- Alternative: Treat run-call `maxTurns` as generic runtime metadata detached from the source
  agent. Rejected because policy review needs the exact agent whose execution is bounded at that
  run site, alongside its conversation, sandbox, tracing, and approval evidence.
- Revisit when: Runner constructor defaults, exported Runner factories, or inherited run options
  can be linked to exact source-agent identity without broad receiver/name matching.

## OpenAI Agents JS run-call streaming is event-surface inventory

- Decision: Represent exact TypeScript OpenAI Agents SDK direct
  `run(agent, input, { stream: true })` calls and stable exact
  `runner.run(agent, input, { stream: true })` calls as `streaming-run` controls on the
  source-proven run agent. Emit only for literal `stream: true` in the third options argument,
  preserve the imported direct-run local binding or stable Runner binding, and do not infer through
  missing, false, dynamic, or reassigned options.
- Evidence: The local conversation fixture proves both direct imported `run(...)` streaming and
  stable `Runner.run(...)` streaming state-resume shapes. The pinned OpenAI Agents JS hosted MCP
  human-in-the-loop example contributes two stable Runner-run streaming branches around the
  interruption loop.
- Alternative: Treat streaming as durable observability or audit coverage. Rejected because
  `stream: true` proves the run exposes streaming events, not that those events are persisted,
  reviewed, attributed to an actor, or exported to an audit sink.
- Revisit when: downstream stream consumers such as `toTextStream(...)`, event handlers, persisted
  event logs, or interruption-review UIs can be linked to exact source-agent identity without
  broad callback/name matching.

## OpenAI Agents JS Agent toolChoice is source-agent model-settings policy

- Decision: Represent exact TypeScript OpenAI Agents SDK
  `new Agent({ modelSettings: { toolChoice: <literal> } })` configuration as a
  `tool-choice-policy` control on that source agent. Accept direct literal strings and earlier
  immutable module-level literal bindings; keep mutable or nonliteral values unresolved.
- Evidence: The local structured-tools fixture proves a literal `required` tool-choice setting on
  the worker agent and keeps a mutable `toolChoice` binding negative. The pinned OpenAI Agents JS
  docs forcing-tool-use example sets `toolChoice: 'required'`, while the programmatic tool-calling
  example sets `toolChoice: 'programmatic_tool_calling'`.
- Alternative: Fold tool choice into generic model/provider metadata. Rejected because tool-choice
  policy changes whether/how the model may invoke tools and should be reviewable next to approval,
  tool reachability, and local execution controls.
- Revisit when: Runner-level `modelSettings.toolChoice`, run-level overrides, or exported agent
  factories can be tied to exact source-agent identity without broad constructor/name matching.

## OpenAI Agents JS Runner toolChoice is per-run model-settings policy

- Decision: Represent exact TypeScript OpenAI Agents SDK stable
  `new Runner({ modelSettings: { toolChoice: <literal> } })` configuration as a
  `tool-choice-policy` control for each later same-instance `.run(agent, ...)` call with
  source-proven agent identity. Accept direct literal strings and earlier immutable module-level
  literal bindings; keep reassigned Runner bindings and nonliteral choices unresolved.
- Evidence: The local conversation fixture reuses a stable Runner with `toolChoice: 'required'`
  across multiple source-proven run sites and keeps a rebound Runner negative. The pinned OpenAI
  Agents JS hosted MCP human-in-the-loop example uses `initialRunner` with
  `toolChoice: 'required'` before approval and `resumeRunner` with `toolChoice: 'auto'` afterward.
- Alternative: Attach Runner tool-choice only to the Runner constructor. Rejected because the
  policy applies when that Runner executes a specific source agent, and review needs the same
  callsite-level edge used for Runner trace and workflow policy.
- Revisit when: run-level `modelSettings.toolChoice`, exported Runner factories, or inherited
  Runner defaults can be linked to exact source-agent identity without broad receiver/name matching.

## OpenAI Agents JS computerTool backend lifecycle is review metadata

- Decision: Record exact TypeScript OpenAI Agents SDK `computerTool({ computer })` backend lifecycle
  metadata on the tool and `computer-control` capability. Object literals with callback-valued
  `create` and `dispose` are `create-dispose-per-run`; object literals with callback-valued `create`
  and no `dispose` are `factory-without-dispose`; shorthand or identifier computer values remain
  `external-binding` metadata without inferred ownership.
- Evidence: The local computer-safety fixture covers inline static computer objects, a per-run
  create/dispose factory, and a create-only factory. The pinned OpenAI Agents JS
  `examples/tools/computer-use-hitl.ts` and `examples/tools/computer-use.ts` per-request examples
  use `create` and `dispose` callbacks that receive `runContext` and `computer`, while the
  singleton HITL example passes an external `computer` binding.
- Alternative: Treat any `computer` object as equally lifecycle-managed. Rejected because a
  create-only factory lacks disposal evidence, while an external binding may be intentionally
  singleton or managed elsewhere.
- Revisit when: imported computer factory helpers, class methods, or explicit browser/backend
  constructor provenance can be linked without broad name matching.

## OpenAI Agents JS Agent model settings are source-agent policy metadata

- Decision: Record exact TypeScript OpenAI Agents SDK Agent-level literal
  `modelSettings.reasoning.effort`, `modelSettings.text.verbosity`, and
  `modelSettings.parallelToolCalls` as `model-settings-policy` controls on the source agent. Emit
  only for direct nested string literals or direct boolean `parallelToolCalls` literals in exact
  imported `new Agent(...)` model settings; keep mutable or nonliteral nested values unresolved.
- Evidence: The local structured-tools fixture covers a worker agent with literal low reasoning and
  verbosity settings and a dynamic-policy negative with a mutable nested effort. The pinned OpenAI
  Agents JS `examples/tools/web-search-filters.ts` example sets both low reasoning and low
  verbosity, while `examples/tools/apply-patch.ts` sets low reasoning for a patch-capable agent.
  The local parallel-tool-calls fixture covers true, false, and dynamic negative cases, and the
  pinned `examples/tools/tool-search.ts` example sets `parallelToolCalls: false` for two Agents.
- Alternative: Fold reasoning/verbosity into generic provider/model components or into
  `tool-choice-policy`. Rejected because these settings alter model behavior but are distinct from
  provider choice, from whether tools are forced/auto-selected, and from session constructor
  configuration.
- Revisit when: run-level model settings, Runner-level defaults, or imported model-settings objects
  can be tied to exact source-agent identity without broad config/name matching.

## OpenAI Realtime session config is separate source-agent policy metadata

- Decision: Represent exact TypeScript OpenAI Realtime
  `new RealtimeSession(agent, { model })` and
  `new RealtimeSession(agent, { model, config: { parallelToolCalls: <boolean>,
  reasoning: { effort }, outputModalities: [...], audio: { input, output } } })`
  configuration as a `realtime-session-config-policy` control tied to the source-proven
  `RealtimeAgent` passed as the session's first constructor argument. Emit only for exact imported
  `RealtimeAgent` and `RealtimeSession` constructors plus direct boolean, direct static session
  model strings, config strings, or literal string-array values, including audio input/output formats
  and
  `audio.input.transcription.{model, delay, prompt, keywords, languages}`; keep dynamic config
  values and unresolved session-agent arguments unresolved. Do not persist full transcription prompt
  text in IR attributes; record literal prompt presence and length only, alongside literal keyword
  arrays and counts.
- Evidence: The local realtime-session fixture covers false, true, and dynamic negative
  `parallelToolCalls` values plus a direct low `reasoning.effort` value and a literal
  `outputModalities: ["audio"]` value with a dynamic-modality negative, plus a literal audio
  details session with exact top-level session model metadata, a model-only session, and dynamic
  session/transcription model negative coverage. The pinned OpenAI Agents JS
  `examples/docs/voice-agents/configureSession.ts` example sets
  `model: 'gpt-realtime-2.1'`, `config.outputModalities: ['audio']`,
  `config.reasoning.effort: 'low'`, and `config.parallelToolCalls: true`, plus
  `audio.input.format: 'pcm16'`,
  `audio.output.format: 'pcm16'`, `audio.input.transcription.model: 'gpt-live-transcribe'`,
  `audio.input.transcription.delay: 'low'`, transcription prompt length, transcription keywords,
  and transcription languages `['en', 'ja']` for the `Greeter` RealtimeAgent. The pinned
  `examples/docs/voice-agents/sendMessage.ts` example proves model-only session options for the
  `Assistant` RealtimeAgent.
- Alternative: Fold realtime session config into Agent-level `model-settings-policy`. Rejected
  because `RealtimeSession` configuration is a different constructor scope from `Agent.modelSettings`
  and should not imply the same inheritance or override semantics.
- Revisit when other RealtimeSession config fields such as turn detection or tool choice can be tied
  to source-proven realtime agents without broad option-object matching.

## OpenAI Agents JS web-search scope is tool/provider policy metadata

- Decision: Record exact TypeScript OpenAI Agents SDK `webSearchTool` literal
  `filters.allowedDomains`, `searchContextSize`, and `userLocation` values as `web-search-policy`
  controls on the source tool and as metadata on its `external-action` capability. Separately
  record exact literal `Agent.modelSettings.providerData.include` arrays as `provider-data-policy`
  controls on the source agent, marking web-search source inclusion only when
  `web_search_call.action.sources` is explicitly requested.
- Evidence: The local `typescript_openai_web_search_policy` fixture covers literal policy evidence
  and dynamic-domain/dynamic-user-location/dynamic-provider-data negatives. The pinned OpenAI
  Agents JS
  `examples/tools/web-search-filters.ts` example sets an OpenAI-domain allowlist, medium search
  context size, and `web_search_call.action.sources` inclusion; `examples/tools/web-search.ts`
  sets an approximate New York user location; and `examples/docs/tools/hostedTools.ts` sets a
  medium context size.
- Alternative: Treat all `webSearchTool()` use as equally governed external access. Rejected
  because unfiltered hosted web search and domain-constrained search have materially different
  review semantics, approximate user location has separate privacy/scope meaning, and source
  inclusion is an Agent provider-data setting rather than a tool constructor setting.
- Revisit when imported literal option objects or OpenAI-compatible provider-defined web search
  factories can be tied to exact source-tool/source-agent identity without broad config matching.

## OpenAI Realtime output guardrails are source-agent governance controls

- Decision: Represent exact TypeScript OpenAI Realtime
  `new RealtimeSession(agent, { outputGuardrails, outputGuardrailSettings })` options as
  `realtime-session-guardrail-policy` controls tied to the source-proven `RealtimeAgent` passed as
  the first constructor argument. Record inline-array, typed-const-array-binding, dynamic-expression,
  and binding-only guardrail sources; record literal guardrail names/counts and direct signed integer
  `outputGuardrailSettings.debounceTextLength` values when exact.
- Evidence: The local `typescript_openai_realtime_session_guardrails` fixture covers a typed
  `RealtimeOutputGuardrail[]` binding with a literal name, an inline guardrail array with
  `debounceTextLength: -1`, a typed `RealtimeSessionOptions` spread with
  `debounceTextLength: 500`, a mutated typed-array negative that stays binding-only, and a dynamic
  debounce negative. The pinned OpenAI Agents JS `examples/docs/voice-agents/guardrails.ts` example
  contributes a typed guardrail array named `No mention of Dom`, and
  `examples/docs/voice-agents/guardrailSettings.ts` contributes `debounceTextLength: 500` with a
  comment-only placeholder array counted as zero concrete guardrails.
- Alternative: Fold guardrail presence into generic RealtimeSession config metadata. Rejected
  because guardrails are governance/safety controls with distinct review semantics from model,
  audio, turn-detection, or auth configuration.
- Revisit when imported guardrail arrays, helper-created guardrails, input guardrails, or guardrail
  tripwire/action quality can be tied to exact source-agent identity without broad name matching.

## OpenAI Agents JS Codex tool is delegated-runtime inventory

- Decision: Represent exact TypeScript `codexTool(...)` calls from
  `@openai/agents-extensions/experimental/codex` as `Codex tool` components when an exact
  `@openai/agents` `Agent` includes the tool through a stable same-file binding or an inline call in
  a literal `tools` array. Record `defaultThreadOptions` governance metadata, including
  `approvalPolicy`, sandbox mode, network/web-search toggles, model/reasoning, stream callback
  binding, working-directory binding, and `useRunContextThreadId`, and attach explicit
  `tool-approval-policy` controls only when an approval policy is present.
- Evidence: The local `typescript_openai_codex_tool` fixture covers same-file binding, inline
  generic-Agent usage, and a mutated-binding negative. The pinned OpenAI Agents JS
  `examples/tools/codex.ts` and `examples/tools/codex-same-thread.ts` examples contribute real
  labels for `approvalPolicy: 'never'`, workspace-write sandboxing, network/web-search toggles,
  stream callbacks, and run-context thread reuse.
- Alternative: Treat every Codex extension import as an executable tool or emit broad network/code
  capabilities from `networkAccessEnabled`. Rejected because the model-visible surface is only
  source-proven once the `codexTool` value reaches an Agent `tools` array, and network/code
  capability severity needs a separate evidence standard from thread-option inventory.
- Revisit when imported/reexported Codex tool bindings, richer working-directory provenance, or
  reportable approval-policy findings can be tied to exact agent/tool identity without broad helper
  matching.

## OpenAI Realtime guardrail tripwires are conservative quality metadata

- Decision: Record direct `tripwireTriggered` return-object metadata on exact TypeScript OpenAI
  RealtimeSession output guardrail controls. Inline guardrails, stable typed
  `RealtimeOutputGuardrail[]` const arrays, and typed `RealtimeSessionOptions` spreads may
  contribute literal or computed tripwire source counts; mutated guardrail arrays and settings-only
  guardrail configurations do not expose tripwire metadata.
- Evidence: The local `typescript_openai_realtime_session_guardrails` fixture covers typed-array,
  inline-array, typed-options-spread, mutable-array, and settings-only cases. The pinned OpenAI
  Agents JS `examples/docs/voice-agents/guardrails.ts` example contributes a real typed
  Realtime output guardrail whose returned tripwire predicate is computed from `agentOutput`.
- Alternative: Treat Realtime output guardrail presence as sufficient tripwire quality. Rejected
  because placeholder settings, mutable arrays, and throwing or delegated guardrails can exist
  without a source-proven predicate.
- Revisit when imported Realtime guardrail arrays, helper-created guardrails, or richer predicate
  semantics can be resolved without broad callback interpretation.

## OpenAI Agents JS Agent guardrails are source-agent governance controls

- Decision: Represent exact TypeScript OpenAI Agents SDK `new Agent({ inputGuardrails })` and
  `new Agent({ outputGuardrails })` constructor options as `agent-guardrail-policy` controls tied
  to the source agent. Support exact `new Agent<...>(...)` generic constructor syntax, inline
  guardrail arrays, stable typed `InputGuardrail`/`OutputGuardrail` object bindings, generic
  `OutputGuardrail<typeof schema>` bindings, literal names/counts, and binding-only fallbacks.
- Evidence: The local `typescript_openai_agent_guardrails` fixture covers inline input guardrails
  with typed object and inline object entries, generic Agent output guardrails with a generic typed
  output guardrail object, a mutated guardrail object that remains name-unresolved, and a dynamic
  guardrail array that remains binding-only. The pinned OpenAI Agents JS
  `examples/agent-patterns/input-guardrails.ts`, `examples/agent-patterns/output-guardrails.ts`,
  and `examples/docs/running-agents/exceptions1.ts` examples provide real input, output, typed
  object, and generic Agent constructor cases.
- Alternative: Reuse the Realtime guardrail control name. Rejected because SDK Agent guardrails and
  RealtimeSession guardrails live on different constructors and have different execution scopes
  even though both are governance controls.
- Revisit when imported guardrail arrays, helper-created guardrails, richer tripwire/action
  quality, or cross-file Agent guardrail updates can be tied to exact source identity without broad
  name matching.

## OpenAI Agents JS Agent guardrail assignments are fallback policy evidence

- Decision: Represent exact post-construction TypeScript OpenAI Agents SDK assignments such as
  `agent.inputGuardrails = [...]` and `agent.outputGuardrails = [...]` as
  `agent-guardrail-policy` controls on the same source agent, with
  `guardrail_update: property-assignment`. Emit only when the receiver is a stable same-file
  `new Agent(...)` binding and no rebinding occurs between declaration and assignment; keep dynamic
  assignment expressions binding-only.
- Evidence: The local `typescript_openai_agent_guardrails` fixture covers stable input/output
  fallback assignments, dynamic fallback assignment binding-only metadata, rebound-agent negatives,
  and lookalike-object negatives. The pinned OpenAI Agents JS
  `examples/docs/running-agents/exceptions1.ts` example mutates `agent.inputGuardrails` and
  `agent2.outputGuardrails` after `GuardrailExecutionError` to install fallback guardrails before
  retrying.
- Alternative: Ignore post-construction updates because constructor guardrails are already modeled.
  Rejected because fallback/retry code can materially change the active safety policy at runtime
  and appears in official OpenAI guidance.
- Revisit when cross-file exported Agent bindings or helper functions that install fallback
  guardrails can be resolved without treating arbitrary `.inputGuardrails` property writes as SDK
  policy evidence.

## OpenAI Agents JS Agent guardrail tripwires are conservative quality metadata

- Decision: Record direct `tripwireTriggered` return-object metadata on exact TypeScript OpenAI
  Agents SDK Agent guardrail controls. Inline object guardrails and stable typed
  `InputGuardrail`/`OutputGuardrail` bindings may contribute `literal-false`, `literal-true`, or
  `dynamic-expression` tripwire source counts; mutated bindings and dynamic guardrail arrays remain
  unresolved for tripwire quality.
- Evidence: The local `typescript_openai_agent_guardrails` fixture covers method-syntax
  `async execute() { return { tripwireTriggered: false }; }` guardrails, mutated binding
  negatives, and dynamic array negatives. The pinned OpenAI Agents JS
  `examples/agent-patterns/input-guardrails.ts`, `examples/agent-patterns/output-guardrails.ts`,
  and `examples/docs/running-agents/exceptions1.ts` examples contribute computed tripwire
  expressions, including fallback guardrails installed after `GuardrailExecutionError`.
- Alternative: Treat any guardrail with an `execute` callback as having an effective tripwire.
  Rejected because guardrail bodies can throw, delegate, or return dynamic data, and AgentVerify
  should distinguish literal inert tripwires from source-proven computed predicates.
- Revisit when helper-created guardrails, imported guardrail bindings, or richer predicate semantics
  can be resolved without broad callback interpretation.

## OpenAI Agents JS Agent guardrail direct throws are failure-mode metadata

- Decision: Record `guardrail_execution_outcomes: ["direct-throw"]` and
  `guardrail_direct_throw_count` on exact TypeScript OpenAI Agents SDK Agent guardrail controls only
  when a stable inline or typed guardrail `execute` body has `throw` as its first direct statement.
  Do not infer throwing behavior through dynamic arrays, mutated bindings, nested branches, or
  arbitrary exception flows.
- Evidence: The local `typescript_openai_agent_guardrails` fixture includes a stable typed
  `InputGuardrail` whose `execute` directly throws. The pinned OpenAI Agents JS
  `examples/docs/running-agents/exceptions1.ts` file defines unstable input and output guardrails
  that directly throw before fallback guardrails are installed after `GuardrailExecutionError`.
- Alternative: Treat any caught `GuardrailExecutionError` as evidence that the configured guardrail
  throws. Rejected because errors can arise from external calls, runtime state, or different
  guardrails; the IR should stay tied to the exact configured guardrail source.
- Revisit when exception behavior can be tied to helper-created or imported guardrails without
  broad control-flow interpretation.

## OpenAI Agents JS tool guardrail reject predicates are shallow condition metadata

- Decision: Record `guardrail_reject_condition_sources` and
  `guardrail_reject_condition_literals` on exact TypeScript OpenAI Agents SDK tool guardrail
  controls only when a guardrail contains a direct `if (...) { return rejectContent }` branch whose
  predicate uses a literal `.includes(...)` or literal string non-equality check.
- Evidence: The local `typescript_openai_tool_guardrails` fixture and pinned OpenAI Agents JS
  `examples/docs/guardrails/toolGuardrails.ts` use `.includes("sk-")` before rejecting input/output
  content, while `examples/basic/tools.ts` rejects non-Tokyo weather requests through a literal
  `!== "tokyo"` predicate.
- Alternative: Treat all code near a `rejectContent` return as a guardrail predicate. Rejected
  because arbitrary boolean logic, nested branches, helper predicates, and mutation can overstate
  the exact condition enforced at the configured tool guardrail.
- Revisit when helper predicate calls or imported literal predicate constants can be resolved while
  preserving the exact configured tool and guardrail binding.

## OpenAI Agents JS tool guardrails govern exact same-file Agents through tool bindings

- Decision: Add Agent-to-`tool-guardrail-policy` governance edges only when a TypeScript OpenAI
  Agents SDK `Agent` uses a same-file tool binding that already emitted a proven
  `tool({ inputGuardrails, outputGuardrails })` control. Record `via_tool` and `via_tool_id` rather
  than pretending the guardrail was configured directly on the Agent.
- Evidence: The local `typescript_openai_tool_guardrails` fixture and pinned OpenAI Agents JS
  `examples/basic/tools.ts` / `examples/docs/guardrails/toolGuardrails.ts` all attach guarded tools
  to Agents through literal same-file `tools` arrays.
- Alternative: Infer Agent governance for imported tools, repeated tool bindings, or any object
  with `inputGuardrails`/`outputGuardrails`. Rejected because the current IR can only source-prove
  the tool guardrail control and Agent attachment in same-file, unambiguous bindings.
- Revisit when imported guarded tool controls can be resolved with stable target identity across
  files.

## OpenAI Agents JS Agent.clone is exact lineage with explicit list semantics

- Decision: Represent exact TypeScript OpenAI Agents SDK `Agent.clone({...})` calls as Agent
  components only when the clone source is a stable same-file Agent binding, an exact imported
  sibling export, or an exact named/star reexport that resolves to one OpenAI `Agent`, and the clone
  config is a direct object literal. Add a `derived-from` edge back to the original source Agent,
  record list properties explicitly supplied in the clone config, and mark omitted SDK list
  properties as `shared-from-source-agent`. Conflicting reexports remain unresolved.
- Evidence: The pinned OpenAI Agents JS `packages/agents-core/src/agent.ts` docs state that
  omitted list properties such as `tools`, `handoffs`, `mcpServers`, `inputGuardrails`, and
  `outputGuardrails` share the original Agent's arrays. The pinned docs example
  `examples/docs/agents/agentCloning.ts` clones `pirateAgent` into `robotAgent` with those lists
  omitted, and `examples/financial-research-agent/manager.ts` clones imported `writerAgent` into
  `reportWriterAgent` while overriding `tools`. Local regression labels now cover direct imports,
  named reexports, star reexports, an ambiguous/conflicting reexport negative, and a lookalike
  `.clone(...)` negative while preserving the original `ts:agents.ts#agent:writerAgent` source ID
  through barrels.
- Alternative: Treat any `.clone(...)` on an identifier as an Agent, or resolve arbitrary imported
  clone sources. Rejected because lookalike objects, dynamic config helpers, rebound source
  bindings, and broad cross-file source identity need stronger provenance before AgentVerify should
  claim lineage.
- Revisit when list mutation can be resolved with stable source IDs, mutation timing, and list
  semantics without broad property-flow interpretation.

## OpenAI Agents JS hostedMcpTool approval is hosted-MCP-specific inventory

- Decision: Record exact `hostedMcpTool({...})` approval state through `mcp_approval_*` attributes
  rather than overloading generic `needsApproval` fields. Support omitted defaults, literal
  `"never"`/`"always"`, direct selective object policies with shallow `toolNames` and `readOnly`
  hints, stable same-file const object policies, dynamic/mutated bindings, and configured
  `onApproval` callbacks.
- Evidence: The pinned OpenAI Agents JS `hostedMcpTool` implementation maps omitted or `"never"`
  `requireApproval` to provider `require_approval: "never"` and otherwise forwards
  `buildRequireApproval(...)` plus `on_approval`. Pinned examples cover simple/default hosted MCP,
  connector `"never"`, selective HITL policy, and a callback that can return an
  environment-backed approval.
- Alternative: Treat hosted MCP approval as generic `approval_policy` or report every hosted MCP
  callback as human approval. Rejected because the SDK option is named differently, approval may be
  handled by the agent loop, and callback quality remains distinct from the MCP tool requirement.
- Revisit when wildcard or package-level reexported policy object bindings can be resolved without
  broad object-flow interpretation. Direct imported sibling const-object policies and named local
  reexports are now covered when the import, reexport, and exported object identity are exact.

## OpenAI Agents Python HostedMCPTool approval is source-proven tool_config inventory

- Decision: Record exact Python `HostedMCPTool(tool_config={...})` approval state through
  `mcp_approval_*` attributes on tool and hosted MCP capability nodes. Support direct literal
  `"never"`/`"always"`, same-block and exact imported local literal string bindings, shallow
  `{always, never}` tool-list dict policies, imported, named-reexported, producer-star-reexported,
  and consumer-star-imported local literal whole `tool_config` dictionaries,
  dynamic/imported/reexported-mutated binding metadata, ordered local multi-star import semantics
  when the later visible source is exact, and configured `on_approval_request` callbacks.
- Evidence: The pinned OpenAI Agents Python `HostedMCPTool` stores a raw MCP `tool_config` and
  separates `on_approval_request` as the callback used when approval is requested. Pinned
  `examples/hosted_mcp/simple.py`, `on_approval.py`, and `human_in_the_loop.py`, plus Composio's
  OpenAI Agents hosted MCP example, cover explicit disablement, same-block and imported local
  literal always-required policies, callback-controlled handling, and manual run-loop handling.
- Alternative: Treat hosted MCP approval as generic `approval_policy` or infer SDK defaults when
  `require_approval` is omitted. Rejected because hosted MCP uses provider/API-specific
  configuration and the Python examples make approval policy explicit in `tool_config`.
- Revisit when package-level policy or `tool_config` exports, unresolved later external star imports,
  `Mcp(...)` factory objects in production examples, or callable `require_approval` policies can be
  resolved without broad Python dataflow.

## OpenAI Agents JS tool guardrails are source-tool governance controls

- Decision: Represent exact TypeScript OpenAI Agents SDK
  `tool({ inputGuardrails, outputGuardrails })` options as `tool-guardrail-policy` controls tied to
  the source tool. Support exact imported `tool` factories from `@openai/agents`, inline guardrail
  arrays, direct `defineToolInputGuardrail`/`defineToolOutputGuardrail` const bindings, literal
  guardrail names/counts, binding-only fallbacks for dynamic or mutated configurations, and exact
  allow/reject-content action metadata from `ToolGuardrailFunctionOutputFactory` or literal
  `{ behavior: { type } }` returns.
- Evidence: The local `typescript_openai_tool_guardrails` fixture covers bound input guardrails,
  bound plus inline output guardrails, dynamic guardrail arrays that stay binding-only, mutated
  guardrail definitions that do not expose stale names/actions, and a lookalike object that is
  ignored. The pinned OpenAI Agents JS `examples/basic/tools.ts` and
  `examples/docs/guardrails/toolGuardrails.ts` examples provide real inline and factory-defined
  input/output tool guardrails, including reject-content and allow behavior.
- Alternative: Fold tool guardrails into `agent-guardrail-policy`. Rejected because OpenAI Agents
  SDK tool guardrails govern tool-call inputs/outputs rather than agent input/output, and they
  attach to a source tool even before agent composition is resolved.
- Revisit when imported literal guardrail arrays, helper-created tool guardrails, richer tripwire
  metadata, or guarded-tool-to-agent composition edges can remain source-proven without broad
  object/property matching.

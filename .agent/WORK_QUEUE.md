# AgentVerify work queue

## P0

- Keep rule additions evidence-backed: real repository case, fixture or corpus label, regression
  test, documentation, and benchmark update.
- Preserve fail-closed behavior for policy, baseline, suppression, and schema inputs used in CI.

## P1

- Attach `agentverify benchmark verify` JSON outputs to release artifacts or release notes once
  release publishing is explicit.
- Expand selected real-world framework coverage where current docs record unresolved ambiguous
  wrapper factories, type-driven symbols, generic same-named provider wrappers, or additional
  non-provider wildcard/reexport forms beyond the current exact framework-constructor,
  provider-factory, and literal-callable cases.
- Extend Vercel AI WorkflowAgent modeling only when framework provenance is exact: connect
  object-tool dictionaries to WorkflowAgent instances and app-level approval/resumption flows without treating
  arbitrary `tools` containers or partial config objects as executable tools. Plain object tool
  inventory now covers top-level `execute` plus schema evidence and static `needsApproval: true as
  const`; exact local `@ai-sdk/workflow` `WorkflowAgent({ tools })` edges are covered for stable
  same-file tool-set bindings; unique stable same-file `execute: helper` bodies now map delegated
  code-execution/filesystem/network capability evidence back to the owning tool; direct
  `WorkflowAgent.model` AI SDK provider calls and stable same-file immutable provider-model consts
  now emit source-agent-linked model-setting controls;
  direct relative named imports, exact named reexports, and unambiguous star reexports of immutable
  exported tool-set objects now link to original sibling-module object-tool IDs with mutation
  guards. Direct relative named imports, exact named reexports, and unambiguous star reexports of
  stable exported `execute` helper functions now map concrete helper-body capabilities back to a
  unique importing object tool. Direct relative named imports, exact named reexports, and
  unambiguous star reexports of immutable exported provider-model consts now feed
  `WorkflowAgent.model`; trailing static TypeScript `as`/`satisfies` assertions are accepted for
  direct and bound provider-model calls, so future work should focus on richer runtime model wrapper
  shapes or additional type syntax only with comparable proof,
  app-level approval event/UI flows beyond the now-covered framework runtime approval pause,
  request-chunk, and revalidation continuation path, richer telemetry sink/retention proof beyond
  the now-covered constructor and same-file stream telemetry/callback-hook inventory, reportable
  Vercel approval findings only with matching real evidence, or richer execute-helper forms beyond
  direct `const alias = helper` bindings only when comparable canonical-helper ambiguity guards
  exist.
- Extend Vercel AI Code Mode only when runtime provenance stays exact: current IR covers the
  host-tool approval gate, interrupt payload kind, denial-before-execute behavior, and
  continuation approval-id validation, plus the public `codeModeTool()` /
  `experimental_toolCaller(...)` surface that routes model `js` into sandboxed TypeScript execution
  with late-bound host tools. Future work should connect concrete Code Mode applications or tool
  definitions to this runtime path only when tool-call identity and approval response provenance are
  source-proven.
- Continue OpenAI Agents JS sandbox and session-governance policy extraction from pinned examples
  where evidence remains exact, especially additional Manifest/sandbox policy fields, additional
  `MemorySession`/server-managed conversation implementation semantics, or agent/session
  composition edges beyond the now-covered `client.create(...)`, `defaultManifest`, top-level
  `session`, exact `conversationId`, exact `previousResponseId`, same-block `result.history`,
  same-call history feedback, direct same-file agent aliases, same-result
  `result.currentAgent ?? agent` feedback-route metadata, and same-file `result.state` resume
  bindings, plus separately modeled `withTrace(..., { groupId/traceId })` and stable
  `Runner({ groupId })` trace correlation plus stable `Runner({ tracingDisabled: true })` and
  delegated `asTool({ runConfig: { tracingDisabled: true } })` observability-disablement evidence,
  delegated `asTool({ runOptions: { maxTurns } })` turn-limit evidence, and delegated
  `asTool({ runConfig: { model } })` model-override evidence, plus delegated
  `asTool({ runConfig: { workflowName } })` trace-workflow evidence and stable
  `Runner({ workflowName })` per-run workflow evidence plus exact direct/stable Runner
  `run(..., { maxTurns })` per-run turn-limit evidence plus exact direct/stable Runner
  `run(..., { stream: true })` streaming runtime-mode evidence and exact Agent-level
  `modelSettings.toolChoice` evidence plus stable Runner-level `modelSettings.toolChoice` per-run
  evidence and exact Agent-level literal reasoning/verbosity/parallel-tool-calls model settings,
  plus exact RealtimeSession top-level `model` including model-only session options,
  `config.parallelToolCalls`,
  `config.reasoning.effort`, literal `config.outputModalities`, audio input/output format, and
  audio transcription model/delay/languages plus privacy-preserving transcription prompt/keyword
  session policy, plus exact literal
  `config.audio.input.turnDetection.type/eagerness/createResponse/interruptResponse` resolved from
  same-file agents, narrow exported sibling `RealtimeAgent` imports, or one exact typed
  `Partial<RealtimeSessionOptions>` spread, plus exact `tool_approval_requested` event
  approval/rejection decisions resolved from same-file or narrow exported sibling
  `RealtimeSession` bindings, plus exact `session.connect({ apiKey })` auth-source and transport
  context resolved from direct `RealtimeSession` bindings, plus exact Codex extension
  `codexTool(...)` inventory for stable same-file/imported/reexported bindings or inline literal
  tools with `defaultThreadOptions.approvalPolicy`, sandbox mode, network/web-search toggles,
  stream callback, top-level or default-thread working-directory values including shorthand
  bindings, and run-context thread reuse metadata, without broadening into ambiguous
  helper/config composition, arbitrary spread objects, or lookalike event emitters/connectors. Exact
  same-file, exact imported sibling, and exact named/star-reexported sibling `Agent.clone({...})`
  lineage/list-property sharing semantics are now covered; future clone work should focus on list
  mutation only if source identity and mutation timing remain exact.
- Continue OpenAI Agents JS HITL and safety-governance extraction where evidence remains exact:
  richer `needsApproval` predicate quality, automatic approval bypasses, and `computerTool`
  `onSafetyCheck` callbacks that distinguish explicit user/policy review from pass-through
  acknowledgement beyond the current exact auto-acknowledgement and computer backend lifecycle
  inventory. Hosted MCP `requireApproval`/`onApproval` inventory now covers direct literals, inline
  selective policies, stable same-file const object policies, exact imported local const object
  policies, exact named local reexported const object policies, unambiguous local star-reexported
  const object policies, and dynamic/mutated/ambiguous bindings; future TypeScript hosted MCP work
  should resolve package-level or external star-reexported policy object bindings only if object
  identity remains exact. Inline result-binding `onApproval` callbacks with same-file readline
  review metadata and opaque no-review callback negatives are now fixture/truthset-backed; future
  callback work should focus on richer predicate/action quality only when prompt source and
  call-site identity remain exact. Same-file helper-derived
  run-state resumes and helper-body prompt-review propagation are now covered for the narrow
  exact-agent-parameter pattern; future helper work should focus only on richer predicate/action
  quality or new exact helper/prompt shapes that preserve call-site and source-agent identity.
- Continue OpenAI Agents Python safety-governance extraction where evidence remains exact: hosted
  MCP callback review quality beyond the now-covered same-file direct approval-dict return
  predicates and same-function result-binding approval dictionaries, `ComputerTool.on_safety_check`
  quality beyond the now-covered exact `return True` auto-acknowledgement and exact `return False`
  non-acknowledgement boolean callbacks, unresolved later external star imports or package-level
  hosted/non-hosted MCP approval policy or `tool_config` exports, any
  reporting-grade remote MCP auth/URL exposure quality only when deployment context is source-proven,
  and production sticky-approval defaults that can be separated from prompt-selected
  `always_approve`/`always_reject` persistence, without resolving arbitrary boolean expressions or
  collapsing duplicate callback names across lexical scopes.

## P2

- Keep example policy trust roots synchronized with composed example policy source digests whenever
  example policies change; prefer regenerating them with `agentverify policy --export-trust-root`.
- Explore CycloneDX/SPDX adapters only when a mapping preserves links back to the native AgentVerify
  evidence graph.
- Improve editor and CI integration examples beyond the installed `agentverify contracts` bundle:
  add SARIF/editor examples, policy-aware diagnostic grouping, or sample extension fixtures when
  they can be validated locally.
- Profile and reduce the remaining full public IR truth-set runtime. Focused label filters,
  optional `--progress` timing, `--scan-label-paths`, and opt-in
  `--expand-local-imports` local import/export closure now make detector-specific iteration
  measurable and fast for many cross-file-focused labels, including `IR-TS-TOOL-GRAPH`. A full
  expanded selected-path profiling run passed 2,350/2,522 public IR labels; the remaining 172 misses
  cluster in detectors that rely on non-import-neighbor architecture sidecars or global summaries
  rather than simple source imports. Repository-wide release scans are still authoritative. Opt-in
  `--scan-cache-dir` now preserves repository-wide semantics across repeated local runs by
  revalidating source and AgentVerify package source digests before reusing cached IR. A previous
  warm-cache post-current-agent smoke showed 157/157 IR target hits in about 3 seconds for the
  then-current 2,583 IR labels.
  The first reporting pass after scanner changes had 106/118 cache hits plus 12 misses and took
  about 47 seconds; the second true warm reporting pass had 118/118 cache hits and took about
  2 seconds. Next performance work should focus on cold-cache invalidation cost after scanner
  changes or selected-path dependency gaps rather than warm-cache hit overhead.
- Explore exact interprocedural OpenAI Agents JS history-state continuation only if it can remain
  source-proven. The real `examples/docs/running-agents/chatLoop.ts` caller-owned concat feedback
  and `examples/agent-patterns/routing.ts` direct triage-agent alias plus same-result
  `agent = result.currentAgent ?? agent` feedback-route metadata are now covered; future work should
  focus on helper-crossing or richer route-update expressions only with same-result provenance.
- Explore richer OpenAI Agents JS tracing only if it can stay source-proven: trace processors,
  durable trace/export sinks, exported Runner factories, delegated `runConfig.groupId`, additional
  trace metadata policy, direct `run(..., { workflowName })` calls, or governance edges that can
  connect `trace-group`/`trace-id`/`tracing-disabled`/`trace-workflow` evidence to actual audit
  storage without treating observability IDs as memory/session continuity.
- Explore additional web-search governance only if it stays source-proven: package-level
  web-search option objects or OpenAI-compatible provider-defined web-search factories in real
  repositories. The exact OpenAI Agents JS
  `webSearchTool({ filters.allowedDomains, searchContextSize, userLocation })`, stable same-file,
  imported sibling, named-reexported, and unambiguous star-reexported `webSearchTool(options)`
  const-object bindings, and `Agent.modelSettings.providerData.include` literal shapes are now
  covered; ambiguous star barrels remain unresolved.
- Explore the remaining OpenAI Agents JS HITL approval-state gaps only if they can stay exact:
  compound callback predicate quality, automatic approval bypasses, and any more complex serialized
  state flows beyond same-file literal
  `writeFile`/`readFile` or direct `.toString()` chains. Direct `result.state`, bound-state,
  narrowly restored `RunState.fromString`, and non-exported async helper-parameter approval
  decisions plus helper-derived state resumes are now inventoried; generic tools, delegated-agent
  adapters, and approval-capable builtin tools now distinguish literal approval from
  callback-controlled `needsApproval`, and the first shallow literal predicate metadata is now
  recorded for prefix/contains/literal-set checks. Exact Realtime
  `tool_approval_requested` event approve/reject calls are now modeled when the event request's
  `approvalItem` is passed to a proven `RealtimeSession`. `computerTool({ onSafetyCheck })`
  pass-through callbacks now report as `AV-APPROVAL011`, and hosted MCP `onApproval` inline
  literal/result-binding return shapes plus same-file readline prompt-helper source shapes are now
  inventoried. Local builtin-tool `shellTool`/`applyPatchTool` `onApproval` callbacks now also record
  exact approval-object return shape, same-file readline prompt-helper source, and conditional
  fallback rejection when source-proven, but AgentVerify still does not claim full approval or safety
  quality without broader predicate/action evidence. Direct OpenAI run-state approval branches now
  also record same-file readline prompt-helper review source when source-proven; future work can
  propagate that through helper-parameter run-state summaries only if call-site provenance remains
  exact.
- Explore whether any Realtime auth-source patterns should become reporting rules only after
  gathering enough real non-example client-side/server-side context. Current auth evidence is IR
  inventory only because `process.env.OPENAI_API_KEY` with websocket/SIP can be legitimate server
  code or unsafe browser bundling depending on deployment context.
- Explore the next OpenAI Realtime guardrail slice only if it stays exact: helper-created
  guardrails, input guardrails, or richer predicate/action semantics beyond direct
  returned `tripwireTriggered` source classification. Current output guardrail inventory covers
  direct session options, typed `RealtimeOutputGuardrail[]` const arrays, typed
  `RealtimeSessionOptions` spreads, exact relative imported typed guardrail arrays including named
  reexports, literal names/counts, direct tripwire source counts, and `debounceTextLength`, with
  mutated arrays, ambiguous barrels, and dynamic settings bounded.
- Explore richer OpenAI Agents JS Agent guardrails only if evidence stays exact: helper-created
  guardrails, imported helper-created guardrail arrays, cross-file guardrail assignment helpers, or
  richer predicate/action semantics beyond direct returned `tripwireTriggered` source
  classification. Constructor `inputGuardrails`/`outputGuardrails`, stable same-file
  post-construction property assignments, direct literal-vs-computed tripwire metadata,
  first-statement direct-throw metadata, and exact relative imported typed guardrail arrays
  including named reexports are now inventoried; dynamic arrays, mutated bindings, ambiguous star
  barrels, and rebound agents should remain binding-only or unresolved.
- Explore richer OpenAI Agents JS tool guardrails only if evidence stays exact: helper-created tool
  guardrail arrays, imported factory-created guardrails, compound or imported helper predicate
  chains, or richer imported guarded-tool composition beyond exact Agent-to-tool IDs. Direct
  `tool({ inputGuardrails, outputGuardrails })`,
  `defineToolInputGuardrail`/`defineToolOutputGuardrail` bindings, exact relative imported typed
  guardrail arrays including named reexports, allow/reject-content actions, shallow literal reject
  predicates, same-file and exact imported helper predicate calls, stable helper-result bindings,
  exact same-file helper predicate chains, exact same-file Agent-to-tool-guardrail edges, and exact
  imported guarded-tool Agent bridge edges are now inventoried as a separate source-tool policy
  slice; ambiguous barrels stay binding-only.

## Deferred until access/authorization

- Create GitHub issues, publish releases, configure external trust roots, or perform adoption/outreach
  work in remote systems.

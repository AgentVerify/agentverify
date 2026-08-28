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
- Continue OpenAI Agents JS sandbox and session-governance policy extraction from pinned examples
  where evidence remains exact, especially additional Manifest/sandbox policy fields, additional
  `MemorySession`/server-managed conversation implementation semantics, or agent/session
  composition edges beyond the now-covered `client.create(...)`, `defaultManifest`, top-level
  `session`, exact `conversationId`, exact `previousResponseId`, same-block `result.history`,
  same-call history feedback, direct same-file agent aliases, and same-file `result.state` resume
  bindings, plus separately modeled `withTrace(..., { groupId/traceId })` and stable
  `Runner({ groupId })` trace correlation plus stable `Runner({ tracingDisabled: true })` and
  delegated `asTool({ runConfig: { tracingDisabled: true } })` observability-disablement evidence,
  delegated `asTool({ runOptions: { maxTurns } })` turn-limit evidence, and delegated
  `asTool({ runConfig: { model } })` model-override evidence, plus delegated
  `asTool({ runConfig: { workflowName } })` trace-workflow evidence and stable
  `Runner({ workflowName })` per-run workflow evidence, without broadening into ambiguous
  helper/config composition.
- Continue OpenAI Agents JS HITL and safety-governance extraction where evidence remains exact:
  richer `needsApproval` predicate quality, automatic approval bypasses, and `computerTool`
  `onSafetyCheck` callbacks that distinguish explicit user/policy review from pass-through
  acknowledgement. Same-file helper-derived run-state resumes are now covered for the narrow
  exact-agent-parameter pattern; future helper work should focus only on richer predicate/action
  quality or new exact helper shapes that preserve call-site and source-agent identity.
- Continue OpenAI Agents Python safety-governance extraction where evidence remains exact: callbacks
  that distinguish explicit user/policy review from unconditional acknowledgement, and production
  sticky-approval defaults that can be separated from prompt-selected `always_approve`/
  `always_reject` persistence, without resolving arbitrary boolean expressions or collapsing
  duplicate callback names across lexical scopes.

## P2

- Keep example policy trust roots synchronized with composed example policy source digests whenever
  example policies change; prefer regenerating them with `agentverify policy --export-trust-root`.
- Explore CycloneDX/SPDX adapters only when a mapping preserves links back to the native AgentVerify
  evidence graph.
- Improve editor and CI integration examples beyond the installed `agentverify contracts` bundle:
  add SARIF/editor examples, policy-aware diagnostic grouping, or sample extension fixtures when
  they can be validated locally.
- Improve installed CLI examples for benchmark verification and schema exports in CI/editor
  workflows; policy-gate GitHub Actions now has a checked workflow example.
- Profile and reduce the remaining full public IR truth-set runtime. Focused label filters,
  optional `--progress` timing, and explicit `--scan-label-paths` development scans now make
  detector-specific iteration measurable and fast for self-contained labels, but complete corpus
  regeneration still spends minutes in broad repository scans. A full selected-path experiment
  failed cross-file-dependent labels, so the next credible acceleration needs dependency-aware path
  expansion or scan-result reuse rather than label files only.
- Explore exact interprocedural OpenAI Agents JS history-state continuation only if it can remain
  source-proven. The real `examples/docs/running-agents/chatLoop.ts` caller-owned concat feedback
  and `examples/agent-patterns/routing.ts` direct triage-agent alias are now covered; dynamic
  routed-agent updates such as `agent = result.currentAgent ?? agent` remain unresolved.
- Explore richer OpenAI Agents JS tracing only if it can stay source-proven: trace processors,
  durable trace/export sinks, exported Runner factories, delegated `runConfig.groupId`, additional
  trace metadata policy, direct `run(..., { workflowName })` calls, or governance edges that can
  connect `trace-group`/`trace-id`/`tracing-disabled`/`trace-workflow` evidence to actual audit
  storage without treating observability IDs as memory/session continuity.
- Explore the remaining OpenAI Agents JS HITL approval-state gaps only if they can stay exact:
  compound callback predicate quality, automatic approval bypasses, and any more complex serialized
  state flows beyond same-file literal
  `writeFile`/`readFile` or direct `.toString()` chains. Direct `result.state`, bound-state,
  narrowly restored `RunState.fromString`, and non-exported async helper-parameter approval
  decisions plus helper-derived state resumes are now inventoried; generic tools, delegated-agent
  adapters, and approval-capable builtin tools now distinguish literal approval from
  callback-controlled `needsApproval`, and the first shallow literal predicate metadata is now
  recorded for prefix/contains/literal-set checks. `computerTool({ onSafetyCheck })` pass-through
  callbacks now report as `AV-APPROVAL011`, but AgentVerify still does not claim full approval or
  safety quality without broader predicate/action evidence.

## Deferred until access/authorization

- Create GitHub issues, publish releases, configure external trust roots, or perform adoption/outreach
  work in remote systems.

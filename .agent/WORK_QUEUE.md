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
  `session`, exact `conversationId`, exact `previousResponseId`, same-block `result.history`, and
  same-file `result.state` resume bindings, without broadening into ambiguous helper/config
  composition.

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
  source-proven. The real `examples/docs/running-agents/chatLoop.ts` pattern stores `result.history`
  in a caller-owned variable across repeated helper calls, but the current same-block scanner should
  not infer that without a narrowly validated function/call-state model.
- Explore OpenAI Agents JS HITL approval-state governance only if it can distinguish SDK-native
  approval callbacks, manual `state.approve`/`state.reject`, and automatic approval bypasses from
  generic same-named functions. The new `result.state` continuity inventory provides the resume
  backbone but does not yet claim approval quality.
- Extend exact OpenAI Agents JS approval inventory from `tool({ needsApproval })` to
  `agent.asTool({ needsApproval })` only if the IR can represent the delegated tool distinctly from
  the source agent and keep callback-controlled coverage separate from literal always-approval.

## Deferred until access/authorization

- Create GitHub issues, publish releases, configure external trust roots, or perform adoption/outreach
  work in remote systems.

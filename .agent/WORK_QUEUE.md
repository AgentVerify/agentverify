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
- Continue OpenAI Agents JS sandbox policy extraction from pinned examples where evidence remains
  exact, especially additional Manifest/sandbox policy fields or agent/session composition edges
  beyond the now-covered `client.create(...)` and `defaultManifest` bindings, without broadening into
  ambiguous helper/config composition.

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

## Deferred until access/authorization

- Create GitHub issues, publish releases, configure external trust roots, or perform adoption/outreach
  work in remote systems.

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

## P2

- Add a signed-policy CI fixture or generated example only if it can avoid committing durable
  private-key material and avoid implying the checked-in key is an organizational trust anchor.
- Keep example policy trust roots synchronized with composed example policy source digests whenever
  example policies change; prefer regenerating them with `agentverify policy --export-trust-root`.
- Explore CycloneDX/SPDX adapters only when a mapping preserves links back to the native AgentVerify
  evidence graph.
- Improve editor and CI integration examples using discoverable schema-backed report, benchmark,
  policy, and rule-catalog contracts.
- Improve installed CLI examples for benchmark verification, schema exports, and policy gates in
  CI/editor workflows.

## Deferred until access/authorization

- Create GitHub issues, publish releases, configure external trust roots, or perform adoption/outreach
  work in remote systems.

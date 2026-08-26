# AgentVerify work queue

## P0

- Keep rule additions evidence-backed: real repository case, fixture or corpus label, regression
  test, documentation, and benchmark update.
- Preserve fail-closed behavior for policy, baseline, suppression, and schema inputs used in CI.

## P1

- Extend release-artifact checks to attach benchmark verifier logs once release publishing is
  explicit.
- Expand selected real-world framework coverage where current docs record unresolved ambiguous
  wrapper factories, type-driven symbols, generic same-named provider wrappers, or additional
  non-provider wildcard import forms beyond the current literal-visibility cases.

## P2

- Design cryptographic signed policy provenance with explicit local trust-root configuration,
  building on `agentverify policy` provenance summaries and digest allowlists. Do not present content
  hashes as author authenticity.
- Keep example policy trust roots synchronized with composed example policy source digests whenever
  example policies change; prefer regenerating them with `agentverify policy --export-trust-root`.
- Explore CycloneDX/SPDX adapters only when a mapping preserves links back to the native AgentVerify
  evidence graph.
- Improve editor and CI integration examples using discoverable schema-backed report, benchmark,
  policy, and rule-catalog contracts.
- Consider release-artifact checks that attach benchmark verification outputs to wheels or release
  notes once the release process is explicit.

## Deferred until access/authorization

- Create GitHub issues, publish releases, configure external trust roots, or perform adoption/outreach
  work in remote systems.

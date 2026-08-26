# AgentVerify work queue

## P0

- Keep rule additions evidence-backed: real repository case, fixture or corpus label, regression
  test, documentation, and benchmark update.
- Preserve fail-closed behavior for policy, baseline, suppression, and schema inputs used in CI.

## P1

- Extend package/distribution checks to cover source examples or documented sample bundles when the
  packaging strategy is explicit.
- Expand selected real-world framework coverage where current docs record unresolved package
  reexports, wildcard imports, wrapper factories, or type-driven symbols.

## P2

- Design cryptographic signed policy provenance with explicit local trust-root configuration,
  building on `agentverify policy` provenance summaries and digest allowlists. Do not present content
  hashes as author authenticity.
- Explore CycloneDX/SPDX adapters only when a mapping preserves links back to the native AgentVerify
  evidence graph.
- Improve editor and CI integration examples using schema-backed report, policy, and rule-catalog
  contracts.
- Consider release-artifact checks that attach benchmark verification outputs to wheels or release
  notes once the release process is explicit.

## Deferred until access/authorization

- Create GitHub issues, publish releases, configure external trust roots, or perform adoption/outreach
  work in remote systems.

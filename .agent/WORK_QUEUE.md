# AgentVerify work queue

## P0

- Keep rule additions evidence-backed: real repository case, fixture or corpus label, regression
  test, documentation, and benchmark update.
- Preserve fail-closed behavior for policy, baseline, suppression, and schema inputs used in CI.

## P1

- Design the sealed holdout benchmark process separately from the public regression corpus.
- Add package/distribution checks that verify bundled schemas and examples are present in installed
  artifacts.
- Expand selected real-world framework coverage where current docs record unresolved package
  reexports, wildcard imports, wrapper factories, or type-driven symbols.

## P2

- Design signed policy provenance with explicit local trust-root configuration. Do not present
  content hashes as author authenticity.
- Explore CycloneDX/SPDX adapters only when a mapping preserves links back to the native AgentVerify
  evidence graph.
- Improve editor and CI integration examples using schema-backed report, policy, and rule-catalog
  contracts.

## Deferred until access/authorization

- Create GitHub issues, publish releases, configure external trust roots, or perform adoption/outreach
  work in remote systems.

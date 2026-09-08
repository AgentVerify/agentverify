# Changelog

## v0.1.0 — 2026-09-08

AgentVerify v0.1.0 is the first public GitHub release. This is an early static analyzer; syntax
coverage and runtime control proof remain limited to documented patterns.

### Included

- Python package with the `agentverify` console script.
- Static analysis for Python and TypeScript/JavaScript AI-agent repositories.
- Agent IR extraction for agents, tools, MCP servers, capabilities, model/provider settings,
  approval controls, audit/observability controls, sandbox settings, policy settings, and selected
  framework-specific runtime evidence.
- 25 enabled reporting rules for high-confidence agent security and governance review findings.
- Deterministic JSON, summary, AI BOM, and SARIF scan formats.
- Inline suppressions, baseline filtering, fail-on gates, schema export, policy validation, local
  policy trust roots, detached policy-signature verification, benchmark verification, holdout setup
  validation, and editor-contract export/verification.
- GitHub Actions examples for benchmark verification, SARIF/code scanning, policy gates, and
  editor-contract artifact export.
- Research and benchmark evidence from a pinned 71-repository corpus.

### Current checked evidence

- Reporting-rule public regression truth set: 733/733 labels pass.
- Agent IR public regression truth set: 2,621/2,621 labels pass.
- Combined benchmark verification: 3,354/3,354 labels pass with digests OK.
- Full-corpus engine snapshot covers 71 successful repositories.

These are curated public-regression results, not an unbiased ecosystem-wide precision/recall claim.

### First-run experience

- GitHub installation instructions, a short README, and a task-oriented documentation index.
- A runnable unsafe/fixed comparison that verifies findings and CI gate behavior.
- Copyable integrations pinned to the official GitHub release.
- Scan-feedback and detection-report forms, a contribution workflow, and private security reporting.
- CI builds wheel/source artifacts and verifies installation, schemas, and command contracts.

### Distribution

The release provides a wheel, source distribution, benchmark verification JSON, and SHA-256
checksums through GitHub Releases. PyPI publication is not part of this release.

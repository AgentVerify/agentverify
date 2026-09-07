# Changelog

## v0.1.0 release candidate

AgentVerify v0.1.0 is the first runnable release candidate for GitHub distribution.

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

### Publish boundary

This candidate is prepared for manual GitHub release publication. It does not publish to GitHub,
create a tag, upload artifacts, or publish to PyPI by itself.

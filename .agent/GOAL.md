# AgentVerify mission

AgentVerify is an evidence-driven open-source static analyzer for AI agent applications: a
Semgrep/CodeQL-style tool that discovers agent architecture, capabilities, trust boundaries,
governance controls, and risky execution paths before deployment.

## Why this matters

AI applications are moving from simple model calls into autonomous agents with local tools, MCP
servers, browser and filesystem access, code execution, approval flows, and durable external
actions. Developers need a practical way to see what an agent can do and where control evidence is
missing.

## Success signals

- The research corpus remains pinned, reproducible, and representative of real Python and
  TypeScript agent repositories.
- Every reporting rule is backed by real cases, regression labels, documentation, and a stable
  machine-readable reporting contract.
- The CLI is usable in local development, pre-commit, CI, SARIF/code-scanning, and policy-gate
  workflows.
- Findings preserve evidence and uncertainty instead of hiding unresolved controls or overclaiming
  compliance.

## Scope

- Static repository analysis for Python and TypeScript/JavaScript agent applications.
- Framework/provider/tool/MCP/sandbox/governance inventory.
- High-confidence security and governance review rules with deterministic reports.
- Baseline, suppression, policy, schema, and integration workflows that support real adoption.

## Non-goals for now

- Acting as a runtime sandbox or live agent monitor.
- Claiming legal compliance or author authenticity without explicit trust-root support.
- Publishing releases, opening issues, or communicating externally without user authorization.

## Escalation conditions

Ask the user before actions requiring external credentials, publishing, destructive data changes,
financial cost, legal agreements, or a strategic scope change. When trust or remote access is not
available, continue with local engineering, corpus validation, documentation, and reproducible
benchmarks.

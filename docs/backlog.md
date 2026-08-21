# Issue-ready backlog

Items are ordered by evidence-backed roadmap priority. They are written to become GitHub issues once
the local repository has an approved remote.

## P0 — module-qualified symbols and graph identities

Replace name-only agent/tool references with module-qualified symbols for Python and a TypeScript AST
frontend. Preserve current location-gated resolution as the conservative fallback. Validate collisions
with two same-named tools in different modules and real monorepositories.

## P0 — configuration and policy resolution

Resolve environment defaults, config objects, CLI flags, MCP allowlists, tool policies, and approval
overrides into control edges. Suppress `AV-MCP002` and `AV-FS001` only when the resolved policy governs
the exact reachable path. Keep unresolved distinct from absent.

## P0 — approval coverage rule

Promote `AV-APPROVAL002` only when a destructive agent path is fully resolved and no approval edge
governs it. Add real positive, approved negative, auto-approved bypass, and delegated-agent cases.

## P1 — sandbox containment quality

Extend `AV-SANDBOX001` from compose syntax to Docker SDK calls, Kubernetes hostPath/privileged specs,
network policy, Linux capabilities, host PID/IPC, device passthrough, and credential mounts. Model the
sandbox as a control attached to the exact code/shell capability.

## P1 — consequential-action audit coverage

Recognize framework tracing, OpenTelemetry spans, durable audit sinks, and tool middleware. Implement
`AV-AUDIT001` only after action-level control edges can distinguish logging imports from durable,
attributable records.

## P1 — benchmark truth set

Hand-label at least 100 positive/negative locations across the pinned corpus. Publish per-rule
precision, recall, unsupported syntax, and framework coverage. Keep discovery sampling metrics
separate from detection-quality metrics.

## P2 — CI adoption workflow

Add GitHub code-scanning upload documentation, SARIF category support, changed-files mode, baseline
diff summaries, inline suppressions with reasons/expiry, and an official pre-commit hook.


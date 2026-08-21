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

Kubernetes privileged mode, host network/PID/IPC, service-account token mounts, explicit privilege
escalation, arbitrary `hostPath` mounts, and literal privileged Docker SDK calls are covered alongside
Compose. Next resolve network policy, Linux capabilities, device passthrough, and credential-volume
semantics. Model containment as a control attached to the exact code/shell capability.

## P1 — consequential-action audit coverage

Lexically scoped OpenTelemetry spans now create action-level control edges, without treating imports
or sibling spans as coverage. Next recognize framework tracing and tool middleware, then resolve span
processors/exporters to durable audit sinks. Implement `AV-AUDIT001` only when durable, attributable
records can be distinguished from instrumentation alone.

## P1 — benchmark truth set

The curated regression set has reached 100 pinned positive/negative locations. Next, create a
separately sampled and externally reviewed holdout set, publish framework-stratified coverage and
unsupported syntax, and keep holdout labels sealed until rule changes are complete. Keep discovery
sampling metrics separate from detection-quality metrics.

## P2 — CI adoption workflow

The repository now includes a GitHub code-scanning workflow and copy-ready SARIF upload guidance
with a stable category. Next add changed-files mode, baseline diff summaries, suppression expiry
enforcement, and an official pre-commit hook. Rule-scoped inline suppressions with required reasons
are supported.

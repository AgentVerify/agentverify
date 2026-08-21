# Issue-ready backlog

Items are ordered by evidence-backed roadmap priority. They are written to become GitHub issues once
the local repository has an approved remote.

## P0 — module-qualified symbols and graph identities

Absolute and relative Python imports now attach exact target paths, while name collisions remain
location-gated. Next replace display-name agent/tool identities with module-qualified symbols and a
TypeScript AST frontend, then resolve package re-exports. Preserve unresolved state for ambiguity and
validate on larger real monorepository graphs.

## P0 — configuration and policy resolution

Resolve environment defaults, config objects, CLI flags, MCP allowlists, tool policies, and approval
overrides into control edges. Suppress `AV-MCP002` and `AV-FS001` only when the resolved policy governs
the exact reachable path. Same-function MCP rejection guards are statement-ordered, so later checks
cannot govern earlier calls. Next resolve branch-local guards and imported policy objects. Keep
unresolved distinct from absent.

## P0 — approval coverage rule

Promote `AV-APPROVAL002` only when a destructive agent path is fully resolved and no approval edge
governs it. Literal OpenAI Agents JavaScript function-tool and Python built-in-tool approval policies
now form exact controls; callbacks and automatic handlers remain unresolved. Add real
destructive-path positives, approved negatives, auto-approved bypasses, and delegated-agent cases
before enabling the rule.

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

The curated regression set has reached 121 pinned positive/negative locations, with 12 separately
scored IR relationship labels. Schema-v2 engine results and `docs/frontend-coverage.md` publish
category-stratified observations and unsupported syntax. Next create a separately sampled, externally
reviewed holdout set and keep its labels sealed until rule changes are complete. Keep discovery
sampling metrics separate from detection-quality metrics.

## P2 — CI adoption workflow

The repository now includes a GitHub code-scanning workflow and copy-ready SARIF upload guidance
with a stable category, an auditable `--paths-from` mode for changed-file scans, and baseline diff
counts that avoid false resolution claims on partial scans. Inline suppressions now retain optional
expiry status, and CI can require an active ISO date. A distributable pre-commit manifest and local
setup are included; publishing its remote form waits for an approved repository URL and release tag.
Next add richer policy-as-code configuration.

## P2 — AI BOM standards adapters

The native schema-backed AI BOM now preserves assets, relationships, evidence, governance summaries,
risks, and ambiguous identities without information loss. Next design separately validated CycloneDX
and SPDX AI-profile adapters. Map only concepts supported by the target specification and retain a
link to the native evidence graph rather than presenting agent-specific extensions as standard fields.

# Issue-ready backlog

Items are ordered by evidence-backed roadmap priority. They are written to become GitHub issues once
the local repository has an approved remote.

## P0 — module-qualified symbols and graph identities

Python and TypeScript agent/tool components now carry module-qualified IDs, including Python class
methods, built-in tools, tool namespaces, and Cline/OpenAI inline factories. The structure-aware
TypeScript tools-array reader resolves all 81 observed agent-to-tool edges and 14 agent-as-tool
delegations in the pinned sample without treating nested tokens as tools. Repeated constructor and
decorated-tool bindings now receive occurrence-qualified IDs for exact source edges; repeated target
references resolve only for a single direct, earlier definition in the same Python lexical/module
scope. Next add branch- and reassignment-sensitive dataflow, then resolve Python/TS package re-exports,
wildcard imports, unrecognized wrapper factories, and type-driven symbols.
Preserve unresolved state for ambiguity and validate on larger real monorepository graphs.

## P0 — configuration and policy resolution

Resolve environment defaults, config objects, CLI flags, MCP allowlists, tool policies, and approval
overrides into control edges. Suppress `AV-MCP002` and `AV-FS001` only when the resolved policy governs
the exact reachable path. Same-function MCP rejection guards and uncaught internal tool-registry
lookups are statement-ordered, so later checks cannot govern earlier calls. A bounded imported
TypeScript path guard now suppresses `AV-FS001` only when a normalized, separator-aware roots
predicate rejects before the write and its roots are a statically narrow literal set. MCP Servers'
dynamic CLI/MCP roots retain a review plus an explicit unresolved-scope control edge. Python now
resolves statement-ordered `Path.resolve()` plus `is_relative_to()` boundaries, including positive
branch-local and fail-closed guards. Literal narrow roots may suppress; configured roots retain the
review, and prefix checks or reassignment remain unresolved. Next resolve imported policy objects,
`relative_to()` exception guards, and bounded root constants without widening name-based inference.
Python filesystem inventory now models canonical and import-aliased `os`/`shutil` create, copy,
move, replace, and delete calls, using the destination rather than the source for two-path APIs.
Next resolve immutable local callable aliases (such as conditional `copy`/`copy2` bindings),
proven-`Path` rename/replace methods, and imported filesystem wrappers without matching arbitrary
same-named methods.
Constructor-only MCP wrapper fields, pure accessors, and unchanged parameters captured by
returned/registered callbacks now produce fixed-binding edges. Mutable fields, rebound parameters,
and same-operation retry closures remain unresolved. Same-class methods and immutable
constructor-bound imported registry managers now summarize exact `get_tool`-then-reject paths. The
collector retains a bounded dependency closure so the imported proof is reproducible. Next resolve
aliased/module-qualified constructors and deeper manager composition, without treating class names
or discovery as authorization.
Keep unresolved distinct from absent.

## P0 — approval coverage rule

`AV-APPROVAL002` now reports the narrow provable subset where an Agent directly reaches a local
OpenAI Agents Python or TypeScript shell tool and its SDK approval is explicitly or default-disabled.
It remains a review: an executor may enforce an equivalent internal control. Promote absence to a
finding only when the complete destructive path and executor policy are resolved. Extend coverage to
delegated agents and other frameworks without treating callbacks or automatic handlers as absent
controls.

## P1 — sandbox containment quality

Kubernetes privileged mode, host network/PID/IPC, service-account token mounts, explicit privilege
escalation, arbitrary `hostPath` mounts, and literal privileged Docker SDK calls are covered alongside
Compose. Next resolve network policy, Linux capabilities, device passthrough, and credential-volume
semantics. Model containment as a control attached to the exact code/shell capability.

## P1 — network destination policy

`AV-NET001` now reports Python and structurally resolved TypeScript tool parameters and their direct
aliases when they determine the HTTP origin. Literal URLs and formatted URLs with a fixed scheme and
host remain inventory-only. TypeScript coverage includes Mastra `createTool` object properties and
MCP `registerTool` callbacks with exact tool identities. Unique same-file free/static network helpers
now propagate positional/destructured parameter flow to exact tool edges. Next
resolve URL parsing/normalization guards, hostname allowlists, DNS rebinding defenses, proxy policy,
and egress controls before treating a review as a demonstrated SSRF path. Add imported, arrow-assigned,
and transitive helper summaries, deeper alias propagation, and equivalent Axios request-object handling.

## P1 — consequential-action audit coverage

Lexically scoped OpenTelemetry spans now create action-level control edges, without treating imports
or sibling spans as coverage. Next recognize framework tracing and tool middleware, then resolve span
processors/exporters to durable audit sinks. Implement `AV-AUDIT001` only when durable, attributable
records can be distinguished from instrumentation alone.

## P1 — benchmark truth set

The curated regression set has reached 196 pinned positive/negative locations, with 70 separately
scored IR relationship labels. Schema-v16 engine results and `docs/frontend-coverage.md` publish
category-stratified observations and unsupported syntax. Next create a separately sampled, externally
reviewed holdout set and keep its labels sealed until rule changes are complete. Keep discovery
sampling metrics separate from detection-quality metrics.

## P2 — CI adoption workflow

The repository now includes a GitHub code-scanning workflow and copy-ready SARIF upload guidance
with a stable category, an auditable `--paths-from` mode for changed-file scans, and baseline diff
counts that avoid false resolution claims on partial scans. Inline suppressions now retain optional
expiry status, and CI can require an active ISO date. A distributable pre-commit manifest and local
setup are included; publishing its remote form waits for an approved repository URL and release tag.
Schema-backed JSON policies now provide per-rule/result-kind/severity count budgets with decision
evidence in every report. Next add organization policy composition and signed policy provenance
without weakening strict unknown-field validation.

## P2 — AI BOM standards adapters

The native schema-backed AI BOM 1.1 now preserves assets, relationships, evidence, governance
summaries, risks, and ambiguous identities without information loss. Exact relationship evidence
resolves capability/control endpoints while genuinely ambiguous agent/tool references remain explicit.
Next design separately validated CycloneDX
and SPDX AI-profile adapters. Map only concepts supported by the target specification and retain a
link to the native evidence graph rather than presenting agent-specific extensions as standard fields.

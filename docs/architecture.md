# Architecture

```text
Repository
  ├─ Python AST frontend
  ├─ TypeScript/JavaScript frontend
  └─ MCP configuration frontend
           │
           ▼
Agent IR: components + source evidence + relationships
           │
           ▼
Context analysis: reachability + governing controls + unresolved state
           │
           ▼
Rule engine: inventory, review candidates, and findings
           │
           ▼
Deterministic text / JSON / native AI BOM / SARIF reports
```

## Agent IR

Components represent frameworks, providers, agents, tools, MCP servers, capabilities, controls, and
control settings. Relationships currently represent `uses`, `delegates-to`, `contains-control`, and
`governed-by` edges. Every object carries source path, line, and excerpt evidence.

Names are intentionally not treated as globally unique. Python and TypeScript agent/tool definitions
carry stable frontend-and-module-qualified `symbol_id` values; relationships carry `source_id` and
`target_id` when resolution succeeds. Context analysis prefers those IDs and falls back to the older
location-gated display-name logic only for unresolved syntax. Capability-to-tool resolution still
requires the relationship and capability observation to share a source location, preventing
same-named definitions in separate modules from leaking reachability or control coverage.
Unambiguous absolute Python
`from local_module import tool` references and filesystem-resolved relative imports point to an exact
repository file and can safely form cross-file agent paths. TypeScript named imports resolve when a
relative module maps to exactly one in-repository `.ts`, `.tsx`, `.js`, or `.jsx` file; aliases retain
the original exported name. Imports that escape the scan root, target missing files, or have multiple
candidate files remain unresolved. Python class methods use class-qualified IDs, and assigned agent
or built-in-tool instances use their binding name. Package re-exports, wildcard imports, dynamic
lookups, and several wrapper-factory forms remain unresolved.

## Result kinds and uncertainty

- `inventory`: observed architecture facts without a risk judgment.
- `review`: a risky configuration candidate that needs surrounding context.
- `finding`: a locally demonstrated dangerous primitive or resolved unsafe flow.

Control analysis reports `present` only for a resolved governing edge. It reports `unresolved` when
coverage cannot be proven and never silently converts missing lexical evidence into “control absent.”
The first policy resolver recognizes same-function MCP tool-name allowlists that reject unknown tools
before forwarding. It also resolves an OpenAI Agents TypeScript function tool's literal
`needsApproval: true` setting. For Python files importing the OpenAI Agents SDK, literal
`needs_approval=True` on `ShellTool`, `ApplyPatchTool`, and `CustomTool` creates an instance-scoped
tool-to-control edge when no automatic approval handler is configured; literal false is recorded as
explicitly disabled. An omitted value records the SDK's documented disabled default. Callback,
handler-controlled, and other non-literal approval policies remain unresolved.

For audit modeling, a tool capability lexically inside an OpenTelemetry
`start_as_current_span(...)` block receives an exact capability-to-`action-trace` control edge. A
span elsewhere in the same tool does not cover the action. The edge records exporter durability as
unresolved: instrumentation is not proof that an attributable record reaches durable storage.

## Safety boundary

AgentVerify reads source and configuration as data. It never imports project modules, evaluates their
code, installs their dependencies, or launches configured MCP servers. Repository traversal excludes
and prunes dependency, build, VCS, cache, and virtual-environment directories. Selected-path scans
reject absolute and parent-traversal paths; their reports are explicitly marked partial.

Configuration discovery includes Compose, devcontainers, and Kubernetes/Helm paths. Exact dangerous
boolean settings are reported as review results; templates and values are not rendered or executed,
and AgentVerify does not infer that a chart value governs a workload unless that relationship is
explicitly resolved.

The native AI BOM serializes the same evidence graph with stable observation IDs. Relationship
endpoints expose unique-display-name, ambiguous, or unresolved identity instead of collapsing
same-named assets. It is a lossless AgentVerify format, not a claim of CycloneDX or SPDX conformance.

Policy evaluation is a post-baseline reporting stage, not a rule filter. Gates count matching
fingerprints by rule, result kind, and minimum severity; findings remain in every output. JSON, text,
AI BOM, and SARIF retain the policy file digest and per-gate decision evidence.

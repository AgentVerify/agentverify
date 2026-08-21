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
Deterministic text / JSON / SARIF reports
```

## Agent IR

Components represent frameworks, providers, agents, tools, MCP servers, capabilities, controls, and
control settings. Relationships currently represent `uses`, `delegates-to`, `contains-control`, and
`governed-by` edges. Every object carries source path, line, and excerpt evidence.

Names are intentionally not treated as globally unique. Capability-to-tool resolution requires the
relationship and capability observation to share a source location; name-only cross-file inference
would overstate certainty. Agent-to-tool and tool-to-control context is likewise restricted to the
capability's source file, preventing same-named definitions in separate modules from leaking
reachability or control coverage. Unambiguous absolute Python
`from local_module import tool` references and filesystem-resolved relative imports point to an exact
repository file and can safely form cross-file agent paths. TypeScript named imports resolve when a
relative module maps to exactly one in-repository `.ts`, `.tsx`, `.js`, or `.jsx` file; aliases retain
the original exported name. Imports that escape the scan root, target missing files, or have multiple
candidate files remain unresolved. Future symbol tables will replace display-name identities with
module-qualified symbols and resolve package re-exports.

## Result kinds and uncertainty

- `inventory`: observed architecture facts without a risk judgment.
- `review`: a risky configuration candidate that needs surrounding context.
- `finding`: a locally demonstrated dangerous primitive or resolved unsafe flow.

Control analysis reports `present` only for a resolved governing edge. It reports `unresolved` when
coverage cannot be proven and never silently converts missing lexical evidence into “control absent.”
The first policy resolver recognizes same-function MCP tool-name allowlists that reject unknown tools
before forwarding. It also resolves an OpenAI Agents TypeScript function tool's literal
`needsApproval: true` setting; callback and non-literal approval policies remain unresolved.

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

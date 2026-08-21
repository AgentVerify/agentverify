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
control settings. Relationships currently represent `uses`, `delegates-to`, and `governed-by` edges.
Every object carries source path, line, and excerpt evidence.

Names are intentionally not treated as globally unique. Capability-to-tool resolution requires the
relationship and capability observation to share a source location; name-only cross-file inference
would overstate certainty. Agent-to-tool and tool-to-control context is likewise restricted to the
capability's source file, preventing same-named definitions in separate modules from leaking
reachability or control coverage. Future symbol tables will add module-qualified identities and
resolve explicit imports across files.

## Result kinds and uncertainty

- `inventory`: observed architecture facts without a risk judgment.
- `review`: a risky configuration candidate that needs surrounding context.
- `finding`: a locally demonstrated dangerous primitive or resolved unsafe flow.

Control analysis reports `present` only for a resolved governing edge. It reports `unresolved` when
coverage cannot be proven and never silently converts missing lexical evidence into “control absent.”
The first policy resolver recognizes same-function MCP tool-name allowlists that reject unknown tools
before forwarding. It also resolves an OpenAI Agents TypeScript function tool's literal
`needsApproval: true` setting; callback and non-literal approval policies remain unresolved.

## Safety boundary

AgentVerify reads source and configuration as data. It never imports project modules, evaluates their
code, installs their dependencies, or launches configured MCP servers. Repository traversal excludes
dependency, build, VCS, cache, and virtual-environment directories.

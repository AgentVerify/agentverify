# Evidence-backed roadmap

Priorities use `impact × corpus frequency × technical feasibility`, each scored from 1–5. Frequency
is based on the initial 71-repository corpus; scores will be recalibrated as the benchmark grows.

| Priority | Capability | Impact | Frequency | Feasibility | Score | Evidence |
|---:|---|---:|---:|---:|---:|---|
| 1 | Agent bill of materials: models, providers, frameworks, tools, MCP | 4 | 5 | 5 | 100 | 44 multi-provider repos; 50 with MCP; 69 with privileged capabilities |
| 2 | Dangerous shell and code execution | 5 | 4 | 4 | 80 | 42 shell-capable repos; 8 `shell=True` candidates |
| 3 | MCP server/tool trust-boundary analysis | 5 | 4 | 4 | 80 | 50 MCP repos; 17 generic forwarding shapes |
| 4 | Approval coverage and bypass paths | 5 | 4 | 3 | 60 | 52 approval-positive; 18 auto-approval candidates |
| 5 | Filesystem scope and destructive writes | 5 | 4 | 3 | 60 | 59 writable-filesystem repos |
| 6 | Sandbox boundary quality | 5 | 4 | 3 | 60 | 64 sandbox-positive; mounts/network/credentials determine quality |
| 7 | Parameter-controlled network origins | 5 | 2 | 4 | 40 | Direct, same-file, imported-function, registered-class, and import-proven urllib tool origins across Python and TypeScript; fixed-host templates and Request objects are common negatives |
| 8 | Consequential-action audit coverage | 4 | 4 | 2 | 32 | 57 tracing-positive, but action-level coverage needs data flow |

## Milestone 1 — explainable discovery

- Parse Python and TypeScript without executing project code.
- Emit Agent IR nodes for models, agents, tools, MCP servers, capabilities, controls, and evidence.
- Produce deterministic text and JSON reports.
- Support OpenAI, Anthropic, and Azure OpenAI providers; LangChain/LangGraph, CrewAI, AutoGen,
  OpenAI Agents SDK, and common MCP configuration shapes.

## Milestone 2 — high-confidence local rules

- Detect shell invocation and distinguish constant argv from dynamic shell strings.
- Detect direct code evaluation and interpreter tools.
- Detect auto-approval/skip-confirmation configuration.
- Detect broad filesystem roots, host mounts, Docker socket exposure, and unscoped file tools.
- Detect MCP tool pass-throughs and enumerate statically registered server capabilities.
- Detect tool parameters used as HTTP origins while preserving fixed-host URL templates and urllib
  `Request` objects as negatives.

## Milestone 3 — graph and control analysis

- Link agents to directly and transitively reachable tools.
- Link privileged actions to approval, sandbox, allowlist, authentication, and audit controls.
- Resolve configuration defaults and environment overrides.
- Report “unresolved” separately from “control absent” to avoid false certainty.

## Milestone 4 — benchmarks and ecosystem UX

- Maintain one real pinned case, minimal regression fixture, and documented remediation per rule.
- Publish precision/recall results and scan-performance budgets.
- Maintain SARIF, baseline/suppression workflows, CI examples, and the schema-backed native AI BOM;
  maintain schema-backed non-hiding policy gates, and add standards adapters only after their Agent
  IR mappings are validated.

## Not prioritized yet

Compliance-framework labels are presentation mappings, not the initial product core. They will be
added only after the underlying technical evidence (provider, capability, authority, approval,
logging, and data flow) is reliable.

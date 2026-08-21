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
| 7 | Parameter-controlled network origins | 5 | 2 | 4 | 40 | 17 reviews across 10 repositories; zero exact Python allowlists, one configured-open TypeScript policy, two fully pinned CrewAI paths, two proxy-conditional Composio paths, ten configurable Langflow paths, one default-off n8n composition, two Flowise paths with distinct proxy behavior, and one Google ADK preflight-only global-fetch path |
| 8 | A2A AgentCard endpoint provenance | 5 | 2 | 4 | 40 | Two pinned TypeScript clients accept remote-card-selected RPC origins; ADK Python supplies two guarded comparison paths |
| 9 | Consequential-action audit coverage | 4 | 4 | 2 | 32 | 57 tracing-positive, but action-level coverage needs data flow |

## Milestone 1 — explainable discovery

- Parse Python and TypeScript without executing project code.
- Emit Agent IR nodes for models, agents, tools, MCP servers, capabilities, controls, and evidence.
- Produce deterministic text and JSON reports.
- Support OpenAI, Anthropic, and Azure OpenAI providers; LangChain/LangGraph, CrewAI, AutoGen,
  OpenAI Agents SDK, and common MCP configuration shapes.

## Milestone 2 — high-confidence local rules

- Detect shell invocation and distinguish constant argv from dynamic shell strings.
- Detect direct code evaluation and interpreter tools.
- Require a provenance-backed browser receiver before promoting dynamic `.evaluate(...)` input;
  expand beyond typed parameters and the pinned Skyvern factory without semantic-name matching.
- Detect auto-approval/skip-confirmation configuration.
- Detect broad filesystem roots, host mounts, Docker socket exposure, and unscoped file tools.
- Detect MCP tool pass-throughs and enumerate statically registered server capabilities.
- Detect tool parameters used as HTTP origins while preserving fixed-host URL templates and urllib
  `Request` objects as negatives.
- Attach exact fail-closed Python scheme/hostname allowlists to their initial-origin capability while
  preserving redirect and DNS scope as unresolved rather than claiming full SSRF prevention.
- Resolve same-file TypeScript URL validators while distinguishing always-on schemes from optional,
  default-open hostname configuration.
- Resolve source-proven imported Python transports only when initial and redirect origins, connected
  peers, and proxies are all covered; retain default-on, opt-out, and force-safe configuration.

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

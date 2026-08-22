# Evidence-backed roadmap

Priorities use `impact × corpus frequency × technical feasibility`, each scored from 1–5. Frequency
is based on the initial 71-repository corpus; scores will be recalibrated as the benchmark grows.

| Priority | Capability | Impact | Frequency | Feasibility | Score | Evidence |
|---:|---|---:|---:|---:|---:|---|
| 1 | Agent bill of materials: models, providers, frameworks, tools, MCP | 4 | 5 | 5 | 100 | 44 multi-provider research signals; schema v64 proves exact selected-path framework/provider evidence in 40/48 repos; 50 have MCP signals and 69 have privileged-capability signals |
| 2 | Dangerous shell and code execution | 5 | 4 | 4 | 80 | 42 shell-capable repos; 8 `shell=True` candidates |
| 3 | MCP server/tool trust-boundary analysis | 5 | 4 | 4 | 80 | 50 MCP repos; 49 forwarding reviews plus 16 automatic unpinned/floating package installs across four pinned repositories |
| 4 | Approval coverage and bypass paths | 5 | 4 | 3 | 60 | 52 approval-positive; 18 auto-approval candidates; three exact environment-backed callbacks reach privileged OpenAI built-ins, while one Python agent→MCP binding inherits a disabled default without a destructive-capability claim |
| 5 | Filesystem scope and destructive writes | 5 | 4 | 3 | 60 | 59 writable-filesystem repos |
| 6 | Sandbox boundary quality | 5 | 4 | 3 | 60 | 64 sandbox-positive; schema v64 finds 20 exact host/privilege/credential boundary reviews across 10 repos |
| 7 | Parameter-controlled network origins | 5 | 2 | 4 | 40 | 18 reviews across 11 repositories; Composio CLI adds a schema-gated tool-argument URL upload through raw fetch, while Google ADK OpenAPI provides a fixed-origin counterexample with encoded model path segments, alongside the existing exact Python, n8n, Flowise, Google ADK load-page, Activepieces, and Composio conditional-runtime control states |
| 8 | A2A AgentCard endpoint provenance | 5 | 2 | 4 | 40 | Two pinned TypeScript clients accept remote-card-selected RPC origins; ADK Python supplies two guarded comparison paths |
| 9 | Consequential-action audit coverage | 4 | 4 | 2 | 32 | 57 tracing-positive; ADK BigQuery supplies attributable test storage, while one exact Skyvern production actor gap now raises AV-AUDIT001 without generic absence inference |

## Milestone 1 — explainable discovery

- Parse Python and TypeScript without executing project code.
- Emit Agent IR nodes for models, agents, tools, MCP servers, capabilities, controls, and evidence.
- Produce deterministic text and JSON reports.
- Support OpenAI, Anthropic, Azure OpenAI, Google, AWS Bedrock, Mistral, Groq, Cohere, and Ollama
  providers; LangChain/LangGraph, CrewAI, AutoGen, OpenAI Agents SDK, Google ADK, Semantic Kernel,
  LlamaIndex, Agno, Mastra, smolagents, Microsoft Agent Framework, CAMEL, Qwen-Agent, Lagent,
  MetaGPT, Marvin, AgentScope, Vercel AI SDK, and common MCP configuration shapes. Newer provider and
  framework taxonomy requires exact frontend-specific SDK/import evidence rather than adjacent names.

## Milestone 2 — high-confidence local rules

- Detect shell invocation and distinguish constant argv from dynamic shell strings.
- Detect direct code evaluation and interpreter tools.
- Require a provenance-backed browser receiver before promoting dynamic `.evaluate(...)` input;
  expand beyond typed parameters and the pinned Skyvern factory without semantic-name matching.
- Detect auto-approval/skip-confirmation configuration.
- Detect broad filesystem roots, host mounts, Docker socket exposure, and unscoped file tools.
- Detect MCP tool pass-throughs and enumerate statically registered server capabilities.
- Resolve literal MCP `npx`/`uvx` launchers and review automatic installs unless the selected package
  carries an exact version.
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

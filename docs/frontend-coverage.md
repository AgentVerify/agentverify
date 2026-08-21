# Frontend coverage and known gaps

This document separates implemented syntax from empirical corpus observations. A missing signature
does not mean a repository lacks agents or controls: AgentVerify may not support its language,
framework, wrapper, or configuration path. Counts come from schema-v6
`benchmarks/engine-results.json`, generated from the 71 pinned partial checkouts.

## Empirical coverage by repository category

“With” columns count repositories containing at least one selected-file observation of that Agent IR
kind. Categories and signature kinds can overlap.

| Category | Repositories | Source-bearing | With framework | With provider | With MCP/protocol | With capability |
|---|---:|---:|---:|---:|---:|---:|
| autonomous-agent | 3 | 3 | 2 | 3 | 1 | 3 |
| browser-agent | 3 | 3 | 2 | 3 | 2 | 3 |
| coding-agent | 15 | 15 | 1 | 5 | 8 | 14 |
| computer-agent | 1 | 1 | 0 | 1 | 0 | 1 |
| examples | 2 | 2 | 2 | 2 | 1 | 2 |
| framework | 22 | 22 | 13 | 17 | 19 | 21 |
| mcp | 9 | 9 | 2 | 2 | 8 | 8 |
| observability | 2 | 2 | 2 | 2 | 1 | 2 |
| research-agent | 1 | 1 | 1 | 1 | 1 | 1 |
| sandbox | 2 | 1 | 0 | 0 | 0 | 1 |
| tool-platform | 2 | 2 | 2 | 2 | 2 | 2 |
| visual-platform | 4 | 4 | 1 | 0 | 1 | 4 |
| workflow-agent | 3 | 3 | 1 | 3 | 1 | 3 |
| workflow-platform | 2 | 2 | 0 | 1 | 2 | 2 |
| **Total with observation** | **71** | **70** | **29** | **42** | **47** | **67** |

Observed framework signatures are LangChain (18 repositories), OpenAI Agents SDK (9), LangGraph
(8), CrewAI (4), PydanticAI (3), AutoGen (1), and Cline SDK (1). Provider observations are OpenAI
(40), Anthropic (16), and Azure OpenAI (10). These counts overlap and are lower than research-wide lexical signals
because the engine requires supported selected files and more specific syntax.

Across the selected snapshot, 8,204 agent/tool observations have module-qualified symbol IDs. Of
2,708 relationship endpoint observations, 1,863 carry IDs and 1,861 resolve to an observed component
(1,627 Python and 234 TypeScript); the two unmatched IDs are explicit Python re-export targets.
Repeated Python and TypeScript constructor bindings are occurrence-qualified. Their direct source
edges resolve exactly. In Python files with repeated identities, schema v6 records 325 same-scope and
14 module-scope single-definition resolutions, plus 23 `ambiguous-repeated-binding` references that
remain withheld.
Capability/control taxonomy endpoints intentionally lack
source-symbol IDs, so the endpoint fraction is inventory coverage rather than an accuracy or recall
metric.

The native AI BOM 1.1 resolver independently classifies all 2,708 endpoints: 1,861 by symbol ID, 300
by exact relationship evidence, 17 by a unique display name, 30 as ambiguous, and 500 as unresolved.
Evidence-local resolution removed 295 capability/control ambiguities; occurrence-qualified bindings
then removed all 688 source agent/tool ambiguities, and conservative lexical resolution removed 145
target ambiguities. The remaining 30 are tool targets without a unique local symbol or target location.

The TypeScript graph contains 95 structure-backed agent edges: 14 agent-as-tool delegations and 81
agent-to-tool edges. All 81 tool endpoints resolve to an observed component. This replaces a prior
token-level array heuristic that could turn words inside callbacks, strings, or nested options into
spurious tool edges.

## Implemented syntax

| Frontend | Implemented observations and resolution |
|---|---|
| Python AST | Imports; known agent/model constructors; tool decorators; literal tool/handoff lists; module-, class-, and repeated-occurrence-qualified agent/tool IDs; shell, eval, filesystem, HTTP, browser, MCP, and Docker SDK calls; absolute and filesystem-relative tool imports; literal approval decorators; OpenAI Agents `ShellTool`/`ApplyPatchTool`/`CustomTool` approval constructors; env-backed auto-approval flags with direct true-return branches and same-class approval short circuits; statement-ordered MCP rejection guards and internal tool-registry routing lookups; lexically scoped OpenTelemetry spans. |
| TypeScript/JavaScript structural lexical | Known imports/providers; balanced top-level `new Agent({tools: [...]})` entries; `tool(...)`, `functionTool(...)`, `toolNamespace(...)`, OpenAI built-ins, Cline `createTool(...)`, and assigned/inline `asTool(...)`; module- and repeated-occurrence-qualified agent/tool IDs; named relative imports and aliases; child-process and Bun `sh -c` calls with literal/dynamic distinction; direct eval; filesystem calls; MCP forwarding object shapes; literal tool approval settings; inline and module-flag env-backed auto-approval branches. Comments and string contents are masked before policy matching. |
| MCP JSON | Common `mcpServers` configuration, transport/command/URL, redacted arguments, and environment-variable names. Configuration is read as data; servers are never launched. |
| Container configuration | Compose/devcontainer Docker socket, privileged/host network/root mounts; Kubernetes/Helm privileged, host namespace, privilege escalation, service-account token, and `hostPath`; literal privileged Python Docker SDK calls. |

## Explicitly unsupported or unresolved

- Go, Rust, Java, C#, Ruby, shell, and other language source frontends are not implemented. Their
  repositories may still contribute supported JSON/YAML or embedded Python/TypeScript files.
- Framework signatures do not yet cover Google ADK, Semantic Kernel, LlamaIndex, Agno, Mastra,
  smolagents, Pydantic wrappers beyond direct imports, or custom agent bases. Generic `Agent` syntax
  may inventory an agent without identifying its framework.
- Google, Bedrock, and other model providers are not yet promoted from research signals into the
  engine's provider taxonomy.
- Python package re-exports, wildcard imports, dynamically selected symbols, alias constructors,
  imported policy objects, callback approval results, cross-class approval-attribute flows, and branch-local allowlist proofs remain
  unresolved. Framework/provider/capability names remain taxonomies rather than source symbols.
- The TypeScript frontend is not an AST/type-checker. Computed property names, conditional tool
  expressions, object-composed Agent options, unrecognized wrapper factories, CommonJS alias flows,
  callback approval results, and type-driven resolution can be missed. Its relative-import resolver
  found zero qualifying real edges in this selected snapshot and is currently regression-validated
  separately from the 81 resolved local tool edges.
- Helm templates are not rendered. Kubernetes RBAC, NetworkPolicy, pod scheduling, and the contents
  or sensitivity of mounted paths are not inferred. Compose environment interpolation is not
  evaluated.
- An OpenTelemetry span proves lexical instrumentation only. Exporter configuration, delivery,
  retention, actor attribution, and durable audit storage remain unresolved.
- Selected-path scans parse only selected files. The full module index can locate import targets, but
  unselected definitions and controls are not evidence of repository-wide coverage or absence.

## Quality interpretation

The 151-label rule truth set and 21-label IR relationship set are curated regression suites. They
guard known positives and negatives; they are not an unbiased accuracy estimate. A future holdout
must be sampled separately across the categories above, externally reviewed, and kept sealed while
rules change. Until then, precision/recall values apply only to the published seed labels.

# Frontend coverage and known gaps

This document separates implemented syntax from empirical corpus observations. A missing signature
does not mean a repository lacks agents or controls: AgentVerify may not support its language,
framework, wrapper, or configuration path. Counts come from schema-v2
`benchmarks/engine-results.json`, generated from the 71 pinned partial checkouts.

## Empirical coverage by repository category

“With” columns count repositories containing at least one selected-file observation of that Agent IR
kind. Categories and signature kinds can overlap.

| Category | Repositories | Source-bearing | With framework | With provider | With MCP/protocol | With capability |
|---|---:|---:|---:|---:|---:|---:|
| autonomous-agent | 3 | 3 | 2 | 3 | 1 | 3 |
| browser-agent | 3 | 3 | 2 | 3 | 2 | 3 |
| coding-agent | 15 | 15 | 0 | 5 | 8 | 14 |
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
| **Total with observation** | **71** | **70** | **28** | **42** | **47** | **67** |

Observed framework signatures are LangChain (18 repositories), OpenAI Agents SDK (9), LangGraph
(8), CrewAI (4), PydanticAI (3), and AutoGen (1). Provider observations are OpenAI (40), Anthropic
(16), and Azure OpenAI (10). These counts overlap and are lower than research-wide lexical signals
because the engine requires supported selected files and more specific syntax.

## Implemented syntax

| Frontend | Implemented observations and resolution |
|---|---|
| Python AST | Imports; known agent/model constructors; tool decorators; literal tool/handoff lists; shell, eval, filesystem, HTTP, browser, MCP, and Docker SDK calls; absolute and filesystem-relative tool imports; literal approval decorators; OpenAI Agents `ShellTool`/`ApplyPatchTool`/`CustomTool` approval constructors; statement-ordered MCP rejection guards; lexically scoped OpenTelemetry spans. |
| TypeScript/JavaScript lexical | Known imports/providers; `tool(...)`/`functionTool(...)`; `new Agent({tools: [...]})`; named relative imports and aliases; child-process calls with literal/dynamic distinction; direct eval; filesystem calls; MCP forwarding object shapes; literal `needsApproval: true` and auto-approval settings. Comments and string contents are masked before policy matching. |
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
  imported policy objects, callback approval results, and branch-local allowlist proofs remain
  unresolved. Display identities are not yet fully module-qualified.
- The TypeScript frontend is not an AST/type-checker. Computed properties, object spreads, wrapper
  factories, complex nested tool arrays, CommonJS alias flows, callback approval policies, and
  type-driven resolution can be missed. Its cross-file resolver found zero qualifying real edges in
  this selected snapshot and is currently regression-validated only.
- Helm templates are not rendered. Kubernetes RBAC, NetworkPolicy, pod scheduling, and the contents
  or sensitivity of mounted paths are not inferred. Compose environment interpolation is not
  evaluated.
- An OpenTelemetry span proves lexical instrumentation only. Exporter configuration, delivery,
  retention, actor attribution, and durable audit storage remain unresolved.
- Selected-path scans parse only selected files. The full module index can locate import targets, but
  unselected definitions and controls are not evidence of repository-wide coverage or absence.

## Quality interpretation

The 121-label rule truth set and 12-label IR relationship set are curated regression suites. They
guard known positives and negatives; they are not an unbiased accuracy estimate. A future holdout
must be sampled separately across the categories above, externally reviewed, and kept sealed while
rules change. Until then, precision/recall values apply only to the published seed labels.

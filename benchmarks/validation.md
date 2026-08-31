# Detection validation log

Validation date: 2026-08-23. Repositories are partial checkouts pinned by
`research/repository-data.json`; paths and results can be reproduced from the corpus scripts.

## AV-EXEC001 — dynamic command through system shell

| Repository | Commit | Selected files scanned | Findings | Representative path |
|---|---|---:|---:|---|
| Aider-AI/aider | `5dc9490b` | 152 | 4 | `aider/editor.py:134` |
| bytedance/trae-agent | `e839e559` | 75 | 3 | `trae_agent/tools/bash_tool.py:229` |
| FoundationAgents/MetaGPT | `11cdf466` | 214 | 1 | `metagpt/repo_parser.py:731` |
| SWE-agent/SWE-agent | `3ea751c0` | 102 | 1 | `tools/windowed/lib/flake8_utils.py:143` |
| cline/cline | `80b3b034` | 194 | 1 | `apps/examples/cli-agent/src/index.ts:19` |
| continuedev/continue | `5522c6f4` | 189 | 1 | `extensions/cli/src/tools/runTerminalCommand.ts:192` |
| RooCodeInc/Roo-Code | `b867ec91` | 209 | 1 | `src/core/tools/ExecuteCommandTool.ts:372` |
| letta-ai/letta-code | `db60f05f` | 231 | 1 | `src/tools/impl/bash.ts:507` |

These are pattern detections, not claims that each application is exploitable. Caller provenance,
input constraints, containment, and approval policy determine exploitability. The rule reports the
dangerous execution primitive with high pattern confidence and leaves reachability for graph analysis.
Schema v117 adds the first exact default-tool reachability path for this rule: Trae Agent's literal
default registry binds `bash` to `BashTool`, its required model `command` reaches persistent
`/bin/bash` stdin, and default-`None` Docker configuration selects the local executor. The optional
Docker executor is retained as available isolation but does not govern the default path.
Schema v118 adds Roo Code's exact native-model composition: the registered `execute_command` schema
reaches `ExecuteCommandTool`, its canonical model command crosses the Task approval callback, and the
approved path reaches `terminal.runCommand`. The approval state is modeled separately below.
Schema v119 adds Letta Code's exact default-tool composition: `Bash` is selected by the Anthropic
default list, bound to its implementation, classified under the default `unrestricted` mode, mapped
to an approved WebSocket decision, and executed through an explicit `zsh`/`bash -c` launcher before
`child_process.spawn(..., shell: false)`. Optional workspace/kernel isolation remains a separate
control setting rather than being credited to the default path.
Schema v120 adds Continue CLI's selected plan-mode path. Normal mode remains the default and asks
for Bash, while plan mode installs an absolute policy override that allows the non-readonly Bash
tool. The same model command passes through `shell-quote` classification and reaches a login-shell
`spawn`; the distinct policy-precedence review is documented under AV-APPROVAL008.

## Regression cases

- `cases/python_dangerous/agent.py`: positive dynamic string plus `shell=True`.
- `examples/safe_agent/agent.py`: negative fixed argv plus default `shell=False`.
- `cases/typescript_mcp`: MCP inventory and approval-bypass candidate.
- `cases/typescript_approved`: literal TypeScript tool approval resolves a governing control, while
  callback and disabled forms remain unresolved.
- `cases/builtin_tool_approval`: OpenAI Agents Python built-in tool instances preserve enabled,
  disabled, callback, and auto-handler approval policies without leaking controls between same-named
  tools.
- `cases/python_openai_hosted_tools`: exact OpenAI web-search, file-search, and image-generation
  imports preserve provider-hosted scope, configuration, canonical alias identity, and unavailable
  approval hooks; near-package and rebound constructors remain unresolved and hosted web search does
  not raise AV-NET001.
- `cases/python_openai_mcp_approval_default`: a directly bound stdio MCP server inherits the OpenAI
  Agents Python disabled approval default; explicit approval and broken SDK propagation stay negative.
- `cases/python_agno_mcp_confirmation`: direct and session-composed Agno filesystem MCP tools retain
  omitted, partial, complete, dynamic, and read-only-filtered confirmation states.
- `cases/python_trae_agent_default_tools`: an exact seven-source Trae Agent composition resolves its
  default Bash/editor paths; a near package and a changed default tool list withhold the graph.
- `cases/typescript_roo_command_approval`: an exact eight-source Roo Code composition resolves the
  native command tool, approval state, allowlist policy, and terminal sink; near packages, incomplete
  chains, and token-boundary matching withhold the graph or specialized review.
- `cases/typescript_letta_default_tools`: an exact 15-source Letta Code composition resolves default
  Bash and Write tools, permission-mode and isolation settings, settings/CLI deny and always-ask precedence,
  and concrete execution sinks; a lookalike client and standard permission default stay negative.
- `cases/typescript_cline_subagent_approval`: an exact nine-source Cline VS Code composition resolves
  root approval policy, default-enabled spawning, child local tools, and dropped policy/callback
  propagation; incomplete chains and forwarded approval state stay negative.
- `cases/typescript_cline_subagent_approval_cli`: an exact ten-source Cline CLI sandbox composition
  resolves startup policy, approval callback, local backend routing, child local tools, and dropped
  policy/callback propagation; incomplete chains and forwarded approval state stay negative.
- `cases/python_semantic_kernel_mcp_sampling`: exact Agent/plugin binding distinguishes explicit
  sampling auto-approval from default/explicit denial, callback, dynamic, and disconnected states.
- `cases/mcp_sampling_consent`: exact Python and TypeScript MCP sampling handlers distinguish
  automatic fulfilment from interactive consent, denial, token caps, unresolved callbacks,
  disconnected receivers, and unrelated imports.
- `cases/mcp_elicitation_consent`: exact Python and TypeScript MCP elicitation handlers distinguish
  automatic acceptance from direct user decisions, decline-only and unresolved callbacks, missing
  capabilities, disconnected receivers, and unrelated imports.
- `cases/typescript_structured_tools`: balanced tool-array parsing, namespace spreads, inline and
  assigned SDK tools, agent-as-tool delegation, approval policies, and unrelated-name negatives.
- `cases/typescript_bun_shell`: Cline inline tools distinguish dynamic Bun `sh -c`, a fixed command,
  direct argv execution, and string-only near misses.
- `cases/typescript_tool_registrations`: import-aware Mastra factory properties and MCP registrations
  retain exact callback-to-capability tool identities, with string and ordinary-registry negatives.
- `cases/typescript_helper_summary`: unique same-file network helpers propagate exact tool edges while
  fixed-host flows and `fetch(...)` text inside JavaScript regex literals remain negatives.
- `cases/mcp_forwarder`: statement-ordered allowlists, internal registries, constructor-only and
  returned closure bindings, plus mutable/rebound negatives remain distinct.
- `cases/mcp_imported_manager`: package reexports and immutable constructor bindings resolve an
  imported registry guard; mutable fields, fallback managers, and rebound imports remain negative.
- `cases/python_post_registration`: exact FastMCP decorator applications resolve same-module and
  relative-imported functions; wrappers, nested calls, rebound bindings, duplicate registrars, and
  unrelated factories remain negative.
- `cases/python_browser_evaluate`: Playwright page evaluation preserves both inventory and browser
  execution context; exact parameter/class/`__init__` `Page` annotations, immutable aliases, and
  exact `TYPE_CHECKING` imports prove dynamic receivers. Literal JavaScript, ordinary non-browser
  `.evaluate(...)`, reassigned parameters, wrong/conflicting fields, static methods, near packages,
  and rebound or duplicate import aliases remain negatives.
- `cases/python_registry_tools`: import-proven MetaGPT function/class and Qwen class decorators retain
  exact entrypoints and capability edges; unlisted methods, nonliteral entrypoints, rebound or
  unrelated registrars, arbitrary `.open()` methods, fixed filesystem paths, and fixed HTTP origins
  remain negative for their corresponding rules.
- `cases/python_literal_tool_bindings`: literal Agent tool lists recover immutable module callables,
  same-block and module-level constructor bindings, occurrence-qualified inline constructors, and
  direct context-manager bindings; reassignment, branch-only definitions, parameters, arbitrary
  factories/builtins, ambiguous or shadowed imports, and nested or reassigned contexts stay unresolved.
- `cases/python_tool_factory_adapters`: immutable imported `from_settings` factories, exact
  HostedMCP/LangChain adapter constructors, and same-block `Agent.as_tool()` bindings receive exact
  tool identities and delegation/capability edges; unknown factories, ambiguous imports, parameters,
  non-Agent or forward receivers, and receiver/adapter reassignment stay unresolved.
- `cases/python_imported_literal_tool`: immutable absolute imports resolve either one exact selected
  local callable export or an explicit SDK import boundary; parameter/local/class shadowing,
  duplicate imports, and forward imports remain unresolved, while the local export proves cross-file
  filesystem reachability.
- `cases/python_imported_network_helper`: exact named imports propagate unique top-level helper
  network behavior and caller arguments; fixed origins and arguments remain inventory-only, while
  nested helpers, module calls, rebound imports/clients, and local reassignment remain unresolved.
  Single-entrypoint class cases cover direct construction, immutable fields, two-hop propagation,
  fixed inputs, mutation, `setattr`, shadowing, module-qualified calls, and rebound constructors.
- `cases/network_dynamic_origin`: import-proven urllib module/named aliases cover direct URLs and
  `Request(url)` objects; fixed hosts remain inventory while local shadowing and module rebinding
  withhold the opener identity.
- `cases/python_proxy_conditional_network_helper`: direct fetches and manually followed redirects
  retain distinct policy states; proxy-dependent pinning stays conditional, while a missing peer
  assertion and an ordinary request remain negative.
- `cases/python_configurable_network_helper`: default-on connector gates compose with allowlist and
  loopback exemptions, enforcement-conditional pinning/proxy rejection, and distinct redirect modes;
  disabling the default, breaking the pinned backend, or calling ordinary `httpx` remains negative.
- `cases/typescript_configurable_ssrf_composition`: a default-off real-versus-passthrough service
  choice propagates into a LangChain tool and Axios helper; a default-on mutation changes policy
  state, while branch, lookup, and redirect-hook mutations plus a raw-Axios near miss remain negative.
- `cases/typescript_flowise_secure_request`: variable Flowise node URLs reach either a fixed Axios
  request object or `secureFetch`; the latter overrides caller options with a pinned agent after the
  spread. Default, redirect, lookup, deny-predicate, caller-transport, mapped-IP, broken class-flow,
  and unrelated same-named-helper negatives withhold the corresponding policy edge.
- `cases/typescript_google_adk_secure_fetch`: an imported `FunctionTool` maps its model URL into a
  same-file global-fetch helper with fail-closed address preflight and disabled redirects; missing
  imports, fixed inputs, automatic redirects, incomplete DNS/address checks, and mapped-IP bypasses
  withhold the edge.
- `cases/typescript_axios_instance`: immutable same-file Axios instances cover direct verbs and
  `.request(...)`, fixed bases, absolute-URL override disabling, no-base behavior, and a shadowed
  local-client negative.
- `cases/typescript_activepieces_safe_http`: exact Activepieces imports compose a manifest-pinned
  filtering Axios client with the MCP transport; private-address, agent-ordering, caller-proxy,
  manifest, and import mutations withhold the policy.
- `cases/typescript_composio_ssrf_safe_fetch`: conditional package imports preserve Node Undici
  pinning, configured-route residuals, edge fail-closed behavior, and the distinct intentionally
  unguarded `WhereSupported` fallback; runtime-map and transport mutations withhold the policy.
- `cases/typescript_composio_cli_upload`: schema-marked tool arguments recursively reach raw fetch
  for URL file inputs; guarded transport, fixed arguments, broken gates, and wrong imports withhold
  the path.
- `cases/typescript_google_adk_openapi_rest_tool`: generated OpenAPI tools preserve a
  spec-configured origin while encoding model path segments; dynamic server variables, unencoded
  paths, credential URL rewrites, and broken factory imports withhold the control.
- `cases/typescript_a2a_card_endpoint`: two remote-card flows reach `ClientFactory`: ADK JS through
  an import-proven resolver and Gemini through an Undici agent/proxy dispatcher. Fixed cards, fixed
  resolver inputs, wrong imports, and unproven dispatchers withhold the corresponding edge.
- `cases/python_a2a_card_endpoint`: cached and per-invocation client creation are both dominated by
  all-interface HTTPS/loopback and same-origin validation. Primary-interface-only, reversed-origin,
  and permissive-scheme mutations withhold the policy edge.
- `cases/sandbox_boundary`: host/privilege settings, Docker SDK calls, and nine exact host credential
  binds are reviews; named volumes, adjacent path names, and ordinary workspace mounts stay negative.
- `cases/framework_provider_taxonomy`: exact Python and TypeScript framework/provider imports,
  literal `bedrock-runtime` selection, Gemini model prefixes, frontend-specific Vercel AI SDK
  package boundaries, and agent-specific CAMEL/Marvin submodules produce taxonomy components;
  near-name packages, unrelated Google Cloud/AWS clients, and Gemma model names remain negative.

## Full-corpus engine benchmark

The 2026-08-31 default scan covered 70 source-bearing repositories plus one docs-only upstream
snapshot. It parsed 10,797 selected Python/TypeScript/JavaScript files plus 155 configuration files,
resolved 2,947 relationships with 10,819 symbolized components, and completed in 927.4887 seconds
on the development machine. The summary now exposes the Vercel AI Code Mode approval/tool surface as
a named `typescript_vercel_code_mode` slice: one repository, eight components, and seven
approval/surface relationships. Three parse warnings were isolated and reported without aborting the
run. Tests and fixtures are inventoried but excluded from findings by default; `--include-tests`
enables them. The pinned corpus contains no AgentVerify inline directives, so the benchmark records
zero suppressed findings.
For focused development, `scripts/benchmark_engine.py --repository <owner/name>` can refresh one or
more named corpus repositories before paying the full-corpus cost; release evidence should still use
the default unfiltered 71-repository run.

The locked collector prioritizes manifests, production SSRF/URL-safety sources, and then general
security/agent/tool/MCP sources within the 220-file cap. It adds at most 20 local source files:
versioned audited evidence hints plus Python imports reached from MCP forwarding or source-proven
URL-security call sites, all charged against the dependency cap. This refresh materialized 202 dependency files across 25
repositories; the engine scans all of them, while the collector's lexical-signal inventory retains
its independent 2 MB per-repository byte cap. Collector schema v4 records the hint manifest and
dependency count per repository; engine schema v123 carries both the 202-file total and the
25-repository coverage.

Engine benchmark schema v96 retains stable component-name taxonomies, category presence counts,
matched-versus-identified endpoint counts, TypeScript graph precision measures, and exact MCP
forwarding-control counts. It also publishes Python and TypeScript initial-origin control coverage
plus source-proven Python and TypeScript secure transports, with redirect, DNS, proxy, configured
scope, and open/default-disabled states kept separate. It intentionally
excludes arbitrary agent/tool display names from the summary. The resulting
framework/provider/protocol/capability coverage and unsupported syntax are published in
`docs/frontend-coverage.md`; presence counts are discovery observations, not recall measurements.

Schema v63 retains exact BOM taxonomy while adding approval-callback graph and finding semantics. Framework
presence rises from 34 to 40 repositories while provider presence remains 48 and gains four named
SDK families. The selected paths identify Vercel AI SDK in five repositories, Microsoft Agent
Framework in two, and CAMEL, Qwen-Agent, Lagent, MetaGPT, Marvin, and AgentScope in one each. Groq
appears in five repositories, Ollama in four, and Mistral and Cohere in three each. Frontend-specific
signatures keep Python package roots separate from TypeScript's exact `ai` package. Eighty component
labels cover 51 positives and 29 near-name or unrelated negatives.

Schema v73 separates import-only provider presence from exact configured calls for Mistral, Groq,
Cohere, and Ollama. Import/alias proof identifies 29 calls across seven repositories: 20 native SDK
calls and nine LangChain wrappers. Seven production calls occur across five repositories; the other
22 calls and all 12 literal call-model arguments are test-scoped. Reassignment removes the binding,
and Mistral-owned literal prefixes remain distinct from unqualified Mixtral or third-party model IDs.

Schema v74 adds official TypeScript AI SDK call attribution for Mistral, Groq, and Cohere. It covers
named aliases, destructured dynamic imports, provider factories, immutable configured instances, and
direct language/embedding/reranking model calls. The pinned corpus has one production Groq model
call in Mastra, reached through an exact dynamic import; its nonliteral model argument is not promoted
to a model component. Four rebound or near-package negatives pin the conservative boundary.

Schema v75 extends exact Python attribution through framework provider APIs. AgentScope's public
`OllamaChatModel` reexport contributes two production calls and literal models. PydanticAI contributes
32 test-scoped provider/model/embedding wrapper calls and 21 literal models. Combined with schema
v73, the Python inventory has 63 calls across eight repositories: 20 native SDK and 43 wrapper calls,
with wrapper splits of nine LangChain, 32 PydanticAI, and two AgentScope. Nine calls across six
repositories are production-scoped; 54 are tests. Exact AgentScope evidence raises overall provider
presence from 48 to 49 repositories and Ollama presence from four to five.

Schema v76 resolves provider identity by exact exported symbol when one public wrapper module spans
several providers. AgentScope adds eight production calls: four OpenAI Chat/Responses, two Anthropic,
and two Google Gemini. The Python inventory reaches 71 calls across eight repositories: 20 native
SDK and 51 wrapper calls, split into nine LangChain, 32 PydanticAI, and ten AgentScope calls.
Seventeen calls are production-scoped, 54 are tests, and all 43 literal call-model values inherit
exact import proof. Overall provider presence remains 49 repositories; OpenAI rises to 42 and
Anthropic and Google to 18 each.

Schema v100 adds four more exact exports from the same public AgentScope module without widening to
class-name matching: `DashScopeChatModel`, `DeepSeekChatModel`, `MoonshotChatModel`, and
`XAIChatModel`. The pinned sample contributes nine production calls—four Alibaba DashScope, one
DeepSeek, two Moonshot AI, and two xAI—and nine literal models. Python reaches 80 exact calls across
eight repositories: 20 native SDK and 60 wrapper calls, split into nine LangChain, 32 PydanticAI,
and 19 AgentScope calls. Twenty-six are production-scoped, 54 are tests, and all 52 call-model values
are literal. Four explicit rebinding negatives pin the import boundary.

Schema v101 adds exact PydanticAI modules for Anthropic, Google/Google Cloud, AWS Bedrock, xAI, and
DeepSeek. Dedicated provider constructors, model wrappers, and Google/Bedrock embedding wrappers
are import- and rebinding-aware; only model/embedding wrappers accept positional literal model IDs.
The expansion adds 266 calls: 263 test-scoped calls in PydanticAI and three production calls in
Marvin. Python reaches 346 exact calls across nine repositories: 20 native SDK and 326 wrapper calls,
split into nine LangChain, 298 PydanticAI, and 19 AgentScope calls. Twenty-nine are production-scoped,
317 are tests, and 227 carry literal models. Generic PydanticAI OpenAI-compatible wrappers remain
unattributed because the corpus uses them with Azure, DeepSeek, AIMLAPI, and custom base URLs.

Schema v102 adds exact Agno model-module attribution for OpenAI Chat/Responses, Google Gemini,
Anthropic Claude, Azure OpenAI, and Groq across both public reexports and observed direct submodules.
The corpus contains 220 Agno calls: 206 production calls across Agno and AgentOps, plus 14
OpenLLMetry tests. Two hundred eighteen carry literal `id=` or positional model values. Python
reaches 566 exact calls across 11 repositories: 20 native SDK and 546 wrapper calls, split into nine
LangChain, 298 PydanticAI, 19 AgentScope, and 220 Agno calls. Two hundred thirty-five are production
scoped, 331 are tests, and 445 carry literal models. Eight rebinding and two custom-endpoint
negatives pin the boundary.

Schema v115 recognizes AutoGen's current official `autogen_agentchat`, `autogen_core`, and
`autogen_ext` namespaces in addition to the legacy `autogen` package. The pinned Microsoft AutoGen
checkout contributes 239 exact import observations and 15 exact model-client calls; AgentOps adds
two more production calls. Exact imports identify OpenAI, Azure OpenAI, and Anthropic wrapper
constructors, while literal `model=` values inherit that identity. Across the corpus, the 17 new
calls comprise seven production paths, ten tests, and 13 literal models. Python attribution reaches
583 calls across 12 repositories: 20 native SDK and 563 wrapper calls, with 242 production calls and
341 tests; 458 calls carry literal models. A custom OpenAI-compatible `base_url`, rebound
constructors, and near packages remain unattributed. Sixteen focused component labels pass at
11 TP / 5 TN.

Selected local package reexport chains of exact provider-wrapper symbols now preserve attribution
when each reexport module imports a known AgentScope or PydanticAI symbol/proven alias and does not
rebind the exported alias. Star imports from proven local reexport modules are supported for names
visible through literal `__all__` or non-underscore exports. Simple imported local wrapper factories
are also supported when they have one return path to a proven provider-wrapper constructor and map
the model from a literal or factory parameter; those factory summaries also survive direct local
reexport chains and star imports when the factory name is visible. Thirty-five local IR labels pin
direct, transitive, wildcard, wrapper-factory, direct factory reexport, and wildcard factory reexport
provider/model positives plus rebound, filtered, and ambiguous negatives.

Schema v103 expands official TypeScript AI SDK call attribution to OpenAI, Anthropic, Google, Azure
OpenAI, and xAI. With the existing Groq call, the selected corpus contains 33 production calls across
OpenAI Agents JS, Mastra, Activepieces, Vercel AI, and Composio: 31 model calls, two factory calls,
four inline/configured-instance calls, and 22 literal model IDs. The provider split is 14 OpenAI, 13
Anthropic, three Google, one Azure OpenAI, one xAI, and one Groq. Exact direct/dynamic imports, image
models, and observed inline embedding methods are included. Literal `baseURL`, unknown or arbitrary
spread factory configs, generic compatible packages, and rebindings are withheld; endpoint-neutral
`spreadIfDefined('apiVersion', ...)` is accepted for Azure-style default configuration. Local and
pinned negatives cover Inception, Azure-hosted Anthropic, mock OpenAI endpoints, and a baseURL spread
counterexample.

Local TypeScript AI SDK reexport regressions now preserve exact provider and model attribution
through named local barrels when the export chain reaches one supported official `@ai-sdk/*`
instance or factory symbol. Eight positive labels cover direct OpenAI, Google factory, transitive
OpenAI, and Azure factory reexports; four negative labels keep ambiguous reexports,
function-parameter-shadowed local imports, and Azure baseURL-spread reexports unresolved.
Three additional real Activepieces negatives pin the opposite boundary: the workspace
`createLanguageModel({ provider, modelId })` wrapper and Cloudflare `@ai-sdk/openai-compatible`
gateway branch remain unresolved because the wrapper implementation is not source-visible in the
pinned checkout and the compatible endpoint is custom-configured.

Schema v104 adds native TypeScript provider SDK constructors through exact ESM imports. The selected
corpus contains 17 production calls across five repositories: ten OpenAI, four Anthropic, and three
Google. Combined with the 33 official AI SDK calls, TypeScript attribution reaches 50 production
calls across eight repositories. No-argument and literal, spread-free default-endpoint configs are
accepted; unknown configs, `baseURL`/`baseUrl` at any literal nesting depth, rebindings, and CommonJS
imports are withheld. Two pinned real-source custom-endpoint/config boundaries complement the
local positive, rebound, and endpoint fixtures.

Local TypeScript model-binding regressions now also prove exact immutable module-level literal object
maps for native SDK request objects and official AI SDK first model arguments. Nine positive labels
cover `MODEL_IDS.chat`, `MODEL_IDS["chat"]`, and `MODEL_IDS["chat-model"]`-style native language,
AI SDK language, and AI SDK embedding calls; eight negative labels keep mutable object properties,
nonliteral object values, dynamic bracket keys, and dynamic bracket member writes unresolved. Exact
`@ai-sdk/azure` factory/configured embedding labels plus real Activepieces Azure embedding provider,
Azure reexport, exact single-symbol star-barrel, and exact top-level CommonJS-destructuring boundary
labels, followed by exact TypeScript OpenAI Agents sandbox inventory labels, raise the public IR
truth set to 1,856 passing labels without broadening provider identity inference or conflating
SDK-sandbox shell/filesystem/memory/skill-loading capability reachability, or exact/conditional SDK
sandbox runtime selection, including inline-created and typed session bindings, helper-returned
agent session edges, Runner option-level session config, delegated `asTool` runConfig sessions,
extension Runner backends, explicit `exposedPorts` sandbox network-exposure controls, and
`extraPathGrants` sandbox path-grant controls, Manifest environment-variable controls, Manifest
entry-source controls, Manifest workspace-root controls, literal local snapshot state-persistence
controls, literal `sandbox.concurrencyLimits` runtime controls, and literal sandbox memory-policy
controls for read/generation/layout settings, plus nested literal Manifest directory/file seed
controls and literal sandbox working-directory controls, with host-local execution risk.

Schema v105 adds the immutable direct CommonJS default-export form for the OpenAI and Anthropic
packages. Two GPT Pilot templates contribute four production constructors, bringing TypeScript to
53 exact calls across nine repositories: 21 native SDK calls and 32 official AI SDK calls. The
CommonJS proof requires one module-level `const` require binding with no reassignment or parameter shadow; custom
and unknown configs share the ESM endpoint boundary. Six positive and five negative labels pin the
new local and real-source behavior.

Schema v106 follows immutable native client instances into exact provider-owned model methods. The
corpus adds three production OpenAI requests and model components across Composio and AgentGPT,
raising TypeScript attribution to 56 calls: 21 constructors, three native model calls, and 32 AI SDK
calls. Exact method chains and a literal `model` property in the direct request object are required.
Eighteen positive labels cover ESM/CommonJS local paths and all three pinned provider/model pairs;
three negatives pin rebound instances, nonliteral request objects, and unrelated SDK methods.

Schema v107 corrects import-shadow parsing so constructor names used in annotations or qualified SDK
types remain valid imports, while actual parameter bindings still invalidate them. It recovers one
OpenAI and one Anthropic constructor, then proves the OpenAI client across a four-function same-file
chain by unanimous direct-call-site fixed point. TypeScript reaches 59 calls: 23 constructors, four
native model calls, and 32 AI SDK calls; one model call carries the dedicated typed-parameter proof.
Seven positive and five negative labels cover the two recovered constructors, pinned provider/model
path, local transitive path, export/mixed/cycle/value-escape withholding, and true shadowing.

Schema v77 assigns stable IDs to results of exact imported Python MCP stdio constructors and
resolves a direct Agent edge only for an earlier, unreassigned same-block binding selected in a literal
`mcp_servers=[...]` list. Literal non-package processes such as Marvin's Deno server remain inventory
without package facts; its `uvx mcp-server-git` peer retains package provenance. Eight positive and
three negative local/pinned labels cover both component and edge behavior plus forward, rebound, and
indirect-container withholding. Across the corpus, 27 import-bound literal constructor calls span
seven repositories: 23 assigned calls receive stable IDs, 20 are non-package processes, seven are
package-backed, and ten are production-scoped. Both resolved Agent edges are production-scoped and
occur in Marvin.

Schema v78 recognizes in-process FastMCP servers only through the exact `fastmcp` or `mcp.server`
exports. It also resolves an earlier immutable module assignment from a function or module control
block when the binding has one module mutation and no shadow in any enclosing lexical scope. Marvin
pins the production FastMCP main-guard edge, a test-scoped module stdio edge, and a conditional-import
FastMCP inventory-only component. Nine positive and four negative new labels cover these paths plus
rebound, shadowed, forward, and near-package local forms.
The corpus contains 240 exact in-process constructor calls across 13 repositories: 227 assigned
results have stable IDs and 22 calls are outside tests. Agent→MCP coverage reaches four fully
resolved Marvin edges—two same-block and two immutable-module—with three outside tests.

Schema v79 accepts one top-level constructor import nested in a `try` only when every handler
terminates. Immutable exact FastMCP registrars then create server→tool edges for exact decorators and
post-registration calls, and capability context traverses Agent→server→tool. Marvin's goose example
pins the fail-closed import, two registered tools, its Agent edge, and the dynamic filesystem path;
fall-through imports and rebound registrars remain disconnected. The corpus has 121 exact FastMCP
server→tool edges across eight repositories; every source and target ID resolves, and 89 edges are
outside tests. Marvin has five exact Agent→server edges, three Agent-reachable registered tools, and
one production Agent→server→tool→filesystem capability path.

Schema v80 adds exact `with`/`async with` MCP identities and exact-import OpenAI `SandboxAgent`
inventory. A context-bound server reaches an Agent only for a direct in-body statement before any
reassignment; duplicate, rebound, escaped, nested, indirect, and near-import cases stay disconnected. Nested
OpenAI `params={command,args}` stdio configuration can retain the server identity even when some
launch arguments are dynamic, without receiving package provenance. Across eight repositories, the
stdio inventory now has 41 exact constructors: 34 assignment-bound and three context-managed calls
carry 37 stable IDs, 11 calls are outside tests, and seven are package-backed. The OpenAI context
edge raises exact Python Agent→server coverage to six edges across two repositories, five outside
tests, and attaches the existing disabled-default approval proof to the same server ID. The pinned
OpenAI checkout also contributes 156 exact-import `SandboxAgent` assets, 15 outside tests.

Schema v81 recognizes imported project-local MCP adapter subclasses through an exact two-file proof.
The exported class must be an immutable top-level direct subclass of an exact SDK `MCPServer` import
and directly define both `list_tools` and `call_tool`; its importer and instance binding must also be
unique, unreassigned, ordered, and in the same lexical scope. Near bases, incomplete adapters,
rebound bindings, and forward use remain disconnected. The pinned corpus contributes one production
instance in Skyvern and one exact Agent→adapter edge. Exact Python Agent→server coverage therefore
reaches seven resolved edges across three repositories, six outside tests.

Schema v82 resolves direct local Agent factory functions only when the helper is undecorated,
uniquely defined earlier in the same statement block, and has one direct top-level return of an
import-proven Agent constructor. Its assigned result must still dominate the consuming Agent
composition without mutation. The pinned OpenAI SDK contributes eight exact SandboxAgent handoff
edges through two returned definitions, all under tests; the final two repeated-binding ambiguities
fall to zero. Conditional/indirect returns, rebound or forward helpers, constructor shadowing, and
result mutation remain unresolved.

Schema v83 adds an exact-import proof for OpenAI Agents Python `LocalShellTool`. The constructor must
come from one immutable, earlier, top-level `agents` or `agents.tool` import; aliases are accepted,
while near-package and rebound imports remain negative. The pinned SDK contributes five test-scoped
instances, five local shell-capability edges, and four exact Agent bindings. All five record
`approval_policy: unavailable` because the SDK constructor exposes no approval parameter. Two
resumed-state references remain ambiguous rather than selecting a repeated occurrence.

Schema v84 extends exact-import built-in proof to OpenAI Agents Python `CodeInterpreterTool`. The
pinned corpus contributes five hosted-sandbox code-execution assets and edges across OpenAI and
AgentOps; two production examples use literal auto-managed containers and resolve directly from
their Agents. All five expose no SDK constructor approval parameter. Symbolic and casted test configs
retain unresolved container policy, and near-package or rebound constructors remain negative. These
sandboxed inventory assets do not raise AV-EXEC002.

Schema v85 extends the same exact-import proof to provider-hosted `WebSearchTool`, `FileSearchTool`,
and `ImageGenerationTool`. The corpus contains 13 instances across OpenAI, AgentOps, and Traceloop:
seven are outside tests, all 13 have capability edges, and eight resolve from exact Agent bindings.
Six web-search assets retain SDK-default external-access state; four file-search assets include two
literal vector-store scopes; three assets provide hosted image generation. All 13 expose no
constructor approval parameter. Same-named tools from other frameworks, near imports, and rebound
constructors remain negative. Hosted web search stays inventory because no parameter-controlled
origin is proven, so AV-NET001 counts do not change.

Schema v86 resolves Playwright browser evaluators through one exact class-body or `__init__`
attribute annotation. Deferred annotations may use an immutable exact Playwright import inside a
top-level `TYPE_CHECKING` block. Conflicting annotations, duplicate aliases, rebound or near-package
imports, and static/class methods are withheld. This proves 15 production receivers—13 in CAMEL and
one each in LaVague and MetaGPT—raising receiver proof from seven to 22 of 80 observations. The
other 58 remain explicitly unresolved, the sole dynamic tool-input path is unchanged, and no
AV-EXEC002 finding is added or removed.

Schema v87 adds a separate exact constructor proof without trusting field names. One immutable
`sync_playwright` import must flow through straight-line browser or context
construction to a page field assigned once in `__init__`; one immutable local alias is also
accepted. Conditional, later-method, repeated, parameter-supplied, and shadowed-factory bindings are
withheld. This proves 13 additional production receivers in Devika—four direct field uses and nine
aliases—raising coverage to 35 of 80 and leaving 45 explicitly unresolved. The sole dynamic
tool-input path and the 51 corpus AV-EXEC002 findings remain unchanged.

Schema v88 replaces the dotted-call-name gate with structural `.evaluate` recognition, inventorying
six Skyvern chains that were previously invisible: four production Locator calls and two test-only
`super()` calls. Known Playwright locator/get-by/filter/nth/and/or/first/last derivations remain proven only when
rooted in an existing exact receiver and may pass through one immutable local alias. This proves one
additional Skyvern chain while leaving the other five explicit, for 86 total observations, 36 proven,
and 50 unresolved. Its normalized numeric scroll JavaScript remains inventory-only, so the sole
dynamic corpus path and 51 AV-EXEC002 findings are unchanged.

Schema v89 additionally accepts two exact receiver forms. A unique built-in `@property` getter with
an immutable Playwright return annotation proves OpenAI Agents Python's `self.page`; shadowed
decorators, duplicate getter/setter definitions, and wrong types remain negative. A direct unique
module or same-function Playwright runtime import may also flow through a top-level context manager
or direct `.start()`, straight-line browser/context/page construction, and immutable local bindings. Conditional or
reassigned pages, shadowed factories, and non-terminating alternate branches remain withheld. This
proves Aider's fixed user-agent evaluation and two fixed Skyvern test evaluations, raising receiver
coverage to 40 of 86 and leaving 46 unresolved. The dynamic corpus path and 51 AV-EXEC002 findings
remain unchanged.

Schema v90 accepts one uniquely annotated module-level Playwright receiver when its annotation has a
single binding and is not shadowed in the function. A top-level guarded Playwright import qualifies
only when every exception handler terminates; Browser-Use's exact `sys.exit(...)` dependency guard
is the pinned real form. The page-derived Locator assignment must dominate the evaluation in the same
statement-list branch, so a branch-only alias used after the branch remains unresolved. This proves
Browser-Use's fixed-script example, raising receiver coverage to 41 of 86 and leaving 45 unresolved;
the single dynamic corpus path and all 51 AV-EXEC002 findings remain unchanged.

Schema v91 structurally inventories Playwright `evaluate_handle(...)`,
`eval_on_selector(...)`, `eval_on_selector_all(...)`, and Locator `evaluate_all(...)` alongside
`evaluate(...)`. It selects the script from positional argument zero, or argument one for the two
selector APIs, and falls back to the exact `expression=` keyword. Dynamic selectors therefore do
not taint fixed JavaScript. Seven newly inventoried pinned Skyvern test calls add three locally
constructed-page proofs and four unresolved receivers, raising browser-evaluator coverage to 44 of
93 and leaving 49 unresolved. The API split is 86 `evaluate`, five `eval_on_selector`, and two
`eval_on_selector_all` observations. A selected production `eval_on_selector` call without local
Playwright provenance remains excluded; the single dynamic production path and all 51 AV-EXEC002
findings remain unchanged.

Schema v92 resolves exact local async-context-manager page yields. The helper must have one immutable
`contextlib.asynccontextmanager` decorator binding, one exact local Playwright
runtime→browser→context→page chain, and exactly one unconditional page yield. The caller must invoke
that unique local helper directly in a top-level `async with` and leave its target immutable. This
proves four fixed-script Skyvern test evaluators at lines 700, 702, 720, and 745, raising coverage to
48 of 93 and leaving 45 unresolved. Branch-dependent and ordinary-object yields, reassigned targets,
helper-parameter flow, and mutable lifecycle fields remain withheld. The single dynamic production
path and all 51 AV-EXEC002 findings remain unchanged.

Schema v93 resolves one bounded same-class browser-helper pattern. A local Playwright runtime may
select a browser through built-in `getattr(...)` only when the `self` field has one immutable exact
`typing.Literal` annotation containing only `chromium`, `firefox`, and `webkit` values. A private,
undecorated instance-helper parameter is proven only when every selected-module call passes that
local browser directly or through one immutable bound-method alias. This proves MetaGPT's
fixed-script evaluators at lines 69 and 71, raising coverage to 50 of 93 and leaving 43 unresolved.
Mixed calls, mutable or escaped aliases, invalid selector literals, other-class calls, and unknown
arguments remain withheld. The dynamic path and all 51 AV-EXEC002 findings remain unchanged.

Schema v94 resolves exact one-shot lifecycle page fields. The field and each intermediate must be
assigned once to `None` in `__init__`, then once in one undecorated async method through an exact
`async_playwright().start()`→browser→page chain. This proves Devika's fixed-script evaluators at
lines 42, 69, and 85, raising coverage to 53 of 93 and leaving 40 unresolved. Conditional
initialization, page or browser reassignment, and shadowed runtime factories remain withheld. The
dynamic path and all 51 AV-EXEC002 findings remain unchanged.

Schema v95 resolves private same-module helper parameters from unanimous exact context-manager page
call sites. The helper must have one undecorated top-level definition, every selected-module call
must pass the proven page directly, and the function may not escape. This proves Skyvern test
evaluators at lines 676, 677, and 678, raising coverage to 56 of 93 and leaving 37 unresolved. Mixed
or missing arguments, star expansion, helper escape, module-level calls, and lambda-hidden calls
remain withheld; caller-local helper-name and context-manager-factory shadowing are also negative.
The dynamic path and all 51 AV-EXEC002 findings remain unchanged.

Schema v96 resolves branching lifecycle page fields only when one exact Playwright runtime root
reaches every non-`None` assignment through runtime, browser, context, page, or exact popup-event
transitions. This proves CAMEL production evaluators at lines 401, 422, 426, 458, 463, 482, 488,
742, 754, 828, 889, and 890, raising coverage to 68 of 93 and leaving 25 unresolved. Unknown or tuple
writes, dynamic `setattr`, non-popup events, and shadowed factories remain withheld. The dynamic path
and all 51 AV-EXEC002 findings remain unchanged.

Schema v63 retains A2A endpoint provenance as a separate authority class: four exact client-construction
paths comprise two unconstrained remote-card-selected TypeScript origins and two same-origin-
constrained ADK Python paths. The guarded paths validate every advertised interface; the Gemini path
also records its Undici agent/proxy transport. These metrics do not count configured card URLs as
model-controlled AV-NET001 origins.

Schema v63 also publishes immutable same-file Axios-instance metrics and the sixth TypeScript
secure-network composition. The corpus-level generic instance counters are zero; those syntax paths
are fixture-validated. The selected Activepieces path contributes one imported-client capability and
one address-filtering control with configured allowlist and environment-proxy residual metrics. Four
Composio edges separately count configured-route pinning residuals, one edge-runtime fail-closed path,
and three edge-runtime unguarded fallbacks.

The benchmark now also measures identity coverage: 10,069 component observations carry
module-qualified IDs. Of 4,756 relationship endpoints, all 3,946 identified symbol endpoints resolve
to an observed component (3,587 Python and 359 TypeScript). The current schema records 379
`lexical-single-definition` targets, 20 exact same-block dominating definitions, 25 contextual
absolute-import targets, and three exact same-class helper-return edges to two Agent source
definitions. Fourteen production CrewAI delegations resolve through an exact contextual import,
class export, immutable same-block instance, and direct Agent-returning method. Literal tools-list
role proof adds 444 inline-constructor, four context-manager, six absolute-import-binding, and four
contextual imported-callable target identities. One import-proven typed tool
parameter resolves through ten unanimous same-module `ApplyPatchTool` constructor call sites. Its
occurrence-qualified parameter component records all ten concrete target IDs without selecting one
runtime instance or propagating instance-specific approval policy. Fifteen
import-proven OpenAI Agents Python `ComputerTool` instances add ten exact agent links, including
three formerly ambiguous repeated bindings. Literal Agent tool lists add 755 role-proven tools: 181
callables, 100 constructor bindings, 444 inline constructors, four context-manager bindings, 21
Agent-as-tool adapters, and five absolute-import boundary tools. Of these, 526 are outside tests;
they add 30 capability edges and 812 exact Agent edges. Every adapter has an exact delegation edge
to its proven Agent receiver. Imported `from_settings` tool factories plus exact
`HostedMCPTool`, `LangchainTool`, and `Agent.as_tool()` adapters resolve the last six production
misses. The schema publishes 1,222 Python Agent→tool edges in total: all 623 non-test edges resolve,
while the 70 unresolved edges are confined to tests and conservative fixtures. Import-proven OpenAI
`function_tool(function)` assignments add 12 wrapper tools and 12 exact Agent edges; three explicitly
enable approval, all occur under tests, and none of their selected bodies contains a recognized
capability. Eight same-block function-factory edges remove the prior two repeated-binding targets;
the two schema-v83 resumed-state LocalShellTool references remain explicitly ambiguous. Cross-branch,
forward, untyped or call-site-inconsistent
parameters, conditional/transformed returns, external receivers, shadowed factories, lambdas, and
reassigned fixture cases stay unresolved. Two former CrewAI misses
were false package-import identities attached after a same-named function parameter or assignment shadowed the
import; their IDs remain withheld.
Capability, control, and taxonomy endpoints intentionally remain evidence observations.

Literal `tools=[...]` positions now establish tool role independently from capability semantics.
Identity still requires one exact local proof: an earlier same-block or immutable module-level
callable, a constructor imported once from a module with a tool namespace, a local class with that
exact imported tool base, or a direct context-manager binding with no intervening mutation. Inline
constructors receive occurrence-qualified IDs. This resolves all 22 formerly unresolved Agno
cookbook edges, all 11 CrewAI Examples named-tool gaps, seven Google ADK toolset gaps, and all nine
Marvin callable gaps while adding hundreds of previously absent inline toolkit observations. It does
not infer capabilities from constructor names. Reassignment, branch-only definitions, parameters,
ambiguous/rebound imports, arbitrary factories/builtins, and nested or reassigned context bindings
remain unresolved. Sixteen IR labels cover those local boundaries and pinned Agno, CrewAI, Google,
and Marvin paths. The newly exact Marvin reachability adds four pinned AV-FS001 reviews for dynamic
writes/deletion; the four rule labels distinguish this graph improvement from generic inventory.

Immutable top-level `from module import name` bindings add a second role-proof path. Four Google ADK
callables resolve through one contextual module path and one unique undecorated top-level export;
their bodies add three exact network-capability edges. Three production SDK tools whose source files
are outside the bounded checkout retain import-statement identities with no inferred capabilities.
Missing relative modules, duplicate or forward imports, module rebinding, and function/class-local
shadowing remain unresolved. Sixteen IR labels cover the local export/import boundary, six negative
forms, and all seven pinned Google ADK edges; one rule label proves cross-file AV-FS001 reachability.

Schema-v86 benchmark output measures native AI BOM endpoint resolution separately. AI BOM 1.2
resolves 3,929 endpoints by symbol ID, 700 by exact evidence location, and 21 by a unique display
name; 38 remain ambiguous and 58 unresolved. Before evidence-local and occurrence-qualified
resolution, raw name matching left many endpoints ambiguous. Exact locations resolve additional
capability/control endpoints. Unique occurrence IDs resolve repeated source agent/tool observations
and mark unsafe targets explicitly unresolved. Conservative lexical resolution removes further target
ambiguities. The 38 remaining ambiguities are agent, protocol, control, or tool endpoints without a unique local definition, so the
resolver does not use a nearby source location to invent an identity.

The Python frontend resolves unambiguous absolute imports rooted at the repository, `src/`, or
`python/`, plus relative modules that map to exactly one sibling package file. Schema v63 records 46
imported graph edges: 32 agent-to-tool edges and 14 agent-to-agent delegations. Twenty-five tool edges
are project-local CrewAI edges: a script-root-style
absolute import must map to exactly one file along the importer's ancestor chain, and that file must
export the exact decorated function or class-qualified method. The eight exact targets span the
Instagram, trip-planner, and landing-page projects. Existing exact paths include
CrewAI Examples' [markdown validator tool](https://github.com/crewAIInc/crewAI-examples/blob/da94a91e691e1cf5b3151416bb15b5b62729bea8/crews/markdown_validator/src/markdown_validator/crew.py#L3).
Two are newly resolved relative imports: the
[email flow draft tool](https://github.com/crewAIInc/crewAI-examples/blob/da94a91e691e1cf5b3151416bb15b5b62729bea8/flows/email_auto_responder_flow/src/email_auto_responder_flow/crews/email_filter_crew/email_filter_crew.py#L46)
and [CrewAI-LangGraph draft tool](https://github.com/crewAIInc/crewAI-examples/blob/da94a91e691e1cf5b3151416bb15b5b62729bea8/integrations/CrewAI-LangGraph/src/crew/agents.py#L44).
Four additional edges resolve Google ADK's undecorated discussion helpers through one contextual
module path and one exact top-level function export. Three other ADK tool imports whose SDK source
files are absent from the bounded checkout resolve only to their local import-boundary components;
they are not counted as cross-file import edges or assigned implementation capabilities.
Missing members, undecorated members, local rebinding, path escapes, and multiple ancestor
candidates remain unresolved rather than
falling back to name-only inference.

The 14 imported Agent-factory edges span Instagram post, meeting preparation, trip planner, and
starter-template crews. A class must be a unique undecorated, non-inherited export; its selected
method must be unique and directly return one import-proven Agent. At the caller, the imported class
must construct the receiver through the sole same-block mutation before the method result, and that
result must remain the sole mutation before Crew composition. Ambiguous ancestor paths, reimports,
missing methods, indirect/conditional returns, dynamic lookup, instance shadowing, and constructor,
receiver, or result rebinding remain unresolved. Four pinned-real and three local IR labels score the
boundary explicitly.

Resolved agent/tool components and relationships now carry frontend-and-module-qualified symbol IDs.
The import truth labels verify both target paths and target IDs, including CrewAI-LangGraph's
`py:integrations/CrewAI-LangGraph/src/crew/tools.py#tool:CreateDraftTool.create_draft` class method.
The same-name collision fixture proves that the approved and dangerous `run_command` definitions do
not share reachability or control coverage.

Python post-definition registration recovery resolves all 115 pinned Skyvern tools through direct
module-level `mcp.tool(...)(function)` applications. Each target has one immutable relative import
and one unique module-level definition. Ninety-three registrations are direct; 22 pass through
metadata-preserving forwarding wrappers, totaling 23 wrapper layers. A wrapper must carry an exact
`functools.wraps(function)` decorator and directly call `function(*args, **kwargs)` from its returned
callback; direct wrappers, decorator factories, and chains of at most four layers are supported.
These tools yield 22 exact capability edges—14 browser actions, seven browser-page evaluations, and
one filesystem mutation—rather than 115 findings. Only one of 36 Skyvern evaluations receives raw
tool-controlled script text; the remaining evaluator inventory is not promoted to a finding.
The filesystem edge exposes
[`resolved.parent.mkdir(...)`](https://github.com/Skyvern-AI/skyvern/blob/486c8975e9864a53037d4701b781f8619e698c40/skyvern/cli/mcp_tools/state.py#L89)
inside `skyvern_state_save`; equality with an allowed root does not prove that its parent remains
inside the root. Opaque and branch-only wrappers, nested registrations, rebound imports or
registrars, wildcard imports, and unrelated `.tool` methods remain unresolved.

Import-proven registry decorators recover another 56 Python tools: five functions and 51 classes,
with 35 observations from MetaGPT and 21 from Qwen-Agent. Thirty-four have resolved callable
entrypoints and yield 26 exact capability edges after imported-helper and urllib propagation. MetaGPT functions use their decorated body;
MetaGPT classes expose only direct methods named by a literal `include_functions=[...]`; Qwen classes
require a literal registered name and one direct `call` method. The class remains the tool identity,
so method capabilities do not create duplicate tool components. Exact module provenance and
statement-ordered alias rebinding prevent ordinary or rebound `register_tool` functions from being
promoted. Dynamic entrypoint lists and names remain unresolved rather than making every class method
reachable.

These edges expose four MetaGPT AV-FS001 reviews and two Qwen AV-NET001 reviews while preserving
near misses. A literal `Path(...).write_text(...)` is filesystem inventory but not a dynamic-path
review, and arbitrary object `.open(...)` methods are not filesystem capabilities. Qwen fixed-host
URLs remain inventory-only when a dynamic path or query is concatenated to a proven module constant
or formatted through an immutable `self` URL field.

Python imported network summaries add 14 corpus capabilities across ten unique top-level helpers;
all have exact tool edges and two remain dynamic. Qwen's `simple_doc_parser`
passes its tool-controlled URL to the imported `save_url_to_local_work_dir`, whose corresponding
formal reaches `requests.get`. Smolagents' `visualizer` performs a function-local self-import of
`encode_image`; its image-path parameter reaches another `requests.get`. Google ADK contributes 12
call sites across its issue-formatting and PR-triaging sample packages. Their package-qualified
absolute imports each have one importer-ancestor candidate. Schema v112 resolves seven of those
arguments to two immutable imported `https://api.github.com` constants; five formerly dynamic calls
become fixed-origin inventory, removing all Google ADK Python AV-NET001 reviews. The edge is attached at the
tool call site and retains the helper path, definition line, and network sink lines. Exact named
imports, unique top-level definitions, direct formal flow, and recognized clients are required;
multiple ancestor candidates are rejected;
module-object calls, nested helpers, reexports, transitive calls, local aliases, and any relevant
binding or client rebinding remain unresolved.

Across direct and summarized requests, imported literal-origin provenance covers nine capabilities
from four source bindings: seven Google ADK helper calls and two production Deep Agents PyPI
requests. Each records the source path and line. Exact literal exports, alias/local propagation, and
fixed-origin f-string prefixes are accepted; environment/composed values, duplicate or globally
mutated exports, consumer rebinding, local shadowing, module-qualified access, and ambiguous imports
remain unresolved. Ten focused IR labels pass at 3 TP / 7 TN.

Schema v114 also resolves Dify Agent's two production shell-layer compositions in
`api/clients/agent_backend/request_builder.py`. Each shell layer is default-disabled, conditionally
enabled by the request, paired with a runtime layer carrying the backend binding, and explicitly
dependent on that runtime layer. The resulting IR records two tool-to-shell-capability edges and two
shell-capability-to-runtime-control edges. The selected source does not establish the deployment
runtime's containment properties, so the sandbox boundary remains `external-unresolved`. Four
focused labels pass at 3 TP / 1 TN, including a missing-runtime negative.

An iterative class pass adds four more capabilities and exact tool edges, all dynamic and all in
Qwen-Agent. It first summarizes `SimpleDocParser.call` from its proven imported-function network
edge, then resolves direct construction in `WebExtractor` and immutable fields in `DocParser` and
`ExtractDocVocabulary`. `DocParser` becomes a summary on the next iteration, exposing `Retrieval` as
a two-hop path. The two callee summaries retain definition and prior network-edge lines. Only unique
registered classes with one literal entrypoint qualify; exact named imports, direct construction or
one constructor-only field, and caller argument flow are required. A unique literal key read by the
callee maps only that caller object field, so a fixed URL plus a dynamic sibling remains inventory.
Fixed inputs retain an inventory edge. Multiple assignments, deletion, `setattr`, shadowed/rebound constructors, duplicate classes,
module-qualified calls, inheritance, and more than four iterations remain unresolved.

The TypeScript frontend now reads only balanced top-level entries from literal Agent tool arrays. It
resolves OpenAI `tool`, `toolNamespace`, built-in tool factories, inline/assigned `asTool` adapters,
and Cline `createTool`. Import-aware discovery now also resolves generic/Mastra object-property
tools plus MCP `registerTool` names and callback spans. Schema v38 records 27 Mastra factory tools,
264 MCP registrations, 70 object-property tools (the factory/property categories overlap), and ten
exact registration-to-capability edges. Four of those edges come from bounded same-file network
helper summaries: three Mastra static methods and one MCP Servers free function. Schema v38 also
records one imported TypeScript path-boundary control edge. The full sample
contains 100 structure-backed agent edges: 14 delegations, 82 tool edges, and four other
agent-composition edges. All tool targets resolve to observed components. The prior token heuristic could
turn words inside callbacks, string literals, and nested options into spurious tool edges. Relative
named imports still apply the conservative `.js`-specifier-to-source rule; this snapshot has no
qualifying cross-file Agent tool edge, so that part remains regression-validated only.

The approval-policy resolver attaches exact controls to inline OpenAI Agents JS tools, including the
pinned [local shell example](https://github.com/openai/openai-agents-js/blob/0b944370c6fe019ac5b08364ca013826cd7d0668/examples/tools/local-shell.ts#L104).
Literal true creates a control; false and the SDK default remain disabled, while callback results are
unresolved. Hosted container shell factories are identified separately and do not trigger the local
approval review.
OpenAI Agents JS helper-parameter HITL decisions now resolve only through non-exported same-file
async helpers whose first parameter is typed as the exact SDK `Agent` import and whose body proves
`run(agentParam, ...) -> result.state -> state.approve/reject`. The pinned
[`computer-use-hitl.ts` helper](https://github.com/openai/openai-agents-js/blob/0b944370c6fe019ac5b08364ca013826cd7d0668/examples/tools/computer-use-hitl.ts#L201-L220)
now yields separate controls for its two `runWithHitl(agent, ...)` call sites, preserving
`AUTO_APPROVE_HITL` approval-bypass metadata and template custom-rejection-message provenance.
The same helper proof now also captures `run(agentParam, state)` resume continuity, producing
distinct `conversation-continuity` controls and configured-by edges for each lexical call site.

For Python, files importing the OpenAI Agents SDK now inventory `ShellTool`, `ApplyPatchTool`,
`ComputerTool`, and `CustomTool` instances with line-scoped identities. `ComputerTool` produces a
local computer-control capability and records its optional `on_safety_check` callback separately
from generic approval policy. All 15 observed instances are local, two configure the callback, and
only the pinned SDK example instance is outside test paths. A literal `needs_approval=True` with no
automatic handler creates an exact tool-to-control edge; literal false and the SDK default are recorded as
disabled, while callbacks and a configured `on_approval` handler remain unresolved. The pinned SDK's
[shell HITL example](https://github.com/openai/openai-agents-python/blob/17ba331bb0ad1622a4ff4ecdc914c77118075dad/examples/tools/shell_human_in_the_loop.py#L117)
is the real positive: `ShellTool@117` is governed by the literal policy at line 119. Requiring an
`agents` import prevents unrelated application classes with the same constructor names from being
promoted into Agent IR.

## AV-APPROVAL001 — enabled approval-bypass path

The rule reports explicit enabled auto-approval/skip-confirmation settings and environment-backed
approval branches. Environment handling is deliberately flow-sensitive within a narrow boundary: an
approval-specific variable such as `SHELL_AUTO_APPROVE` must be compared with an explicit enabled
value, and the governed branch must return true directly without an intervening conditional. Python
tracks module flags into functions and keeps local flags lexically scoped. TypeScript supports inline
`process.env` comparisons and module-level flag assignments; comments and strings remain masked.

The full benchmark now reports 14 default-scope reviews. Eight newly resolved paths are official SDK
examples: OpenAI Agents Python's
[shell prompt bypass](https://github.com/openai/openai-agents-python/blob/17ba331bb0ad1622a4ff4ecdc914c77118075dad/examples/tools/shell.py#L80),
its [apply-patch approval short circuit](https://github.com/openai/openai-agents-python/blob/17ba331bb0ad1622a4ff4ecdc914c77118075dad/examples/tools/apply_patch.py#L83),
and OpenAI Agents JS examples for
[hosted MCP approval](https://github.com/openai/openai-agents-js/blob/0b944370c6fe019ac5b08364ca013826cd7d0668/examples/mcp/hosted-mcp-on-approval.ts#L6),
[computer use](https://github.com/openai/openai-agents-js/blob/0b944370c6fe019ac5b08364ca013826cd7d0668/examples/tools/computer-use-hitl.ts#L62),
[local shell](https://github.com/openai/openai-agents-js/blob/0b944370c6fe019ac5b08364ca013826cd7d0668/examples/tools/local-shell.ts#L73),
and [apply patch](https://github.com/openai/openai-agents-js/blob/0b944370c6fe019ac5b08364ca013826cd7d0668/examples/tools/apply-patch.ts#L77),
plus two sibling HITL examples using the same flag. These are intentional examples, not vulnerability
claims; `review` communicates that deployments should decide whether the bypass is acceptable.

Regression negatives reject status variables such as `AUTO_APPROVED_WARNING`, disabled values,
non-approval methods, and branches that add a second safety condition before returning. Same-class
Python attributes are resolved only when an approval-specific method has an unconditional early
return; inheritance, helper-object propagation, and callback results remain unresolved. The rule has
14 positive and 15 negative exact labels. Semantic Kernel's sampling opt-in is excluded here because
`AV-MCP004` explains its distinct server-to-model authority.

## AV-APPROVAL002 — reachable local shell with approval disabled or unavailable

The enabled rule is intentionally narrower than a general “missing approval” claim. It requires a
directly reachable local shell tool and either an explicit false, a documented disabled default, an
exact constructor with no approval parameter, or a complete executor proof with no per-action
decision branch. It reports a high-confidence `review`, not a generic lexical absence finding.

Schema v63 separately inventories OpenAI Agents Python's MCP approval default without widening the
rule. In the pinned sandbox-agent example, omitted `MCPServerStdio.require_approval` flows through the
SDK's `None → False` normalization and missing-name false fallback into each generated
`FunctionTool`, and the exact server binding reaches `SandboxAgent.mcp_servers`. The IR emits one
agent→server edge and one disabled-default policy setting. No AV-APPROVAL002 review is emitted because
the downstream reference-policy tools are not a proven destructive capability. Two negative rule
labels, two positive/one negative IR labels, and six mutations preserve that boundary.
Hosted shell environments, callback policies, automatic handlers, unresolved environments, and test
paths are excluded.

Schema v83 adds five exact `LocalShellTool` assets in pinned OpenAI SDK tests. They produce five
shell-capability edges and four resolved Agent links, all with
`approval_source: sdk-no-approval-parameter`. Because default scans exclude test findings, they do
not change the two-site corpus finding count. Three local positives and two exact-import guard
negatives extend the rule matrix; 11 positive and four negative IR labels independently pin the
asset, capability, and relationship behavior.

The two original sites remain in the pinned SDK's
[local shell skill example](https://github.com/openai/openai-agents-python/blob/17ba331bb0ad1622a4ff4ecdc914c77118075dad/examples/tools/local_shell_skill.py#L29).
The paired real negative is the
[HITL shell example](https://github.com/openai/openai-agents-python/blob/17ba331bb0ad1622a4ff4ecdc914c77118075dad/examples/tools/shell_human_in_the_loop.py#L117),
which creates a resolved human-approval edge. OpenAI Agents JS contributes real approved-local and
hosted-shell negatives.

Schema v117 adds one Trae Agent site. The proof requires the literal `TraeAgentConfig` Bash default,
registry binding, `TraeAgent → BaseAgent` construction, direct `ToolExecutor` dispatch, and
default-local executor selection. The executor class is rejected if an approval, confirmation, or
HITL branch appears. The rule now has eight positive and nine negative exact labels.

Schema v119 adds one Letta Code site. The 15-source proof requires the default Bash registration,
declared approval requirement, `unrestricted` default, settings/CLI deny and always-ask precedence before the mode
override, classifier and WebSocket approved-decision mapping, approved batch execution, and the
explicit local shell sink. Ordinary calls are therefore allowed without a prompt, but explicit deny,
always-ask, and `AskUserQuestion` interactivity remain real controls. The full benchmark now reports
four sites across three repositories, and the rule matrix reaches 10 TP, 11 TN, 0 FP, and 0 FN.

## AV-APPROVAL003 — environment-backed approval callback reaches a privileged tool

Schema v63 resolves approval callbacks independently from the presence or absence of an SDK policy.
It requires a reachable OpenAI built-in local shell or apply-patch tool, a configured approval
handler, a unique same-file helper chain, and an approval-specific environment comparison whose
immediate branch returns true. The IR records the environment names on the tool and adds a
`configured-by control-setting:auto-approval` edge with `same-file-transitive-callback` resolution.

Three default-scope findings qualify: OpenAI Agents Python's
[local shell](https://github.com/openai/openai-agents-python/blob/17ba331bb0ad1622a4ff4ecdc914c77118075dad/examples/tools/shell.py#L117),
OpenAI Agents JS's
[local shell](https://github.com/openai/openai-agents-js/blob/0b944370c6fe019ac5b08364ca013826cd7d0668/examples/tools/local-shell.ts#L104),
and its
[apply-patch tool](https://github.com/openai/openai-agents-js/blob/0b944370c6fe019ac5b08364ca013826cd7d0668/examples/tools/apply-patch.ts#L121).
The Python path includes one named wrapper before the environment-backed prompt; both TypeScript
paths use inline handlers that call a summarized helper. Six negatives preserve safe callbacks,
unused helpers, hosted/container shells, and the manual Python HITL example. The rule matrix is 3 TP,
6 TN, 0 FP, and 0 FN; the corresponding IR matrix is 6 TP, 2 TN, 0 FP, and 0 FN.

## AV-APPROVAL004 — writable local MCP filesystem tools inherit disabled approval

Schema v66 verifies the OpenAI Agents JS composition across its pinned SDK sources: configured MCP
servers are attached to the Agent, discovered tools are converted through `tool(...)` without a
`needsApproval` override, and the generic tool factory normalizes omission to `false`. Three
reachable filesystem-package examples qualify: the docs `fullCommand` form, the tools docs form,
and the `process.execPath` plus import-proven `createRequire.resolve` form. Each produces an exact
agent→MCP-server→filesystem path and a high-confidence review.

The static-filter example is the real counterexample: its literal allowlist contains only
`read_file` and `list_directory`, so the capability records `write_access: false` and a
`mcp-tool-filter` control. An unbound writable server is inventory-only. The rule matrix is 6 TP,
3 TN, 0 FP, and 0 FN; seven IR labels cover local and real edges, the filter control, and a constructor
provenance negative.

## AV-APPROVAL005 — Agno filesystem mutations lack confirmation coverage

Schema v67 verifies Agno's pinned `MCPTools` propagation: an omitted
`requires_confirmation_tools` value becomes an empty list, and each discovered function receives
confirmation only when its exact name is in that list. Both direct command construction and the
exactly nested `StdioServerParameters` → `stdio_client` → `ClientSession` composition resolve into an
Agent. The full-corpus benchmark contains three such filesystem servers: two keep the known mutation
surface without confirmation and raise high-confidence reviews, while one exposes only a literal
read-only include list.

Local cases distinguish the disabled default, incomplete static coverage,
complete mutation coverage, dynamic policy, read-only filtering, unbound tools, and wrong imports.
Complete static coverage adds a human-approval control; dynamic policy remains unresolved. The rule
matrix is 5 TP, 4 TN, 0 FP, and 0 FN. The corresponding IR matrix is 9 TP, 1 TN, 0 FP, and 0 FN.

## AV-APPROVAL006 — OpenHands risk analysis leaves confirmation disabled

Schema v116 verifies exact OpenHands SDK composition from built-in `TerminalTool` and
`FileEditorTool` instances through a static `Agent.tools` list to the same `Conversation`. Installing
an `LLMSecurityAnalyzer` establishes action-risk analysis, but the SDK's `NeverConfirm` default still
leaves confirmation mode inactive. The pinned
[MCP integration example](https://github.com/OpenHands/software-agent-sdk/blob/1de2e6d1bfcf70c7c3d4eb13616811943f33dd75/examples/01_standalone_sdk/07_mcp_integration.py#L36)
is the real positive: its analyzer governs reachable terminal and file-editor actions while no
confirmation policy is installed. The review is anchored once per conversation, and the reachable
file editor independently raises AV-FS001 because its absolute path argument is not constrained by
`workspace_root`.

The paired
[security-analyzer example](https://github.com/OpenHands/software-agent-sdk/blob/1de2e6d1bfcf70c7c3d4eb13616811943f33dd75/examples/01_standalone_sdk/16_llm_security_analyzer.py#L113)
is the real negative: it installs both the analyzer and `ConfirmRisky`, producing exact
action-risk-analysis and human-approval controls. Local negatives reject dynamic policies, rebound
factories, near-package imports, forward setters, and one Agent shared by multiple conversations. The rule matrix is
2 TP, 4 TN, 0 FP, and 0 FN. Remediation is to install a static confirmation policy such as
`ConfirmRisky` on the same conversation; risk classification alone is not an approval gate.

## AV-APPROVAL007 — raw command prefix crosses an auto-approval token boundary

Schema v118 requires an exact eight-source Roo Code composition: native `execute_command` schema,
registry and model-tool builder, Task approval routing, assistant-message dispatch, command executor,
auto-approval router, and command-decision helper. The graph proves Agent→tool→shell execution plus
the governing prompt-default setting and command allowlist. Auto-approval still requires both the
global option and `alwaysAllowExecute`; denylist precedence, chain parsing, and dangerous-substitution
rejection remain explicit controls.

The specialized review isolates the helper's raw
[`trimmedCommand.startsWith(lowerPrefix)`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/auto-approval/commands.ts#L106)
semantics, which do not require the following character to be an executable or argument token
boundary. The local safe case accepts only equality or prefix followed by a space; near-package and
incomplete compositions remain absent. The rule matrix is 2 TP, 2 TN, 0 FP, and 0 FN; the exact
composition has 18 positive and two negative IR labels. Remediation is to parse the command and
compare executable/argument tokens, or at minimum require equality or a deliberate token boundary.

## AV-APPROVAL008 — plan mode discards shell approval escalation

Schema v120 requires the exact Continue CLI composition across six production sources: plan-mode
defaults, absolute mode installation, static/dynamic precedence, runtime approval dispatch, Bash
tool and login-shell sink, and the ordered terminal evaluator. Normal mode remains the default and
configures Bash as `ask`. Selected plan mode excludes Edit/MultiEdit/Write but sets Bash to `allow`.
The evaluator still returns `disabled` for critical commands, `allowedWithPermission` for high-risk
and unknown commands, and `allowedWithoutPermission` for safe commands.

The review is anchored at the
[`permission: basePermission`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/cli/src/permissions/permissionChecker.ts#L171)
return: only `disabled` overrides the static allow, so the runtime approves high-risk and unknown
commands without invoking the user-permission path. Critical-command blocking remains effective and
is recorded as a compensating control. The rule matrix is 2 TP, 2 TN, 0 FP, and 0 FN; the exact
composition has 20 positive and two negative IR labels. Remediation is to retain a more restrictive
dynamic result, or replace plan-mode Bash with a parsed read-only command allowlist.

## AV-APPROVAL009 — plan mode wildcard-allows unclassified MCP tools

Schema v121 requires a separate exact Continue CLI composition across six production sources:
plan/normal wildcard policy, absolute plan-mode installation, first-match permission resolution,
runtime allow/ask dispatch, discovered-tool adaptation, and MCP discovery/invocation. Normal mode
remains the default and asks for unknown tools. Selected plan mode excludes the three built-in write
tools but ends with a wildcard allow for MCP tools.

Every server-discovered schema is made model-visible while the adapter records `readonly: undefined`.
The allow branch returns approved without invoking the user-permission path, then the adapter reaches
[`client.callTool`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/cli/src/services/MCPService.ts#L184-L198).
The review does not infer that every MCP tool mutates state; it reports that the host has no locally
enforced effect classification before auto-execution in the selected read-oriented mode. The rule
matrix is 2 TP, 2 TN, 0 FP, and 0 FN; the exact composition has 22 positive and two negative IR
labels. Remediation is to ask for unclassified MCP calls and auto-allow only a locally reviewed
read-only allowlist.

## AV-APPROVAL010 — spawned sub-agent loses approval state

Schema v123 requires two exact Cline production compositions. The VS Code path spans nine sources:
the root policy builder and live session wiring, host callback wiring, SDK fail-open policy dispatch,
Act preset and spawn default, local spawn registration, child tool construction, and the shared spawn
factory. Root `editor` and `run_commands` are explicitly gated, but `spawn_agent` is absent and the
SDK auto-approves unlisted tools. The CLI sandbox path spans ten sources: startup policy, interactive
safe-tool policy, terminal approval callback, `runAgent` capability/policy wiring, CLI core local
backend routing, SDK policy dispatch, spawn default, local host registration, child tool
construction, and the shared spawn factory.

The review is anchored at
[`createSpawnAgentTool({`](https://github.com/cline/cline/blob/80b3b0348e694bafc48e3dcd70154de3cf4289d9/sdk/packages/core/src/runtime/host/local/spawn-tool.ts#L149):
the wrapper constructs child tools from the Act preset but omits both `toolPolicies` and
`requestToolApproval`, even though the factory accepts and forwards those fields. The rule matrix is
4 TP, 4 TN, 0 FP, and 0 FN; the exact compositions have 48 positive and four negative IR labels.
Remediation is to gate the parent spawn operation and propagate the effective policy/callback into
every delegated agent, failing closed when propagation is unavailable.

## AV-MCP004 — MCP server model sampling is auto-approved

Schema v68 verifies Semantic Kernel's bidirectional MCP composition. The pinned SDK registers its
sampling callback on `ClientSession`, denies requests when neither consent nor auto-approval exists,
gives a configured consent callback precedence, maps the server's system prompt, messages, model
hint, temperature, and token limit into a chat completion, and returns that completion to the
server. Exact plugin and `ChatCompletionAgent` imports plus direct async-context binding produce the
Agent→MCP-server→model-sampling path.

Seven pinned plugin instances qualify for inventory. Six omit the opt-in and receive a
`mcp-sampling-consent` control representing the fail-closed default. The release-notes sample at
`python/samples/concepts/mcp/agent_with_mcp_sampling.py:55` explicitly enables
`sampling_auto_approve` and raises the one high-confidence review. Callback-controlled and dynamic
policies remain unresolved, while disconnected plugins, wrong imports, and a changed SDK default
withhold the path. The rule matrix is 2 TP, 7 TN, 0 FP, and 0 FN; the IR matrix is 9 TP, 2 TN, 0 FP,
and 0 FN.

## AV-MCP005 — MCP sampling is fulfilled without a proven user decision

Schema v69 verifies the raw client registration seam in both supported frontends. Python requires an
exact `mcp.ClientSession`, a same-scope named async callback, and an exact `mcp.types` sampling result.
TypeScript requires an exact `@modelcontextprotocol/client` `Client` with a literal sampling
capability, a proven receiver, and a balanced inline `sampling/createMessage` handler returning
`role`, `content`, and `model`. The IR records the
MCP-protocol→model-sampling path, server input authority, response destination, fulfilment target,
and configured policy.

Schema v71 additionally resolves PydanticAI's exact `MCPToolset(sampling_model=...)` adapter, where
the SDK generates the sampling callback. A null model, a simultaneous non-null custom handler,
expanded keyword arguments, rebound constructors, conditional imports, and unrelated imports withhold the path; protocol
availability remains explicitly SDK-session-dependent.

Ten pinned handlers qualify: five Python and five TypeScript, including six test-only automatic
handlers. Nine automatically return results; the three default-scope instances raise reviews across
two repositories. The TypeScript CLI host is the governed counterexample: it displays the full system
prompt and messages, caps the server's token request, awaits an explicit decision, throws on
rejection, and only then calls its provider. Direct Python rejection, unresolved callbacks, and a
too-late TypeScript confirmation are separately regression-tested. A missing capability, unrelated imports, and a disconnected TypeScript receiver withhold
the path. The rule matrix is 7 TP, 15 TN, 0 FP, and 0 FN; the IR matrix is 17 TP, 7 TN, 0 FP, and 0 FN.

## AV-MCP006 — MCP elicitation is accepted without a proven user decision

Schema v70 treats elicitation as a distinct server-to-client authority. Python requires an exact
`mcp.ClientSession`, a same-scope named async callback, and a literal `mcp.types.ElicitResult` action.
TypeScript requires an exact `@modelcontextprotocol/client` `Client`, a literal form/URL capability,
a proven receiver, and a balanced inline `elicitation/create` arrow handler returning literal action
objects. The IR records the protocol→user-elicitation path, advertised modes, server input authority,
response destination, acceptance policy, and consent control. The
[official MCP elicitation specification](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)
defines `accept` as user consent and requires explicit consent plus clear target domain/host display
before URL-mode navigation. The
[draft safe-URL guidance](https://modelcontextprotocol.io/specification/draft/client/elicitation)
adds a stricter requirement to show the full URL before consent; `AV-MCP007` measures that boundary.

Schema v71 additionally resolves FastMCP's exact `Client(elicitation_handler=...)` adapter. Ordinary
returned data is implicit `accept`, while explicit `ElicitResult` preserves accept, decline, and
cancel. Rebound callbacks or response factories, unknown returns, and unrelated imports remain
unresolved or absent. This follows the
[official FastMCP elicitation contract](https://gofastmcp.com/clients/elicitation).

Fifteen pinned handlers qualify: three Python and 12 TypeScript. Ten can return `accept`, including
seven test-only handlers; the three default-scope automatic acceptances raise reviews in the
TypeScript SDK. Two test handlers decline only. The SDK CLI host is human-confirmed through direct URL
confirmation plus a unique imported form collector that gathers input and preserves decline/cancel.
The Microsoft Python tutorial independently prompts and branches on explicit user choices. FastMCP's
production CLI is also human-confirmed, but its proven disclosure is message-only. Wrong
imports, disconnected or reassigned receivers, missing capabilities, unreturned or nested action
objects, shadowing parameters, and named external callbacks withhold the path. The rule matrix is 7
TP, 24 TN, 0 FP, and 0 FN; the IR matrix is 29 TP, 4 TN, 0 FP, and 0 FN.

## AV-MCP007 — MCP URL elicitation hides the full target URL

Schema v72 records `url_disclosure` independently from human consent. Exact Python display/prompt
calls must receive the complete params object or `.url`; TypeScript UI calls must receive
`request.params.url`. Message and form-schema rendering do not satisfy the URL-mode requirement.
The rule applies only to human-confirmed URL-capable handlers, so automatic acceptance remains the
single responsibility of `AV-MCP006`.

Two default-scope clients qualify: the Microsoft tutorial and FastMCP CLI both ask for a decision but
do not show the target URL. The TypeScript SDK host is the negative control: it displays the full URL,
rejects unsafe non-HTTPS/non-loopback destinations, and asks before proceeding. The rule matrix is 4
TP, 3 TN, 0 FP, and 0 FN; seven additional positive IR labels pin full versus missing disclosure.
All 730 cross-rule labels pass (337 positives and 393 negatives).

During validation, import-aware shell resolution rejected Cline's `RegExp.exec()` calls as unrelated
to `child_process.exec()`. Structure-aware Cline `createTool` parsing then exposed the distinct real
path where agent input reaches
[`Bun.spawn(["sh", "-c", input.command])`](https://github.com/cline/cline/blob/80b3b0348e694bafc48e3dcd70154de3cf4289d9/apps/examples/cli-agent/src/index.ts#L19).
Truthy approval-bypass matching plus test-scope filtering reduced Cline approval candidates from 41
to six after the additional SDK policy sources were selected; those remain review results rather
than confirmed vulnerabilities.

Expanding the truth set exposed two additional false-positive families. Literal TypeScript commands
were incorrectly classified as dynamic; resolving complete string literals removed five corpus
findings while preserving interpolated templates. Broad approval-name matching confused warning-state
and version-check flags with human approval; requiring approval-specific names removed six review
candidates. Corpus totals are now 25 `AV-EXEC001` findings, 15 `AV-APPROVAL001` reviews, one
`AV-APPROVAL007` raw-prefix review, one `AV-APPROVAL008` plan-mode precedence review, one
`AV-APPROVAL009` plan-mode MCP-classification review, two `AV-APPROVAL010` sub-agent propagation
reviews, one specialized `AV-MCP004` review, three generic `AV-MCP005`
sampling-consent reviews, and three
`AV-MCP006` elicitation-consent reviews, plus two `AV-MCP007` full-URL-disclosure reviews.
The dependency closure also exposes CAMEL's production `func_string_to_callable(code)` helper, whose
parameter reaches `exec`. Browser-aware evaluation adds one more exact path: Skyvern's registered
[`skyvern_evaluate`](https://github.com/Skyvern-AI/skyvern/blob/486c8975e9864a53037d4701b781f8619e698c40/skyvern/cli/mcp_tools/browser.py#L2458)
passes its tool parameter to Playwright `page.evaluate`. Across 93 inventoried browser-page
evaluations, this is the only production call with direct tool-parameter flow, raising `AV-EXEC002`
to 51 across 15 repositories. The original `.evaluate(...)` subset remains 41 proven of 86 under
schema v90: two exact Playwright `Page` parameters in
SWE-agent, five results of Skyvern's exact imported `get_page` factory, 15 exact typed class
attributes across CAMEL, LaVague, and MetaGPT, and 13 exact constructor-field/alias uses in Devika.
One exact Skyvern locator derivation, one OpenAI Agents Python property, three straight-line local
page uses in Aider and Skyvern, and Browser-Use's exact module-page Locator complete those proofs.
Schema v91 adds four alternate API shapes and seven Skyvern test observations: three locally
constructed-page receivers are proven and four remain unresolved. Overall receiver coverage is 44
of 93, with 49 unresolved. Schema v92 proves those four remaining alternate-API test receivers
through exact local async-context-manager page yields, bringing current coverage to 48 of 93 and 45
unresolved. Schema v93 proves two MetaGPT production evaluators through exact Literal-bounded local
browser selection and unanimous private same-class helper calls, bringing current coverage to 50 of
93 and 43 unresolved. Schema v94 proves three Devika lifecycle-field receivers, bringing current
coverage to 53 of 93 and 40 unresolved. Schema v95 proves three Skyvern same-module helper-body
evaluators, bringing current coverage to 56 of 93 and 37 unresolved. Schema v96 proves 12 CAMEL
branching-lifecycle field receivers, bringing current coverage to 68 of 93 and 25 unresolved.
Schema v97 proves Skyvern's imported wrapper scope, schema v98 proves its imported context field,
and schema v99 proves its imported protocol method return through an immutable captured parameter.
Current coverage is 71 of 93 with 22 unresolved. Six
chained calls are inventoried. Dynamic calls with only browser-import context are withheld: local
regressions cover an ordinary calculator's `.evaluate(...)`, a reassigned typed
page, one immutable typed-page alias, conflicting class types, and ambiguous/rebound/near type-only
imports. Skyvern's normalized numeric direct and locator scroll JavaScript at lines 1664 and 1662
remain real negatives. API-specific regressions also pin dynamic selector/fixed-expression
discrimination, the `expression=` keyword, an ordinary object's `evaluate_handle`, branch and
ordinary-object yields, reassigned context targets, mixed helper calls, mutable and escaped
bound-method aliases, and invalid selector literals. Registry, receiver, and evaluator fixtures
bring the rule to 38 positive and 124 negative exact labels.

## AV-MCP002 — dynamic MCP forwarding

The rule requires an MCP import plus a non-literal tool name. A fixed tool name is the negative
regression. The full benchmark reports 49 default-scope forwarding sites across 23 repositories.
Hand-reviewed pinned examples include:

- [CrewAI client](https://github.com/crewAIInc/crewAI/blob/456c67d7c27923ed3c3dca202c6f56651d8e6063/lib/crewai/src/crewai/mcp/client.py#L599)
- [browser-use client](https://github.com/browser-use/browser-use/blob/85ddbfedf609166b2d2c76c3d80506649fee82a9/browser_use/mcp/client.py#L324)
- [Semantic Kernel connector](https://github.com/microsoft/semantic-kernel/blob/b39d95a34435f4c1d55dd00c86120ce118d847e1/python/semantic_kernel/connectors/mcp.py#L618)
- [ChatDev tool manager](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/runtime/node/agent/tool/tool_manager.py#L291)

These are legitimate protocol boundaries in framework code and are therefore `review` results. A
later policy-resolution pass will suppress sites governed by a resolved allowlist rather than
claiming that the forwarding operation itself is unsafe.
Six newly selected OpenAI Agents Python SDK calls account for the corpus increase; the retry wrapper
at `src/agents/mcp/server.py:1538` is pinned as a real dynamic-forwarding positive.

That policy pass now handles a same-function `not in` guard followed by `raise`/`return`. Guards are
applied in statement order: a rejection after the forwarding call does not govern the earlier action.
It resolves
and suppresses CAMEL's [registered-tool guard](https://github.com/camel-ai/camel/blob/473388d36390b22e0df31e25b7b2d50db55310d2/camel/utils/mcp_client.py#L1054)
before the dynamic call, while retaining the forwarding capability and a `tool-allowlist` control edge.

The resolver also recognizes an uncaught, statement-ordered lookup through an internal `self.*tool*`
registry. The MCP Python SDK's
[`SessionGroup.call_tool`](https://github.com/modelcontextprotocol/python-sdk/blob/57394b0548d1e2dc2dce8d67d84985769df3b8bb/src/mcp/client/session_group.py#L239-L241)
indexes both the tool-to-session map and the registered tool map before forwarding. An unknown name
therefore raises before the call. AgentVerify attaches a `tool-registry` edge with the lookup
location and explicitly marks its policy effect as `routing-only`. The review remains because this
registry aggregates every server-advertised tool and is not an authorization allowlist. A
caller-owned mapping, a lookup after the call, or a lookup hidden inside a caught fallback does not
qualify even as routing coverage.

The 49-site audit also found five forwarding calls in four repositories where the name comes from a
single constructor assignment with no class-local reassignment. CrewAI exposes the
stored name through a property, Trae through a zero-argument getter, Lagent directly through stored
metadata, and AgentScope has two calls over one stored tool. AgentVerify attaches a
`fixed-tool-binding` edge with `policy_effect: binds-tool-source-per-instance`. A second assignment,
deletion, or augmented assignment invalidates the proof. These five reviews remain: anchoring the
name to one stored source removes a direct call-parameter selector, but it does not prove that the
source object is immutable, the discovered tool set is an authorization allowlist, or arguments are
constrained.

Five more calls use captured parameters in callbacks that escape their factory: browser-use registers
three wrappers through its action registry, while ArcadeAI returns two LangChain tool callbacks. They
carry `binding_scope: closure` and `policy_effect: binds-tool-source-per-closure`. Merely nesting a
function does not qualify: the MCP Python SDK and FastMCP retry helpers are invoked within the same
caller-selected operation, so their names remain uncontrolled. A rebound parameter is likewise
unresolved. Schema v38 publishes the resulting fixed-binding split as five instance edges and five
closure edges; all ten remain AV-MCP002 reviews.

FastMCP contributes a second `tool-registry` edge through a same-class method summary. Its middleware
branch recursively calls `self.call_tool(..., run_middleware=False)`; the summarized callee resolves
the name through `get_tool`, rejects `None`, and only then invokes the tool. The edge records
`required_arguments: {run_middleware: false}` rather than assuming that the earlier recursive return
was bypassed. A local fallback fixture proves that substituting a default tool is not a rejecting
guard.

The bounded dependency closure now selects the MCP Python SDK's `tools` package reexport and
`ToolManager` body. `MCPServer.__init__` binds `self._tool_manager` once to that imported class;
`ToolManager.call_tool` resolves `get_tool(name)` and raises before execution when absent. This adds
the third `tool-registry` edge with `summary: imported-class-method`. Local negatives cover a mutable
manager attribute, a fallback manager, and a rebound imported constructor. Schema v38 distinguishes
one same-function lookup, one same-class method summary, and one imported-class summary; all three
retain their AV-MCP002 reviews as routing-only discovery controls rather than authorization
allowlists.

## AV-MCP003 — automatic unpinned MCP package launch

Schema v64 resolves 24 literal MCP package launchers: 19 unpinned, three floating, and two exact.
Twenty-two use an automatic installation mode; tests remain inventoried but excluded from findings.
The rule reports 16 default-scope launchers across four repositories: one Marvin `uvx` server, nine
Qwen-Agent `uvx`/`npx -y` configurations, three Agno launchers (including two `@latest` references),
and three CAMEL configurations. These are supply-chain review points, not claims that the referenced
packages are malicious.

The resolver requires standard MCP structure: an MCP-module-bound Python constructor, a literal
nested Python `mcpServers` dictionary, or MCP JSON. `uvx` is automatic by definition; `npx` requires
literal `-y`/`--yes`. Exact npm `package@version` and Python `package==version` references are
inventory negatives. The same pinned OpenHands example supplies both real exact-version negatives,
while CAMEL supplies prompt/cache-only `npx` negatives. Dynamic package selection,
`npx --no-install`, arbitrary package scripts, lookalike constructors, and unsupported launcher options
remain negative or unresolved. Remediation is to pin a reviewed exact package version and update it
through a controlled dependency-review process.

## AV-FS001 — dynamic writable tool path

The rule requires a writable tool-input-derived path inside a resolved tool; ordinary application
writes and fixed/configured tool paths do not trigger it. The full benchmark reports 39 default-scope sites across 11
repositories. Four newly reachable sites come from immutable module-level callables passed literally
to Marvin Agents: writes in `examples/deepseek_chat.py:74`, `examples/hello_agent.py:7`, and
`examples/provider_specific/aimlapi/run_agent.py:30`, plus the delete in
`examples/hello_agent.py:15`. A hand-reviewed case is ArcadeAI's
[local-filesystem MCP `write_file`](https://github.com/ArcadeAI/arcade-ai/blob/597debaa1593b54172061ce36a414cc29aa8fc6a/examples/mcp_servers/local_filesystem/src/local_filesystem/tools.py#L154),
which resolves a caller-provided path before writing. No workspace-root constraint is visible in the
tool function, but the result remains `review` because enclosing server policy is unresolved.
Trae Agent contributes one exact default-tool review: `TextEditorTool` requires an absolute `path`,
but its validator checks only absoluteness, existence, and file/directory state before mutation. It
does not resolve or compare the path with the configured working directory, so absolute paths outside
the workspace remain reachable on the default local executor.
Letta Code contributes one exact default Write-tool review. Its required `file_path` is expanded and
passed to `writeUtf8Text`; the pinned implementation retains cross-agent and requested-workspace
guards, but the default graph proves no general workspace-root boundary. Those compensating controls
remain explicit and the review does not claim arbitrary writes bypass every configured sandbox.
New TypeScript registration edges expose Mastra's
[`writeFile` tool adapter](https://github.com/mastra-ai/mastra/blob/1da5fb00e141b78c2148b21ee085ec24112cf2a5/packages/agent-builder/src/defaults.ts#L457-L475)
and the MCP filesystem server's
[`create_directory` callback](https://github.com/modelcontextprotocol/servers/blob/599dafc1054550a6eeb87a6545c1e1b03b3ca827/src/filesystem/index.ts#L412-L429).
For the latter, an unambiguous import chain resolves `validatePath` to a normalized,
separator-aware roots predicate; the callback rejects paths outside configured roots before `mkdir`.
AgentVerify emits a `path-boundary` control edge, but retains the review because the CLI/MCP-provided
roots are not statically known and could be broad. A literal narrow-root fixture demonstrates the
suppressible case. A helper name alone, missing imports, or a check after the write remain
unresolved. Exact string-prefix checks are classified separately by AV-FS002 and never satisfy this
boundary.

Post-definition registration recovery adds Skyvern's
[`skyvern_state_save`](https://github.com/Skyvern-AI/skyvern/blob/486c8975e9864a53037d4701b781f8619e698c40/skyvern/cli/mcp_tools/state.py#L71)
to exact tool reachability. Its line-89 parent-directory creation remains a review because
`_validate_state_path` permits the resolved candidate to equal an allowed root; that does not prove
the candidate's parent remains within the boundary.

Registry-decorator recovery adds four MetaGPT sites: the Editor's parent creation and file write plus
GPT-v Generator's output-directory creation and write. Schema v113 removes Qwen-Agent's former
`simple_doc_parser.py:447` review. The tool-controlled URL is transformed by an exact imported helper
whose body returns hexadecimal `hashlib.sha256(input.encode()).hexdigest()`, and the result occupies
only a non-root `os.path.join(self.data_root, ...)` segment. AgentVerify records a
`path-segment-sanitizer` edge with `policy_effect: removes-path-separator-control`; hexadecimal output
cannot inject a separator, dot segment, drive prefix, or UNC prefix. The proof requires the stdlib
constructor, helper body, import, call binding, and join position. A generic/lookalike helper, local
`hashlib` shadow module, mutable `hashlib` or `os.path.join`, digest-derived root, extra unsanitized segment, rebound call, or branch
escape remains AV-FS001. A fixed literal `Path.write_text` fixture
retains its capability edge without a finding. Attribute `.open(...)` calls now require a proven
`pathlib.Path` receiver, preventing MetaGPT's in-memory filesystem API from being misclassified as a
host filesystem sink.

The Python frontend adds a second pinned `path-boundary` edge at FastMCP's
[`download_skill` directory creation](https://github.com/jlowin/fastmcp/blob/609f79b8a118cd6c4bb58a5341bafd76e42e5a2b/fastmcp_slim/fastmcp/utilities/skills.py#L166-L184).
It proves the resolved candidate is checked with `is_relative_to()` before `mkdir`, but retains
unresolved scope because `target_dir` is caller configured. Local fixtures prove both fail-closed
and positive-branch dominance for literal absolute roots. Writes after the positive branch,
string-prefix checks, candidate/root reassignment, and candidates without `resolve()` remain
reviews. Parent-directory writes also require a strict-descendant check so an equal-to-root
candidate cannot escape through `.parent`. ChatDev adds a second Python form at its
[`target_path.relative_to(tools_dir)`](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/server/routes/tools.py#L58)
check: the try body contains only the check and the ValueError handler terminates before the write.
OpenAI Agents Python adds the interprocedural form: `WorkspaceEditor._resolve()` returns the exact
resolved value after an exclusive, terminating `relative_to(self._root)` check, and its create,
update, and delete methods consume that return at two writes and one unlink. AgentVerify propagates
the proof only through a unique undecorated same-class helper, exact argument mapping, restricted
`Path` construction, and an unchanged return binding. It records `summary: same-class-return` and
keeps the scope unresolved, so these inventory controls do not suppress a tool review. Duplicate or
rebound methods, async/generator helpers, opaque path transforms, continuing handlers, different or
reassigned returns, try `else`/`finally` mutation, conditional construction preludes, caller
reassignment, and parent writes remain unresolved.

Schema v38 therefore records five Python and one TypeScript boundary edges, all with unresolved root
scope in the pinned corpus. Four Python edges use `Path.relative_to`; three are same-class return
summaries. The helper distinction and summary provenance are explicit.

Canonical, top-level import-aliased, and statement-ordered local callable-aliased `os`/`shutil`
mutations extend the Python sink model beyond `open()` and ordinary `Path` methods. They contribute
429 calls; with proven Path moves, the full inventory contains 449 calls: 179 creates, 191 deletes,
46 copies, and 33 moves. Two-path APIs use the destination
argument, including keyword `dst`, and calls record their canonical API, possible API family,
operation, path role, and callable-alias provenance. The added real case is ArcadeAI's
[`copy_fn` selection between `shutil.copy` and `shutil.copy2`](https://github.com/ArcadeAI/arcade-ai/blob/597debaa1593b54172061ce36a414cc29aa8fc6a/examples/mcp_servers/local_filesystem/src/local_filesystem/tools.py#L329-L331),
raising the rule total by one without adding a repository. Compatible branch-local choices merge;
calls before assignment, conditional rebinding to an unknown wrapper, and copy/delete choices remain
negative. A fixed destination and two boundary-guarded copies are local negatives; shadowed imports
and string `.replace()` remain explicit near misses.

Schema v38 additionally resolves 20 `Path.rename`/`Path.replace` moves: two renames and 18 replaces.
Receivers require an explicit unshadowed constructor, an exact Path annotation, or a single immutable
local derived from one. DeepAgents contributes 18 real atomic replacement calls; these are inventory,
not AV-FS001 reviews, because they are not reached from resolved tools. Conditional, reassigned,
union-typed, helper-returned, and shadowed receivers remain unresolved. The destination argument is
still the governed path. ChatDev's
[`source_path.rename(target_path)`](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/server/services/workflow_storage.py#L137)
is a pinned immutable-derived receiver, and a local guarded-rename fixture proves boundary-control
integration.

## AV-FS002 — string-prefix filesystem boundary

The specialized rule reports four default-scope sinks in one pinned repository, CrewAI Examples.
Its file writer checks
[`not str(resolved_path).startswith(str(workdir))`](https://github.com/crewAIInc/crewAI-examples/blob/da94a91e691e1cf5b3151416bb15b5b62729bea8/crews/landing_page_generator/src/landing_page_generator/tools/file_tools.py#L58)
before a parent `mkdir` and `open`; its template copier applies the same shape to
[`destination_resolved`](https://github.com/crewAIInc/crewAI-examples/blob/da94a91e691e1cf5b3151416bb15b5b62729bea8/crews/landing_page_generator/src/landing_page_generator/tools/template_tools.py#L71)
before another parent `mkdir` and `copytree`. A raw string prefix is not a path-component boundary:
a sibling such as `/workspace-escape` starts with `/workspace`.

AgentVerify follows parameter taint through tuple unpacking and self-derived string assignments,
tracks unresolved root joins until `resolve()`, and propagates facts through a try only when
continuing handlers do not bypass the check. Each sink receives a non-suppressing
`path-prefix-check` edge with `weak-string-prefix-validation`; AV-FS002 replaces the generic AV-FS001
result at that location. A check after the sink and a separator-aware expression are pinned
negatives. The rule has high pattern confidence but remains a `review`: an independent allowlist,
sandbox, or other enclosing policy may still prevent exploitation.

## AV-NET001 — parameter-controlled HTTP origin

The rule requires a recognized Python HTTP client or TypeScript global `fetch`/Axios call inside a
tool, or a uniquely named same-file TypeScript helper containing such a call, where an execution
parameter (or its shallow assignment/destructuring alias) determines the URL origin. Immutable
same-file Axios instances preserve direct verb and `.request(...)` flow, including fixed-base and
`allowAbsoluteUrls: false` discrimination. Five exact TypeScript composition families additionally
propagate URLs through imported Axios, `node-fetch`, or global-fetch helpers. A
literal URL and a template/concatenation whose resolved literal prefix already contains a complete
HTTP scheme and host remain inventory-only. The full benchmark reports 17 reviews across ten
repositories:

- [Goose's Wikipedia MCP tool](https://github.com/block/goose/blob/48d480f91163bbcdc0f69f01befa3841a93a1d3e/examples/mcp-wiki/src/mcp_wiki/server.py#L29)
  checks only that the URL begins with HTTP before requesting it.
- [AgentOps' webpage tool](https://github.com/AgentOps-AI/agentops/blob/f8e907b92dabe47232978023fdcb01e2a7d4b752/examples/smolagents/multi_smolagents_system.py#L73)
  sends the tool's URL parameter directly to `requests.get`.
- The MCP TypeScript SDK's
  [`fetch-data` example](https://github.com/modelcontextprotocol/typescript-sdk/blob/3924de99df834302d89f5997a1b64ca268282284/packages/server/src/server/mcp.examples.ts#L130-L138)
  passes its registered tool input directly to global `fetch`.
- Mastra's
  [`httpRequest` tool](https://github.com/mastra-ai/mastra/blob/1da5fb00e141b78c2148b21ee085ec24112cf2a5/packages/agent-builder/src/defaults.ts#L1045)
  passes caller-provided `url` and optional `baseUrl` fields through a static helper to `fetch`.
- MCP Servers' registered
  [`gzip-file-as-resource` tool](https://github.com/modelcontextprotocol/servers/blob/599dafc1054550a6eeb87a6545c1e1b03b3ca827/src/everything/tools/gzip-file-as-resource.ts#L85)
  passes its validated URL through `fetchSafely`; its hostname allowlist is optional and empty by
  default, while byte and timeout limits constrain response size and duration rather than origin.
- Qwen-Agent's multimodal crop example and `image_zoom_in_tool` pass caller-selected remote image
  URLs to `requests.get`. Exact class-registry entrypoints make both network calls reachable.
- Qwen-Agent's registered `simple_doc_parser` passes its URL to an exact imported downloader, and
  smolagents' `visualizer` passes an image path to a function-local self-imported encoder. Each
  helper's matching formal parameter directly reaches `requests.get`; the call-site capability
  retains the helper and sink locations.
- Qwen's `doc_parser`, `extract_doc_vocabulary`, and `web_extractor` reach that same downloader
  through `SimpleDocParser.call`; `retrieval` reaches it through the newly summarized
  `DocParser.call`. Exact class and tool identities make the second hop explicit.
- n8n's AI Builder `web_fetch` passes its parsed tool URL into an imported Axios helper. Its address
  policy is default-off and separately modeled below, so the dynamic-origin review remains visible.
- Flowise contributes two paths: its Agentflow HTTP node copies a variable URL into a fixed Axios
  request object, while its Web Scraper tool propagates `_call(initialInput)` through the recursive
  scraper into `secureFetch`; their distinct transport residuals are modeled separately below.
- Google ADK JS's `LOAD_WEB_PAGE` maps its model-controlled URL into `loadWebPage`; its preflight-only
  address policy and unpinned global fetch are modeled separately below.

Schema v38 separately inventories 22 import-proven `urllib.request.urlopen` calls. Two occur in
Qwen's registered `area_to_weather` and `weather_hour24` tools and therefore receive exact tool
edges. Both construct `Request` objects from a fixed `https://ali-weather.showapi.com` origin plus
tool-controlled query data, so unwrapping the Request's URL keeps them inventory-only. The other 20
calls are outside resolved tool bodies and do not create tool reachability. Exact module-level
imports or aliases are required; rebinding and same-function shadowing invalidate the symbol proof.

Python `urlparse`/`urlsplit` guards now create a `network-origin-allowlist` edge only when an immutable
tool-origin value is checked against static nonempty scheme and hostname sets and the rejecting branch
terminates before the direct request. The control explicitly covers the initial origin only. An
explicit `allow_redirects=False` or `follow_redirects=False` is recorded as redirect-disabled; all
other redirect behavior and DNS scope remain unresolved. The full corpus contains zero such exact
Python controls on its Python review paths. This is a bounded governance gap, not proof that imported validators,
proxy policy, or runtime egress controls are absent.

MCP Servers' same-file `validateDataURI` now contributes one TypeScript
`network-origin-policy` edge to the gzip resource fetch. The validator always restricts schemes to
`data`, `http`, or `https` and uses exact/subdomain matching when `GZIP_ALLOWED_DOMAINS` is nonempty.
Because the normalized environment list explicitly defaults to empty, the edge records
`configured-optional` and `hostname_default: open`; DNS and redirect scope remain unresolved. It
therefore explains partial governance without satisfying destination policy or suppressing the review.

Schema v38 also resolves CrewAI's locally defined `safe_get` as a `network-ssrf-policy` at two
production call sites: `DocsSiteLoader.load` and `DOCXLoader._download_from_url`. The helper validates
the initial URL and each redirect, disables automatic redirects and environment proxies, rejects
private/reserved DNS results, and verifies the connected peer through its mounted adapter. Both edges
record `enforcement_default: enabled`, `redirect_scope: each-hop-validated`,
`dns_scope: connection-pinned`, and `proxy_scope: disabled`. The
`CREWAI_TOOLS_ALLOW_UNSAFE_PATHS` escape hatch and `CREWAI_TOOLS_FORCE_SAFE_PATHS` override remain
explicit instead of being collapsed into unconditional protection. Ten test-scope `safe_get` calls
are inventoried but excluded from the production-control total.

Schema v38 adds two production Composio edges from the session-file router to `safe_get` and
`safe_request`. Both validate HTTP(S) targets against public resolution results before requesting and
pin direct connections through a protected adapter with a connected-peer assertion. `safe_get`
records `redirect_scope: disabled`; `safe_request` follows a bounded loop and records
`redirect_scope: each-hop-validated`. The helper deliberately allows environment or caller proxies,
where the proxy resolves the target and the SDK cannot pin that peer. Both edges therefore record
`dns_scope: connection-pinned-unless-proxied` and
`proxy_scope: environment-or-caller-dependent`, rather than inheriting CrewAI's stronger
`connection-pinned`/`disabled` profile. Four positive and one negative exact IR labels validate this
new family.

Schema v38 adds ten Langflow production edges whose policy is strong when enabled but explicitly
configurable. The collector's schema-v4 selection-hint manifest lists 11 callers from Langflow's own
SSRF-wiring registry plus the security settings source; all 12 files are charged against the existing
20-file dependency cap. The analyzer then resolves exact imports across Langflow's nested source root
and requires the default-on global and connector settings, both gate implementations, configured
allowlist and default literal-loopback behavior, the core public-address validator, async and sync
backends that connect to validated IPs, proxy-rejecting transports, protected client construction,
and ordinary-client fallbacks. Five synchronous GET edges disable redirects by default and validate
each bounded hop when enabled; the other five GET/POST edges reject automatic redirects. All ten
record `dns_scope: connection-pinned-when-enforced`, `proxy_scope: disabled-when-enforced`, and both
opt-out environment names. The initial-origin scope explicitly preserves configured allowlists and
the default literal-loopback exemption, so no edge claims unconditional SSRF prevention. Four
positive and one negative IR labels cover local sync/async applications, DeepSeek and Glean pinned
calls, and an ordinary request; mutations of the enabled default or pinned backend withhold the
summary.

Schema v38 resolves n8n's AI Builder `web_fetch` as a dynamic-origin tool path and preserves its
default-off composition. Four audited hint files add the CLI composition root, discovery subgraph,
tool factory, and Axios helper within n8n's existing dependency budget. The composition root injects
`SsrfProtectionService` only when `N8N_SSRF_PROTECTION_ENABLED` is true; the false/default branch
injects `createPassthroughSsrfGuard`, whose URL checks are successful no-ops and whose lookup is the
ordinary DNS function. The enabled service applies configured hostname/IP allowlists and blocklists,
preflight resolution, and a custom lookup that validates addresses returned at connection time. The
Axios helper caps redirects at five, uses the custom lookup, validates direct-IP redirect targets,
halts cross-host auto-follow, and revalidates the cross-host URL before a second fetch. The edge still
records `proxy_scope: unresolved`: selected source does not prove whether Axios proxy routing keeps
the custom lookup on the destination. Independent domain HITL is retained as governance context but
does not satisfy address policy. Two positive and one negative IR labels cover the local and pinned
edges plus raw Axios. Mutations of the composition branch, lookup, or redirect hook withhold the
edge; a literal default-on mutation instead retains it and changes its enforcement/escape state.

Schema v38 also resolves two Flowise paths. Its `httpAgentflow` node reaches
`secureAxiosRequest` through a fixed request object, while `web_scraper_tool` propagates
`_call(initialInput)` through `scrapeRecursive` and `scrapeSingleUrl` into `secureFetch`. Two audited
caller hints and the `src/index.ts` re-export barrel are charged against Flowise's dependency budget.
The HTTP node exposes
`nodeData.inputs.url` as a variable input, derives `finalUrl`, and assigns it to the
fixed config's `url` property before the imported call. The helper enables its default address deny
list unless `HTTP_SECURITY_CHECK=false`, normalizes IPv4-mapped IPv6, validates every DNS answer,
disables automatic redirects, validates each manual hop, and installs an agent lookup pinned to the
chosen address. The exact caller supplies no adapter, agent, proxy, socket path, transport, or spread
property. Environment proxy routing remains a real residual, so the edge records
`dns_scope: connection-pinned-unless-proxied`, `proxy_scope: environment-dependent`, and
`escape_hatch: configured-opt-out`. The fetch helper overwrites the caller's requested redirect mode
with `manual`, validates and resolves every bounded hop, then supplies `agent: () => agent` after the
caller-option spread. Its edge therefore records `dns_scope: connection-pinned`,
`proxy_scope: pinned-agent`, and `transport_scope: caller-agent-overridden`; it does not inherit the
Axios path's environment-proxy residual. Three exact IR labels per family cover both local and pinned
edges plus unrelated same-named helpers. Default-off, automatic-redirect, unpinned-agent,
caller-transport, mapped-address, deny-predicate, and broken same-class-flow mutations withhold the
corresponding edge.

Schema v38 resolves Google ADK JS's `LOAD_WEB_PAGE` through its imported `FunctionTool` definition
and exact `execute: ({url}) => loadWebPage(url)` callback. The helper restricts schemes, blocks
localhost names, checks every preflight DNS answer against explicit IPv4/IPv6 non-global ranges,
normalizes IPv4-mapped IPv6, and disables redirects. It then calls unpinned global `fetch`, whose own
connection-time DNS lookup is not tied to the preflight result. The edge therefore records
`dns_scope: preflight-only-rebinding-residual`, `transport_scope: global-fetch-unpinned`, and
`proxy_scope: unresolved`, while preserving `enforcement_default: enabled` and `escape_hatch: none`.
Two positive and one negative IR labels cover the local and pinned paths plus an ordinary same-named
helper; missing imports, fixed inputs, automatic redirects, incomplete address checks, or mapped-IP
bypasses withhold the edge.

Schema v40 adds Activepieces' configured MCP transport as an imported filtering-Axios composition.
The entrypoint passes `tool.serverUrl` into `createMcpClient`; the transport's exact `safeHttp` named
import reaches `safeHttp.axios.request`. The helper forces `RequestFilteringHttpAgent` and
`RequestFilteringHttpsAgent` after caller config, while the nearest package manifest pins
`request-filtering-agent` 3.2.0. Direct IPs and every direct connection-time DNS result are filtered,
with `AP_SSRF_ALLOW_LIST` retaining configured IP/CIDR exceptions. Environment proxy routing can
shift that boundary to the proxy, so the edge records
`dns_scope: connection-time-filtered-unless-proxied`, `proxy_scope: environment-dependent`, and
`transport_scope: imported-axios-client-instance`. Two positive and one negative IR labels cover the
local and pinned paths plus raw Axios; wrong imports, missing manifest proof, unsafe agent ordering,
and caller proxy/agent overrides withhold the edge. The generic same-file Axios-instance syntax is
fixture-validated; the selected corpus contains no matching real same-file instance call.

Schema v41 adds four Composio TypeScript paths through the package-conditional `#ssrf_guard`
import. The Node/default helper validates every DNS answer and bounded manual redirect, then supplies
the validated addresses through an Undici dispatcher's lookup. Caller dispatchers, non-stock global
dispatchers, and `NODE_USE_ENV_PROXY` routing stand down from pinning and retain preflight-only
validation. The edge implementation of `ssrfSafeFetch` fails closed for the caller-selected session
upload URL; the separate `ssrfSafeFetchWhereSupported` export uses raw edge fetch for three
API-response transfer paths. Four positive and one negative IR labels cover local and pinned paths
plus raw fetch. Mutations of the package map, manual redirect, dispatcher pin, import, or edge
fail-closed branch withhold all four edges.

Schema v42 adds Composio CLI's tool-file preprocessing path. The exact
`ToolsExecutor.execute(slug, params)` implementation passes `params.arguments` and the resolved input
schema to `uploadToolInputFiles`. Recursive `file_uploadable` hydration sends HTTP(S) strings through
`readFileFromUrl`, which uses raw global `fetch(url)` rather than the core safe-fetch export. The
engine emits one symbolized tool-to-network edge and one AV-NET001 review at line 146. Two positive
and one negative IR labels cover local, pinned, and raw paths; guarded-fetch, fixed-argument,
schema-gate, and wrong-import mutations withhold the edge.

Schema v43 adds Google ADK JS's generated OpenAPI tool as a fixed-origin counterexample. The exact
toolset/parser/factory chain creates `RestApiTool.runAsync`; model arguments can affect encoded path
segments, query, headers, and body, while `endpoint.baseUrl` comes from the first spec server.
Server variables use declared defaults or enums, dot segments are rejected, and credential handling
only appends query data or headers. The engine emits one symbolized tool-to-network edge and one
`network-origin-policy` edge at line 134, but no AV-NET001 review. Two positive and one negative IR
labels plus six incomplete-composition mutations pin the distinction.

Pinned negatives include a [fixed Devpost origin](https://github.com/microsoft/ai-agents-for-beginners/blob/01777b05e8afeba6bf5a6dbe74cc2293372d3693/11-agentic-protocols/code_samples/github-mcp/app.py#L118),
the MCP SDK's [fixed weather API](https://github.com/modelcontextprotocol/typescript-sdk/blob/3924de99df834302d89f5997a1b64ca268282284/examples/guides/get-started/firstServer.examples.ts#L20-L40),
Vercel's [literal PDF URL](https://github.com/vercel/ai/blob/f607a129c0298870038b398dbcba57ff041114f6/examples/ai-e2e-next/tool/fetch-pdf-tool.ts#L5-L12),
and Qwen's two fixed urllib weather endpoints plus fixed AMap endpoint formatted with a dynamic
query. Python fixed-origin facts propagate
through unique module constants and immutable `self` fields, concatenation, and `.format(...)`.
Results remain `review`: neither the local Python controls, configured-open TypeScript policy,
default-off n8n control, proxy-conditional Flowise control, nor ADK's preflight-only address check
suppresses the rule. Redirect, DNS rebinding, proxy, imported-validator, and runtime-egress state is
kept path-specific rather than treated as universally resolved.

## AV-SANDBOX001 — container/host boundary

The rule found 20 default-scope boundary crossings across ten repositories. It reports development
and production configuration alike but retains their source path so policy can distinguish them.
Hand-reviewed examples include:

- [AutoGen devcontainer Docker socket](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/.devcontainer/docker-compose.yml#L11)
- [Langflow deployment Docker socket](https://github.com/langflow-ai/langflow/blob/09ef6b2b7119e35a6787fc249f916f8b47b28615/deploy/docker-compose.yml#L10)
- [Bytebot privileged container](https://github.com/bytebot-ai/bytebot/blob/3d37894ce07ef8d8b40adc7fd309ad96c2a71313/docker/docker-compose.yml#L15)
- [Bytebot Helm privileged default](https://github.com/bytebot-ai/bytebot/blob/3d37894ce07ef8d8b40adc7fd309ad96c2a71313/helm/charts/bytebot-desktop/values.yaml#L40)
- [OpenHands service-account token default](https://github.com/OpenHands/OpenHands/blob/4a8cabc5fdc81bb6d899785f33ea7449387beb4c/helm/agent-canvas/values.yaml#L45)
- [AutoGPT read-only Docker socket mount](https://github.com/Significant-Gravitas/AutoGPT/blob/601093ddfe23a3d58a9c8f4a208bd49b203ee612/autogpt_platform/db/docker/docker-compose.yml#L471)
- [trae-agent privileged Docker SDK call](https://github.com/bytedance/trae-agent/blob/e839e559ac61bdd0e057c375dd1dee391fee797d/evaluation/patch_selection/trae_selector/sandbox.py#L33)
- [Skyvern host-mounted credentials directory](https://github.com/Skyvern-AI/skyvern/blob/486c8975e9864a53037d4701b781f8619e698c40/kubernetes-deployment/backend/backend-deployment.yaml#L63)
- [Goose read-only host SSH credential mount](https://github.com/block/goose/blob/48d480f91163bbcdc0f69f01befa3841a93a1d3e/documentation/docs/docker/docker-compose.yml#L15)

A read-only Docker socket mount is still reported because the Docker API can create privileged
workloads even when the socket file itself is mounted read-only. A mounted service-account token does
not by itself prove useful Kubernetes privileges; the result remains `review` until RBAC bindings and
the rendered workload are resolved. Likewise, a `hostPath` finding proves a node-filesystem boundary,
not that its contents are sensitive; path-specific policy and pod scheduling remain unresolved. The
Docker SDK frontend currently requires an imported `docker` module, a `.containers.run(...)` call,
and a literal `privileged=True` keyword. Host credential binds remain reviews when marked read-only:
that mode prevents key mutation but not credential use or exfiltration. Exact host-source paths are
required; named volumes, `.gitconfig`, near-name directories, and ordinary workspace binds remain
negative even when their container destination resembles a credential directory.

## AV-AUDIT001 — durable action record lacks actor attribution

Schema v63 reports one medium-severity, high-confidence production review in Skyvern Task v3. The
exact path executes a billable/recordable [tool handler](https://github.com/Skyvern-AI/skyvern/blob/486c8975e9864a53037d4701b781f8619e698c40/skyvern/forge/taskv3/loop.py#L559),
passes its completed or failed result to the configured callback, and commits an action row. However,
the Task v3 constructor does not populate `created_by`, and the
[`ActionModel` field](https://github.com/Skyvern-AI/skyvern/blob/486c8975e9864a53037d4701b781f8619e698c40/skyvern/forge/sdk/db/models.py#L1157)
is nullable. The row remains correlated to organization, workflow, task, step, action type, status,
and ordering, so this is an actor-attribution gap in a proven durable record—not a claim that logging
is absent.

The rule fires only when an external-action capability has a source-proven durable-action-record edge
whose actor-attribution state is explicitly unresolved. Generic untraced or unrecorded actions and
Google ADK's attributable BigQuery record are regression negatives. Remediation is to populate and
require a non-null authenticated actor identifier before commit while retaining execution correlation
and surfacing failed writes through metrics or alerts.

## Seed truth-set metrics

`benchmarks/truthset.json` contains 730 exact labels across all 25 enabled rules: 337 positives and 393
negatives. Labels mix local fixtures, immutable real positives, and unmatched real corpus observations,
including a CAMEL allowlist, fixed-name MCP, ordinary non-tool filesystem writes, fixed argv and
literal TypeScript shell calls, constant/test-only eval, literal browser evaluation, an ordinary
non-browser `.evaluate(...)` method, non-approval skip flags, disabled
auto-approval, conditional environment guards, late MCP guards, and safe
Compose/Kubernetes/Docker SDK settings, host credential bind near misses, and exact/prompt-only MCP
package launchers. All 730 currently pass;
each rule's seed precision and recall are 1.0. Negative labels must retain either an observed Agent IR
component anchor or verified source text at the exact pinned line, preventing a missing or drifting
location from passing silently.

This is a curated regression set, not an unbiased estimate of ecosystem precision or recall. The next
benchmark milestone is a separately sampled, externally reviewed holdout set with framework-stratified
coverage; its labels must not drive rule implementation before evaluation.
[`holdout-design.md`](holdout-design.md) defines the sampling, labeling, leakage-control, and
reporting process for that future benchmark. Evaluator outputs now include benchmark metadata that
distinguishes public regression runs from sealed-holdout runs and records label/manifest hashes; the
shape is validated by [`benchmark-results-v1.schema.json`](benchmark-results-v1.schema.json). Result
files include `passed` and `failed` totals, an `all_labels_passed` boolean, and a failure summary
that separates observation, anchor, and source-snippet mismatches, so stale labels do not hide
inside precision/recall metrics.
Run `agentverify benchmark verify --require-evaluation-kind public-regression --require-all-passed`
to validate the checked-in result files, recompute their embedded label or manifest digests, and
cross-check those derived totals. The source-checkout `uv run python scripts/verify_benchmark_results.py`
wrapper delegates to the same verifier. Use
[`release-checklist.md`](release-checklist.md) before publishing benchmark numbers; the verifier can
fail release workflows that require `public-regression`, `sealed-holdout`, manifest, sealed-status,
or all-labels-passed claims. The same contract is available from installed CLIs through
`agentverify schema benchmark-result`.

## Agent IR control-edge checks

IR component and relationship inference is scored separately from finding rules in
`benchmarks/ir-truthset.json`.
Four audit labels pair a traced and untraced local external action with ArcadeAI's pinned
[Gmail send span](https://github.com/ArcadeAI/arcade-ai/blob/597debaa1593b54172061ce36a414cc29aa8fc6a/examples/mcp_servers/telemetry_passback/src/telemetry_passback/server.py#L234)
and its sibling authentication span. Only the `httpx` send at line 241 is governed by the send span;
the authentication span at line 223 does not claim action coverage. All four labels pass. Exporter
configuration and durable storage remain unresolved, so this inventory edge does not suppress a
finding or trigger `AV-AUDIT001`. The full corpus scan observed seven action-trace controls and five
lexically governed HTTP capability edges, all in that ArcadeAI telemetry example.

Four additional audit labels exercise Google ADK Python's BigQuery Agent Analytics plugin: a local
enabled external action and explicit-disabled counterexample, the pinned Storage Write API edge, and
a pinned `InMemoryRunner` plugin composition. The resolver requires the exact enabled/default plugin,
`Runner` propagation, `PluginManager` callback dispatch, before/after/error tool flow, and
`append_rows` sink. Schema v63 records one available durable control, one audit-storage capability,
two test deployments, two agent-control edges, one storage edge, and zero production deployments or
production external-action control edges. Records are attributable by event, agent, user, session,
invocation, and tool, but delivery is best-effort with drop accounting. This attributable control is
a negative for `AV-AUDIT001`; production deployment, retention, and loss guarantees remain unresolved.

Five Skyvern Task v3 labels add a local governed action, an unrelated untracked negative, and pinned
production action, storage, and agent-control edges. The exact path begins after model-selected
`spec.handler(args)` dispatch, retains billable/recordable completed or failed actions, invokes the
configured round callback, constructs an action with organization/workflow/task/step/order identity,
and commits an `ActionModel` to the SQLAlchemy `actions` table. Schema v63 records one production
deployment, one governed external-action edge, and one storage edge. It remains a
`durable-action-record`, not a fully attributable audit: `created_by` is nullable and unset in this
path, persistence happens after the action, and callback/database failures are contained.
Schema v63 raises one medium-severity, high-confidence `AV-AUDIT001` review at this exact production
action edge. The rule requires a durable-action-record relationship whose actor-attribution state is
explicitly unresolved; it does not infer findings from generic untraced or unrecorded actions. Two
positive and two negative rule labels pin the Skyvern, ADK, and unrelated-action boundaries.

Three MCP registry labels cover the local control edge, a caller-owned-map negative, and the pinned
SDK SessionGroup edge. Four fixed-instance labels cover a local constructor-only binding, a mutable
negative, AgentScope's pinned wrapper, and Trae's pure-getter path. Eight import labels cover relative
and contextual positives, missing-export and multiple-ancestor negatives, and three pinned CrewAI
Examples edges. Three contextual network-import labels cover dynamic and fixed Google ADK helper
calls with exact helper-path evidence. Seven approval labels cover enabled,
disabled, callback, and automatic-handler policies plus pinned Python and TypeScript OpenAI shell
edges. Four TypeScript graph
labels cover inline and assigned agent adapters, the Cline tool path, and a nested-token negative.
Nine registration labels cover four local Mastra/MCP edges, an ordinary-registry negative, and four
pinned Mastra/MCP capability edges. Six helper-summary labels cover two local edges, two pinned
Mastra edges, the MCP Servers edge, and a regex-literal negative. Four TypeScript path-boundary labels
cover a local proven guard, imported name-only and reassignment negatives, and MCP Servers' real
control edge. Sixteen Python path-boundary labels cover six local proven sinks, seven local bypasses,
a configured-root edge, and FastMCP's and ChatDev's real control edges. Nineteen Python filesystem-mutation labels
cover nine local positives, seven local rebinding/compatibility negatives, and three pinned
ArcadeAI/CrewAI edges. Four closure-binding labels cover a returned local callback, a rebound negative, browser-use's
registered wrapper, and the Python SDK retry negative. Three method-registry labels cover a local
resolved callee, a fallback negative, and FastMCP's real summary. Five imported-registry labels cover
a local resolved manager, mutable/fallback/rebound negatives, and the pinned MCP Python SDK manager.
Eleven same-class path-helper labels cover the local exact-return edge, seven adversarial negatives,
and OpenAI's three real sinks. Fourteen path-prefix labels cover Python local/real weak-prefix
checks, TypeScript same-class helper propagation, OpenAI Agents JS' workspace-editor prefix check,
and post-write, separator-aware, and unchecked-helper negatives. Seven Python post-registration
labels cover two local
tool edges, one cross-file approval edge, three adversarial negatives, and Skyvern's real filesystem
edge. Six transparent-wrapper labels cover direct, decorator-factory, and two-layer positives plus
metadata-only, branch-only, and deferred-call negatives. Ten browser-evaluation labels cover eight
exact tool-to-browser-page execution components—including positional and keyword alternate APIs,
selector/script discrimination, and one pinned Skyvern test observation—plus two ordinary-method or
missing-component negatives. Thirteen Python
registry-tool labels cover eight exact MetaGPT/Qwen capability edges and five provenance,
entrypoint, or receiver negatives. Eleven imported Python function-network labels cover six exact
tool edges and five nested, module-qualified, or rebound negatives. Fifteen imported class-network
labels cover ten direct/bound/multihop or fixed-field edges and five mutable or ambiguous negatives.
Seven urllib labels cover two local dynamic origins, one local fixed origin, two local binding
negatives, and two pinned Qwen fixed-origin tool edges. Nine Python network-origin-control labels cover
two fail-closed local guards and seven late, partial, continuing, rebound, shadowed, mutable-policy,
or rejection-branch-sink negatives. Seven TypeScript network-origin-policy labels cover the local and
MCP Servers edges plus late, rebound, nested-call, scheme-only, and branch-only negatives. One
hundred thirty-three browser-receiver labels cover 63 exact parameter, alias, factory,
annotated/constructed class-field, property, local/module/context-manager construction, derived
Locator, chained-inventory, imported field/method return, and pinned-real proofs plus 70 ordinary,
reassigned, late/branch,
container, conflicting/wrong type, static-method, near-package, rebound, duplicate-import,
conditional/reassigned local construction, branch/ordinary context yields, repeated/shadowed
property, near-factory, shadowed-factory, ordinary-locator, and unknown-derivation negatives. Six
secure-network-helper
labels cover two local and two CrewAI edges plus incomplete-redirect and rebound-import negatives.
Five proxy-conditional secure-network labels cover two local and two Composio edges plus an ordinary
request negative. Five configurable pinned-network labels cover two local and two Langflow edges plus
an ordinary request negative. Three TypeScript configurable-composition labels cover local and n8n
edges plus raw Axios. Three Flowise request-object labels and three Flowise `secureFetch` labels each
cover local and pinned governed paths plus an unrelated same-named helper. Three Google ADK labels
cover local and pinned preflight-only paths plus an ordinary same-named helper. Nine A2A endpoint
labels cover two local and two pinned unconstrained TypeScript paths, four guarded ADK Python paths,
and a trusted local-card negative. Five Axios-instance labels cover four direct/request/base-policy
edges and one shadowed-client negative. Three Activepieces filtering-client labels cover the local
and pinned governed paths plus raw Axios. Five Composio conditional-runtime labels cover two local
and two pinned governed paths plus raw fetch. Three Composio CLI upload labels cover the exact local
and pinned schema-driven tool-argument flows plus an unrelated raw fetch. Three Google ADK OpenAPI
labels cover the local and pinned origin locks plus an unrelated raw global fetch. Three OpenAI
Agents Python MCP-approval labels cover the local and pinned disabled defaults plus an unrelated
server helper. Four Google ADK BigQuery audit labels add three positive durable-control/storage edges
and one explicit-disabled negative. Five Skyvern action-history labels add four positive production/
local record edges and one unrelated-action negative. Ten direct-callable labels add the pinned
PydanticAI definition and local same-block positives plus reassigned, cross-branch, parameter, and
forward-reference negatives. Thirteen wrapper labels cover exact local body/approval/Agent edges,
wrong and shadowed factories, reassignment, cross-branch and lambda negatives, and both pinned
OpenAI Agent edges. Eleven Agent-helper labels cover direct and tuple local propagation, conditional,
reassigned, transformed, cross-branch and external-receiver negatives, and all three pinned CrewAI
edges. Seven imported-Agent-factory labels cover one exact local edge, ambiguous and reimported
unresolved edges, and four pinned production CrewAI projects. Eighteen typed-tool-parameter labels cover exact assigned and inline-only local plus pinned
parameter edges, the non-collapsing concrete-ID negative, and mismatched, reassigned, uncalled,
rebound, class/nested-scope shadowed, union-typed, and wrong-annotation cases. Sixteen literal-tool-
binding labels cover local exact/unresolved boundaries plus pinned Agno, CrewAI, Google ADK, and
Marvin paths. Nineteen imported-literal-tool labels cover the exact local export/import boundary,
literal-`__all__` star-import visibility, filtered wildcard negatives, six unresolved
ambiguity/shadowing/order forms, and all seven pinned Google ADK edges. Twenty-three
tool-factory/adapter labels cover four local Agent edges, one hosted-MCP capability, one local
Agent-as-tool delegation, eight conservative local negatives, two AutoGen factory edges, one Google
ADK LangChain adapter edge, four Composio HostedMCP edges, and the OpenAI Agent edge plus delegation.
The 452 component-taxonomy labels add 324 exact local/pinned framework, provider, call,
and model positives plus 128 near-name, rebound, custom-endpoint, scoped-binding, nonliteral-request,
and unrelated-service negatives. Nineteen OpenHands labels—four taxonomy and 15 composition—pin
built-in tools, analyzer and confirmation controls, exact Agent reachability, shared-conversation
ambiguity, and rebound or near-package negatives. Twenty-four Trae default-tool labels add 22 exact
Agent/tool/capability/setting-edge positives plus two near-package negatives. Twenty Roo command-
approval labels add 18 exact composition positives plus two near-package or token-boundary negatives.
Thirty-two Letta default-tool labels add 30 exact Agent/tool/capability/setting-edge positives plus
near-package and standard-default negatives.
Twenty-two Continue plan-mode labels add 20 exact framework/Agent/tool/capability/control/edge
positives plus incomplete-composition and dynamic-ask negatives.
Twenty-four Continue MCP labels add 22 exact Agent/tool/server/capability/control/edge positives plus
incomplete-composition negatives.
Fifty-two Cline sub-agent approval labels add 48 exact root/child Agent, tool, capability,
setting/control, and relationship positives plus incomplete and safely propagated negatives.
Three path-segment-sanitizer labels pin the exact local and Qwen
SHA-256 edges plus a lookalike negative.
Twenty-five MCP
package-launcher labels separately
pin package/version/auto-install facts across JSON, Python constructors, Python dictionaries, and
four real repositories. Forty-eight Python Agent→MCP-binding labels comprise 31 positives and 17
negatives. Five Python OpenAI run-state approval-decision persistence labels pin literal sticky,
stable boolean, per-call, and prompt-derived dynamic `always_approve`/`always_reject` metadata.
Twenty-one OpenAI run-state rejection-message and helper-parameter labels pin Python literal,
literal-binding, template, and dynamic `rejection_message` metadata, the TypeScript `{ message }`
reject-options equivalent, exact same-file helper-call decision provenance, and helper-derived
run-state resume continuity.
Twelve real OpenAI Agents JS built-in-tool labels pin approval-enabled `shellTool` and
`applyPatchTool` components, their human-approval edges, reachable agent-tool edges from the local
built-in tools documentation and workspace-editor examples, and the local filesystem write
capability implied by literal `applyPatchTool({ editor, ... })` options.
Twelve OpenAI Agents JS history-feedback labels pin local loop/concat feedback shapes, exact
same-file agent aliases with reassignment negatives, the real `chatLoop.ts` caller-owned history
helper, and the real routed `routing.ts` triage-agent alias.
Twelve OpenAI Agents JS trace labels pin local and real `withTrace(..., { groupId })` and
`withTrace(..., { traceId })` correlation evidence, including the real `routing.ts` dynamic
`conversationId` group binding, the real Codex tool example's generated trace ID with a logged
OpenAI platform trace URL, and local missing-option negatives.
All 2,482 IR labels pass (1,898 positives and 584 negatives). The checked
`benchmarks/ir-truthset-results.json` file contains the current per-check precision/recall
breakdown, including the Vercel WorkflowAgent same-file/imported/reexported model-binding labels,
direct/named-reexported/star-reexported execute-helper tool-graph labels, real Vercel
WorkflowAgent constructor and stream-call telemetry/callback observability labels, OpenAI
Agents JS and Python safety-check labels added for `computerTool({ onSafetyCheck })` and
`ComputerTool(on_safety_check=...)`, plus OpenAI Agents JS run-state approval-decision labels for JS
and Python state approve/reject handling, persistence, custom rejection messages, JS env-backed
approve branches, TypeScript local/helper reject-message metadata, helper-derived state resumes, and
clean reject/reassigned near misses.

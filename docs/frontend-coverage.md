# Frontend coverage and known gaps

This document separates implemented syntax from empirical corpus observations. A missing signature
does not mean a repository lacks agents or controls: AgentVerify may not support its language,
framework, wrapper, or configuration path. Counts come from schema-v36
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
| visual-platform | 4 | 4 | 1 | 1 | 1 | 3 |
| workflow-agent | 3 | 3 | 1 | 3 | 1 | 3 |
| workflow-platform | 2 | 2 | 0 | 1 | 2 | 2 |
| **Total with observation** | **71** | **70** | **29** | **43** | **47** | **67** |

Observed framework signatures are LangChain (18 repositories), OpenAI Agents SDK (9), LangGraph
(8), CrewAI (4), PydanticAI (3), AutoGen (1), and Cline SDK (1). Provider observations are OpenAI
(41), Anthropic (17), and Azure OpenAI (11). These counts overlap and are lower than research-wide lexical signals
because the engine requires supported selected files and more specific syntax.

Across the selected snapshot, 8,738 agent/tool observations have module-qualified symbol IDs. Of
2,938 relationship endpoint observations, 1,930 carry IDs and 1,928 resolve to an observed component
(1,675 Python and 253 TypeScript); the two unmatched IDs are explicit Python re-export targets.
Repeated Python and TypeScript constructor bindings are occurrence-qualified. Their direct source
edges resolve exactly. In Python files with repeated identities, schema v36 records 325 same-scope and
14 module-scope single-definition resolutions, plus 23 `ambiguous-repeated-binding` references that
remain withheld.
Capability/control taxonomy endpoints intentionally lack
source-symbol IDs, so the endpoint fraction is inventory coverage rather than an accuracy or recall
metric.

The native AI BOM 1.1 resolver independently classifies all 2,938 endpoints: 1,928 by symbol ID, 463
by exact relationship evidence, 18 by a unique display name, 30 as ambiguous, and 499 as unresolved.
Evidence-local resolution removes capability/control ambiguities; occurrence-qualified bindings
resolve repeated source agent/tool observations, and conservative lexical resolution removes further
target ambiguities. The remaining 30 are tool targets without a unique local symbol or target location.

The TypeScript graph contains 95 structure-backed agent edges: 14 agent-as-tool delegations and 81
agent-to-tool edges. All 81 tool endpoints resolve to an observed component. This replaces a prior
token-level array heuristic that could turn words inside callbacks, strings, or nested options into
spurious tool edges.

Import-aware factory/registration discovery adds 27 Mastra `createTool` observations, 264 MCP
`registerTool` observations, 70 generic/Mastra object-property tools, and ten exact
callback-to-capability edges; the factory/property categories overlap. Four edges are network
capabilities propagated from unique same-file free/static helpers. Literal or uniquely bound
registration names become symbol identities; unknown names retain occurrence-qualified fallbacks.
Six capability-to-control edges resolve `path-boundary` guards: one imported TypeScript guard, two
same-function Python guards, and three same-class return summaries in OpenAI Agents Python.
FastMCP uses `Path.is_relative_to`; ChatDev and OpenAI use an exclusive `Path.relative_to` try with a
terminating `ValueError` handler. The OpenAI helper's checked return is consumed by two writes and an
unlink. All six pinned roots are dynamically configured, so their scope remains explicit and
unresolved and none suppresses a review.

The Python frontend also resolves all 115 Skyvern tools registered after definition through exact
`mcp.tool(...)(function)` applications. Every target is reached through one immutable relative
import and one unique module-level function definition. Ninety-three registrations are direct; 22
pass through proven metadata-preserving forwarders, totaling 23 wrapper layers because one tool has
a two-wrapper chain. The wrappers must use `functools.wraps` and directly forward `*args, **kwargs`
to the wrapped callable. All 115 tools create only 21 exact capability edges—14 browser actions, six
browser-page evaluations, and one filesystem mutation—so inventory expansion is kept separate from
finding volume. Of Skyvern's 30 inventoried Playwright evaluations, only `skyvern_evaluate` receives
raw tool-controlled script text and triggers `AV-EXEC002`; JavaScript assembled from normalized
numeric scroll inputs remains inventory-only. Opaque or
branch-only wrappers, rebound imports or registrars, wildcard imports, and non-FastMCP factories
remain unresolved.

Import-proven MetaGPT and Qwen-Agent registry decorators add 56 Python tools: five functions and 51
classes, split across 35 MetaGPT and 21 Qwen observations. Thirty-four class/function entrypoints are
resolved and create 26 exact tool-to-capability edges after imported-helper and urllib propagation. MetaGPT class reachability is limited to a
literal `include_functions=[...]` list; Qwen classes require a literal registered name and one direct
`call` method. Decorator aliases must come from the exact framework module and remain unrebound.
Nonliteral entrypoint lists and names retain inventory where possible but do not promote arbitrary
methods, while unrelated `register_tool` functions remain negative.

Two Python call sites resolve network behavior through unique top-level imported functions. Qwen's
registered document parser passes its URL into a downloader whose first parameter reaches
`requests.get`; smolagents' visualizer uses a function-local self-import of an image encoder with the
same direct flow. Both create exact network edges and dynamic-origin reviews. The summary requires an
exact named import to a selected file, a unique top-level definition, a recognized direct HTTP call,
and direct formal-parameter origin flow. Fixed origins remain inventory-only. Nested HTTP helpers,
module-object calls, rebound imports or HTTP clients, and function-local reassignment are withheld.

Four more Qwen network edges propagate iteratively through registered classes. A class summary is
created only for a unique registered class with one literal entrypoint and an already proven dynamic
network edge. Exact imported direct construction or one immutable `self` field can apply it, mapping
the caller's positional/keyword argument back to the callee's first entrypoint parameter. This
resolves `DocParser`, `ExtractDocVocabulary`, and `WebExtractor` through `SimpleDocParser`, then
resolves `Retrieval` through `DocParser` on the next graph iteration. All four are dynamic and cite
two exact callee summaries. Fixed arguments retain inventory edges. Multiple assignments, `setattr`,
constructor shadowing/rebinding, duplicate classes, and module-qualified calls remain unresolved. A
unique literal callee key is mapped field-sensitively, preserving a fixed URL beside dynamic sibling
fields as an inventory-only edge.

Exact same-function Python scheme and hostname rejection can govern a direct network capability as
`network-origin-allowlist`. The proof is statement-ordered and import-proven, and records explicit
redirect disabling separately from unresolved DNS and redirect scope. The full schema-v36 corpus run
finds zero qualifying controls on the Python AV-NET001 review paths; imported validators and runtime
egress policy remain outside this bounded observation.

One TypeScript `network-origin-policy` edge governs MCP Servers' gzip resource fetch. Its same-file
validator always restricts the URL scheme, but the normalized exact/subdomain hostname list comes
from `GZIP_ALLOWED_DOMAINS` and defaults to empty, so the edge records `configured-optional` and
`hostname_default: open`. Redirect and DNS scope remain unresolved, and the review is retained.

Two production Python `network-ssrf-policy` edges govern CrewAI's documentation-site and DOCX
loaders. The source-proven `safe_get` transport validates the initial URL and every redirect, disables
automatic redirects and environment proxies, rejects private/reserved DNS results, and validates the
connected peer. Both edges record `enforcement_default: enabled`, `dns_scope: connection-pinned`, and
the explicit `CREWAI_TOOLS_ALLOW_UNSAFE_PATHS` opt-out plus `CREWAI_TOOLS_FORCE_SAFE_PATHS`
override. Ten additional test-scope calls are inventoried, explaining the 12 new relationships while
the CrewAI production submetric remains two.

Two further production edges govern Composio's session-file download and upload paths. Their shared
validator rejects non-HTTP(S) targets and non-public DNS results; direct connections mount a pinned
adapter and verify the connected peer. The download helper disables redirects, while the upload
helper validates every hop in its bounded manual loop. Environment or caller proxies intentionally
bypass peer pinning, so these edges retain `dns_scope: connection-pinned-unless-proxied` and
`proxy_scope: environment-or-caller-dependent`. Schema v36 therefore reports four enabled-default
Python secure-network edges in this pair of families: two fully pinned/proxy-disabled and two
proxy-conditional.

Ten Langflow connector call sites form a third structural family. Versioned selection hints add the
audited production callers and settings file within the same 20-file dependency cap; the selected
validator and transport modules then resolve through exact imports across the nested `src/lfx/src/lfx`
package root. The proof requires default-on global and connector settings, the corresponding opt-out
gates, configured allowlist and default literal-loopback behavior, async and sync pinning backends,
proxy-rejecting transports, and ordinary-client fallbacks. Five synchronous GET edges disable
redirects by default and validate each bounded hop when enabled; five remaining GET/POST edges reject
automatic redirects. All ten record `dns_scope: connection-pinned-when-enforced`,
`proxy_scope: disabled-when-enforced`, and `escape_hatch: configured-opt-out` rather than claiming
unconditional protection. Schema v36 therefore reports 14 enabled-default Python secure-network edges:
two fully pinned, two proxy-conditional, and ten configurable/enforcement-conditional.

One n8n TypeScript edge resolves the AI Builder `web_fetch` tool through its production composition
root. Four audited hint files expose the composition root, discovery subgraph, tool factory, and Axios
helper. The global setting defaults false: the enabled branch injects `SsrfProtectionService`, while
the default branch injects a passthrough whose validation succeeds and whose lookup is ordinary DNS.
When enabled, the service applies configured address policy during preflight and supplies a custom
lookup; the Axios helper caps redirects, validates direct-IP redirect targets, halts cross-host
auto-follow, and revalidates before the second fetch. The edge records `enforcement_default: disabled`,
`enforcement_mode: configured-opt-in`, `escape_hatch: default-disabled`, and
`proxy_scope: unresolved`. Domain HITL is an independent
governance control and does not convert the address policy into default-on protection.

One Flowise TypeScript edge resolves the Agentflow HTTP node's variable URL through a fixed Axios
request object into `secureAxiosRequest`. The helper's default deny list is enabled unless
`HTTP_SECURITY_CHECK=false`; it normalizes IPv4-mapped IPv6, validates all resolved addresses,
manually validates each bounded redirect, and pins the chosen address through an agent lookup. The
caller supplies none of Axios's transport override fields. Environment proxy routing can still move
destination resolution away from that lookup, so the edge records
`dns_scope: connection-pinned-unless-proxied`, `proxy_scope: environment-dependent`, and a configured
opt-out rather than unconditional protection.

Four additional Python edges record exact string-prefix checks at CrewAI Examples sinks. They target
`path-prefix-check`, carry `weak-string-prefix-validation`, and never satisfy path-boundary policy.
Two checks govern both a parent-directory creation and its write/copy action. The specialized
`AV-FS002` result explains the sibling-prefix weakness without duplicating `AV-FS001` at the same
sink.

Schema v36 records 14 exact MCP-forwarding control edges: one explicit allowlist, three discovery
registries, and ten fixed bindings. The fixed-binding edges split evenly between constructor-bound
instance sources and escaping returned/registered closures. Same-operation retry closures do not
qualify. The ten bindings and discovery registries retain their reviews; only the explicit allowlist
satisfies AV-MCP002's name-policy requirement.

The Python frontend inventories 449 canonical/import/callable-aliased and proven-`Path` mutations:
179 creates, 191 deletes, 46 copies, and 33 moves. Of these, 434 use non-literal path expressions;
one is reached through a statement-ordered local callable alias and 20 are `Path.rename`/`replace`
methods with explicit or immutable receiver proof. That
inventory count is intentionally broader than AV-FS001, which additionally requires an exact tool
edge and a path derived from a tool input. Expanded registry reachability produces 30 filesystem
reviews across ten repositories. Four CrewAI Examples sinks are specialized as AV-FS002, leaving 26
AV-FS001 sites across nine repositories. Fixed paths remain inventory-only, and attribute `.open()`
is treated as filesystem access only for a proven `pathlib.Path` receiver. The Skyvern review is
`resolved.parent.mkdir(...)` in its registered state-save tool: the validator admits equality with an
allowed root, so the parent mutation is not proven to remain inside that root. No pinned mutation
destination has a statically narrow guard, so the corpus records zero guarded calls in this API
subset.

## Implemented syntax

| Frontend | Implemented observations and resolution |
|---|---|
| Python AST | Imports; known agent/model constructors; ordinary tool decorators; import-proven MetaGPT/Qwen registry decorators with literal class entrypoint resolution; literal tool/handoff lists; module-, class-, and repeated-occurrence-qualified agent/tool IDs; shell, Python eval/exec, Playwright/Selenium/Puppeteer-context `.evaluate(...)`, filesystem, Requests/httpx/aiohttp plus import-proven `urllib.request.urlopen` and `Request(url)`, browser, MCP, and Docker SDK calls; browser-page execution context with direct tool-parameter/alias flow, literal discrimination, exact Playwright receiver annotations/aliases, and a provenance-locked Skyvern page factory; canonical, top-level import-aliased, and statement-ordered local callable-aliased `os`/`shutil` create/copy/move/delete mutations with compatible branch merging, destination roles, and rebinding invalidation; `Path.open`/`rename`/`replace` through proven receivers; tool-input filesystem-path state; tool-parameter HTTP origins with direct alias propagation plus fixed-origin constants, instance fields, concatenation, and `.format(...)`; exact fail-closed `urlparse`/`urlsplit` scheme+hostname controls with redirect/DNS scope; source-proven imported secure transports with initial/redirect URL, proxy, DNS, peer, default, and escape-hatch state; unique top-level imported network-function summaries plus iterative single-entrypoint registered-class summaries through direct constructors or immutable fields; absolute and filesystem-relative tool imports; literal approval decorators; OpenAI Agents `ShellTool`/`ApplyPatchTool`/`CustomTool` approval constructors; env-backed auto-approval flags with direct true-return branches and same-class approval short circuits; statement-ordered MCP rejection guards, internal tool-registry routing lookups, same-class rejecting registry-method summaries with literal boolean path selection, immutable constructor-bound imported registry summaries through exact package reexports, constructor-only fixed tool bindings through direct attributes or pure accessors, unchanged captured parameters in returned/registered callbacks, same-function resolved `pathlib.Path.is_relative_to()` or fail-closed `relative_to()` exception boundaries, exact same-class checked-Path return summaries, and non-suppressing string-prefix path checks with dominance and reassignment invalidation; lexically scoped OpenTelemetry spans. |
| TypeScript/JavaScript structural lexical | Known imports/providers; balanced top-level `new Agent({tools: [...]})` entries; `tool(...)`, `functionTool(...)`, `toolNamespace(...)`, OpenAI built-ins, Cline and import-aliased Mastra `createTool(...)`, MCP `registerTool(...)`, and assigned/inline `asTool(...)`; module- and repeated-occurrence-qualified agent/tool IDs; named relative imports and aliases; execution-callback parameter origins for global `fetch` and Axios verbs with direct alias/fixed-host discrimination; bounded summaries for uniquely named same-file free/static network helpers, object-parameter mapping, and multiline destructuring aliases; same-file `new URL(...)` validator policies with always-on scheme and configured-optional hostname scope; default-off service-versus-passthrough SSRF composition through a LangChain tool and Axios lookup/redirect hooks; Flowise variable node URLs through fixed Axios request objects into redirect-validating, address-pinned helpers with proxy residuals; imported filesystem guards whose nested predicate normalizes both paths, uses separator-aware root containment, and rejects before the write, with suppression only for statically narrow literal roots; child-process and Bun `sh -c` calls with literal/dynamic distinction; direct eval; filesystem calls; MCP forwarding object shapes; literal tool approval settings; inline and module-flag env-backed auto-approval branches. Comments, strings, and regex literals are masked before policy matching. |
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
- Python registry classes reexported through exact selected `__init__.py` imports are resolved only
  for immutable constructor-bound attributes. General package reexports, wildcard imports,
  module-qualified or dynamically selected constructors, imported policy objects, callback approval
  results, cross-class approval-attribute flows, and branch-local allowlist proofs remain unresolved.
  Framework/provider/capability names remain taxonomies rather than source symbols.
- MetaGPT/Qwen registry decorators are recognized only through exact direct imports or unchanged
  aliases. Framework reexports, wildcard imports, rebound aliases, computed Qwen names, nonliteral
  MetaGPT entrypoint lists, inherited entrypoints, and indirect method adapters remain unresolved.
- The TypeScript frontend is not an AST/type-checker. Computed property names, conditional tool
  expressions, object-composed Agent options, unrecognized wrapper factories, CommonJS alias flows,
  callback approval results, and type-driven resolution can be missed. Its relative-import resolver
  found zero qualifying real edges in this selected snapshot and is currently regression-validated
  separately from the 81 resolved local tool edges.
- TypeScript network helper flow is same-file and shallow. Arrow-assigned, imported, transitive, or
  duplicate-named helpers, general Axios request objects, computed callback properties, redirects, and
  general hostname-validation helpers remain unresolved.
- TypeScript network-origin policy proof is limited to a unique same-file function with direct
  `new URL(parameter)`, a fail-closed literal scheme set, and an exact/subdomain predicate over one
  immutable normalized environment list with an explicit empty default. Only a direct result
  assignment and immutable aliases propagate; late, rebound, nested-call, scheme-only, imported,
  default-closed, and other predicate shapes remain unresolved.
- TypeScript secure-network composition proof recognizes two exact structural families. The n8n
  family requires a literal boolean default, service-versus-passthrough ternary, two-stage guard
  propagation, LangChain tool factory, and Axios helper with custom lookup plus bounded redirect
  hooks; its proxy scope remains unresolved. The Flowise family requires a CommonJS-registered `INode` class,
  variable URL descriptor and exact `nodeData.inputs.url` flow, fixed request-object URL property,
  default-on deny list, manual redirects, mapped-address normalization, and a pinned agent lookup;
  environment proxy routing remains conditional. Other dependency injection containers, request
  objects, client instances, fetch/Undici transports, reexports, and configuration shapes remain
  unsupported; domain approval is kept independent from address policy.
- Python imported network summaries cover exact named imports of unique top-level free functions and
  direct HTTP calls only. Module-qualified calls, package reexports, nested or transitive helpers,
  client instances, formal-parameter aliases inside the helper, and star imports
  remain unresolved; any observed binding or HTTP-client rebinding invalidates the bounded proof.
- Python urllib coverage requires an exact module-level `urllib`/`urllib.request` import or named
  `urlopen` import. It unwraps only a direct import-proven `Request(url)` expression or immutable
  local assignment. Function-local imports, opener aliases assigned later, custom opener objects,
  redirect policy, and Request factories remain unresolved; module rebinding or any same-function
  shadowing withholds the API identity.
- Python network-origin controls require an exact module-level `urllib.parse` parser import, one
  immutable direct URL alias at most, an immutable parse-result local, and fail-closed static scheme
  plus hostname rejection before the direct request. Late, partial, continuing, rebound, shadowed,
  normalized-expression, positive-branch, and imported-validator forms remain unresolved. The
  control covers the initial origin only; redirect disabling and unresolved redirect/DNS scope are
  preserved separately. Schema v36 observes zero such controls on the Python corpus reviews.
- Python secure-network helper proof requires selected local source for the validator, transport,
  adapter/backend, caller, and any defaults that affect enforcement. One structural family proves
  every redirect, disables proxies, and pins all connections; another distinguishes redirect-disabled
  from bounded each-hop validation and pins only direct connections because environment or caller
  proxies resolve remotely. A third requires default-on global and connector gates, configured
  allowlist/default literal-loopback behavior, DNS-pinning backends, proxy-rejecting transports, and
  ordinary-client fallbacks, and consequently records pinning/proxy rejection only when enforcement
  is active. All require exact named imports and public-address rejection. Other helper shapes,
  missing redirect/proxy/peer/default/composition proof, module-object calls, package reexports, and
  rebound imports remain unresolved; configured opt-outs, exemptions, or proxy residuals never
  become unconditional enforcement.
- Imported class-network propagation is limited to unique registered classes with one entrypoint,
  exact named imports, direct constructor calls or immutable constructor-only `self` fields, and four
  iterations. Reexports, inheritance, local constructor variables, module-qualified calls, multiple
  entrypoints, mutable/dynamic fields, and arbitrary class methods remain unresolved.
- TypeScript path-boundary proof is deliberately narrower than general validator inference. Local or
  dynamically imported guards, prefix-only containment, custom normalization, multiple reassigned
  guard results, and post-write checks remain unresolved.
- Python path-boundary proof is `pathlib`-specific. It covers same-function flow and unique,
  undecorated same-class helpers that return the exact resolved value after a fail-closed check.
  Imported/transitive helpers, duplicate or rebound methods, async/generator helpers, opaque path
  transforms, conditional construction preludes, try `else`/`finally` blocks, module/class root-scope
  inference, nonexclusive or continuing exception guards, non-exact prefix expressions, unresolved
  candidates, and cross-branch aliases remain unresolved. Exact `str(Path).startswith(str(root))`
  checks are reported as weak controls rather than boundaries. Configured roots
  create a control edge but do not suppress `AV-FS001` until their narrow scope is proven.
- Python filesystem mutation resolution covers direct module calls, top-level import aliases, and
  statement-ordered direct/conditional local callable aliases with compatible branch merging.
  Chained callable aliases and imported wrapper helpers remain unresolved. `Path.rename`/`replace`
  require explicit or immutable receiver proof; conditional, reassigned, union-typed, and helper-
  returned receivers remain unresolved rather than matching string/container methods by name.
  Arbitrary attribute `.open()` calls are deliberately excluded unless the receiver is proven to be
  a `pathlib.Path`; configured or fixed write paths remain inventory but do not raise AV-FS001.
- Browser-page evaluation inventories 80 import-context calls, but only seven receivers are proven:
  two exact Playwright-annotated SWE-agent parameters and five Skyvern calls reached from an exact
  imported page factory. The other 73 fixed-script observations retain unresolved receiver state.
  Dynamic promotion also supports one immutable alias of a typed parameter; reassigned annotations
  and ordinary same-module `.evaluate(...)` methods are withheld. Constructor-bound fields, chained
  locators, sanitizers, structured JavaScript builders, imported/transitive helpers, and evaluator
  APIs beyond `.evaluate(...)` remain unresolved.
- Helm templates are not rendered. Kubernetes RBAC, NetworkPolicy, pod scheduling, and the contents
  or sensitivity of mounted paths are not inferred. Compose environment interpolation is not
  evaluated.
- An OpenTelemetry span proves lexical instrumentation only. Exporter configuration, delivery,
  retention, actor attribution, and durable audit storage remain unresolved.
- Selected-path scans parse only selected files. The research corpus adds at most 20 local source
  dependencies to each 220-file root sample: versioned audited evidence hints plus bounded Python
  import closure, all charged against the same cap. This refresh added 152 files across 14 repositories. Unselected definitions
  and controls are not evidence of repository-wide coverage or absence.

## Quality interpretation

The 305-label rule truth set and 218-label IR relationship set are curated regression suites. They
guard known positives and negatives; they are not an unbiased accuracy estimate. A future holdout
must be sampled separately across the categories above, externally reviewed, and kept sealed while
rules change. Until then, precision/recall values apply only to the published seed labels.

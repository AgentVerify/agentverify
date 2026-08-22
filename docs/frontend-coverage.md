# Frontend coverage and known gaps

This document separates implemented syntax from empirical corpus observations. A missing signature
does not mean a repository lacks agents or controls: AgentVerify may not support its language,
framework, wrapper, or configuration path. Counts come from schema-v74
`benchmarks/engine-results.json`, generated from the 71 pinned partial checkouts.

## Empirical coverage by repository category

“With” columns count repositories containing at least one selected-file observation of that Agent IR
kind. Categories and signature kinds can overlap.

| Category | Repositories | Source-bearing | With framework | With provider | With MCP/protocol | With capability |
|---|---:|---:|---:|---:|---:|---:|
| autonomous-agent | 3 | 3 | 2 | 3 | 1 | 3 |
| browser-agent | 3 | 3 | 2 | 3 | 2 | 3 |
| coding-agent | 15 | 15 | 3 | 7 | 8 | 14 |
| computer-agent | 1 | 1 | 0 | 1 | 0 | 1 |
| examples | 2 | 2 | 2 | 2 | 1 | 2 |
| framework | 22 | 22 | 20 | 19 | 19 | 21 |
| mcp | 9 | 9 | 2 | 3 | 8 | 8 |
| observability | 2 | 2 | 2 | 2 | 1 | 2 |
| research-agent | 1 | 1 | 1 | 1 | 1 | 1 |
| sandbox | 2 | 1 | 0 | 0 | 0 | 1 |
| tool-platform | 2 | 2 | 2 | 2 | 2 | 2 |
| visual-platform | 4 | 4 | 1 | 1 | 1 | 3 |
| workflow-agent | 3 | 3 | 2 | 3 | 1 | 3 |
| workflow-platform | 2 | 2 | 1 | 1 | 2 | 2 |
| **Total with observation** | **71** | **70** | **40** | **48** | **47** | **66** |

Observed framework signatures are LangChain (18 repositories), OpenAI Agents SDK (10), LangGraph
(8), LlamaIndex (6), Vercel AI SDK (5), CrewAI (4), Agno (3), Google ADK (3), PydanticAI (3),
Microsoft Agent Framework (2), Semantic Kernel (2), smolagents (2), AgentScope (1), AutoGen (1),
CAMEL (1), Cline SDK (1), Lagent (1), Marvin (1), Mastra (1), MetaGPT (1), and Qwen-Agent (1).
Provider observations are OpenAI (41), Anthropic (17), Google (17), Azure OpenAI (11), AWS Bedrock
and Groq (6 each), Ollama (4), Cohere (3), and Mistral (3). These overlapping exact-import/call,
literal-service, and model-string observations are lower than research-wide lexical signals.

Schema v73 identifies 29 exact Python provider calls across seven repositories: 20 native Mistral,
Groq, Cohere, or Ollama SDK calls and nine LangChain wrappers. Seven calls across five repositories
are production-scoped; 22 calls and all 12 literal call-model arguments occur in tests. These call
facts refine configured use without changing the 48-repository provider-presence total.

Schema v74 adds exact TypeScript call proof for the official Mistral, Groq, and Cohere AI SDK
providers. Named aliases, destructured dynamic imports, provider factories, and immutable configured
instances are supported; rebindings and near-name packages are withheld. The pinned corpus contains
one production dynamic-import Groq model call in Mastra and no test-scoped calls or literal call-model
arguments.

Across the selected snapshot, 9,584 agent/tool observations have module-qualified symbol IDs. Of
4,254 relationship endpoint observations, all 3,486 identified endpoints resolve to an observed
component (3,173 Python and 313 TypeScript). Two former false IDs on CrewAI test edges are now
withheld because a function parameter and assignment shadow the same-named package import.
Repeated Python and TypeScript constructor bindings are occurrence-qualified. Their direct source
edges resolve exactly. Schema v63 records 359 Python lexical-single-definition, 20 same-block
dominating-definition, 25 contextual-absolute-import resolutions, three same-class helper-return
resolutions, 14 contextual imported-class Agent-factory resolutions, 444 inline constructor
resolutions, four context-manager resolutions, four contextual imported-callable exports, six
absolute-import binding edges, and one typed-tool-parameter
resolution. The latter uses an import-proven `ApplyPatchTool` annotation and ten unanimous
same-module constructor call sites to create an occurrence-qualified parameter component that
retains every concrete target ID. No `ambiguous-repeated-binding` target remains in the pinned
corpus; inconsistent, uncalled, rebound, shadowed, reassigned, and non-exact typed fixture forms stay
unresolved.
Literal Python Agent tool lists recover 755 exact role-proven tools: 181 callables, 100
constructor-bound instances, 444 inline constructors, four direct context-manager bindings, 21 exact
Agent-as-tool adapters, and five absolute-import boundary tools. Of these, 526 are outside tests;
they contribute 30 capability edges and 812 exact Agent edges. Each Agent-as-tool adapter has one
exact delegation edge to its same-block Agent receiver. Thirty use immutable module-level definitions. Four imported callables
resolve to exact selected local definitions; unavailable absolute-import sources retain a boundary
identity without inferred capabilities. Imported `from_settings` tool factories, exact
`HostedMCPTool` and `LangchainTool` constructors, and exact same-block `Agent.as_tool()` adapters
resolve the final six former production misses. Across all 1,184 Python Agent→tool edges, all 600
outside tests resolve; the 72 unresolved edges are confined to tests and conservative fixtures.
Import-proven OpenAI `function_tool(function)`
assignments recover 12 wrappers and 12 Agent edges; all are tests, three enable approval, and their
selected bodies add no recognized capability edges. Import-proven Python `ComputerTool`
constructors contribute 15 computer-control assets and ten exact agent links; their optional
`on_safety_check` callback is inventoried separately from generic approval policy. All 15 are local,
two configure the callback, and one occurs outside test paths in the pinned SDK example.
Capability/control taxonomy endpoints intentionally lack
source-symbol IDs, so the endpoint fraction is inventory coverage rather than an accuracy or recall
metric.

The native AI BOM 1.2 resolver independently classifies all 4,254 endpoints: 3,480 by symbol ID, 645
by exact relationship evidence, 23 by a unique display name, 38 as ambiguous, and 68 as unresolved.
Evidence-local resolution removes capability/control ambiguities; occurrence-qualified bindings
resolve repeated source agent/tool observations, and conservative lexical resolution removes further
target ambiguities. The remaining 38 ambiguous endpoints are agent, protocol, control, or tool targets without a unique
local symbol or target location.

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

Eleven Python call sites resolve network behavior through nine unique top-level imported functions.
Qwen's
registered document parser passes its URL into a downloader whose first parameter reaches
`requests.get`; smolagents' visualizer uses a function-local self-import of an image encoder with the
same direct flow. Google ADK contributes nine more calls across two project-local packages whose
absolute imports resolve through one importer-ancestor candidate; five carry dynamic origins and
become AV-NET001 reviews. All eleven create exact network edges, seven with dynamic origins. The
summary requires an
exact named import to a selected file, a unique top-level definition, a recognized direct HTTP call,
and direct formal-parameter origin flow. Fixed origins remain inventory-only. Nested HTTP helpers,
module-object calls, rebound imports or HTTP clients, and function-local reassignment are withheld.

Twenty-five additional CrewAI Agent edges resolve script-root-style imports to eight exact decorated
class-method targets across the Instagram, trip-planner, and landing-page projects. The proof requires
one candidate along the importer's ancestor chain and one matching decorated export; it withholds
missing members, local rebinding, and imports with two possible ancestor candidates.

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
redirect disabling separately from unresolved DNS and redirect scope. The full schema-v65 corpus run
finds zero qualifying controls on the Python AV-NET001 review paths; imported validators and runtime
egress policy remain outside this bounded observation.

Two TypeScript `network-origin-policy` edges are proven. The first governs MCP Servers' gzip resource fetch. Its same-file
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
`proxy_scope: environment-or-caller-dependent`. Schema v38 therefore reports four enabled-default
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
unconditional protection. Schema v38 therefore reports 14 enabled-default Python secure-network edges:
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

Two Flowise TypeScript edges share the same default-on address validator. The Agentflow HTTP node's
variable URL reaches `secureAxiosRequest` through a fixed Axios request object. The helper's default deny list is enabled unless
`HTTP_SECURITY_CHECK=false`; it normalizes IPv4-mapped IPv6, validates all resolved addresses,
manually validates each bounded redirect, and pins the chosen address through an agent lookup. The
caller supplies none of Axios's transport override fields. Environment proxy routing can still move
destination resolution away from that lookup, so the edge records
`dns_scope: connection-pinned-unless-proxied`, `proxy_scope: environment-dependent`, and a configured
opt-out rather than unconditional protection. The Web Scraper tool propagates `_call(initialInput)`
through its same-class recursive methods into `secureFetch`. That helper forces manual redirects and
places a pinned `node-fetch` agent after the caller-option spread on every hop, so its edge records
`dns_scope: connection-pinned`, `proxy_scope: pinned-agent`, and
`transport_scope: caller-agent-overridden`.

Google ADK JS contributes a fourth TypeScript secure-network edge. Its imported `FunctionTool`
passes the model's `url` into `loadWebPage`, which restricts schemes, blocks localhost and explicit
non-global IPv4/IPv6 ranges, validates every preflight DNS answer, normalizes mapped IPv6, and
disables redirects. Global `fetch` resolves again at connection time, so the edge records
`dns_scope: preflight-only-rebinding-residual`, `transport_scope: global-fetch-unpinned`, and
`proxy_scope: unresolved`, not connection pinning.

Activepieces contributes a fifth TypeScript secure-network edge at its configured MCP transport.
The exact import chain reaches `safeHttp.axios.request`, whose Axios instance forces both
`RequestFilteringHttpAgent` and `RequestFilteringHttpsAgent` after caller configuration. The nearest
package manifest pins `request-filtering-agent` 3.2.0. That library validates direct IPs and each DNS
lookup result at connection time; `AP_SSRF_ALLOW_LIST` supplies explicit IP/CIDR exceptions.
Environment proxy routing can move the connection boundary to the proxy, so the edge records
`dns_scope: connection-time-filtered-unless-proxied` and `proxy_scope: environment-dependent` rather
than claiming destination pinning.

Composio adds four more TypeScript secure-network edges through a conditional `#ssrf_guard` package
import. The Node/default implementation validates public resolution on every bounded manual redirect
and uses an Undici dispatcher that reconnects only to validated addresses. Caller dispatchers,
non-stock global dispatchers, and `NODE_USE_ENV_PROXY` routes intentionally retain preflight-only
behavior because the proxy resolves the destination. The edge implementation fails closed for the
caller-selected upload URL, but three `ssrfSafeFetchWhereSupported` API-response transfers fall back
to unguarded edge-runtime fetch. Schema v63 therefore reports nine TypeScript secure-network
controls: the prior five plus one Composio all-runtime/fail-closed edge and three runtime-conditional
edges.

The Composio CLI also contributes one exact unsafe tool path. `ToolsExecutor.execute` maps
`params.arguments` into `uploadToolInputFiles`; schema-marked `file_uploadable` values recurse into
the URL branch and raw global `fetch(url)`. The symbolized tool edge records
`origin_authority: tool-execution-arguments` and `destination_policy: absent-on-proven-path`, raising
the corpus to 23 AV-NET001 reviews across 12 repositories. A guarded transport, fixed argument map,
broken schema gate, or wrong import withholds the path.

Google ADK's generated OpenAPI tools contribute the configured-origin comparison path. The exact
`OpenAPIToolset → OpenApiSpecParser → RestApiTool.runAsync` composition reaches raw global fetch,
but model arguments affect only segment-encoded path, query, header, and body fields. Dot segments
are rejected, server variables resolve from declared defaults or enums, and credential application
only adds headers or query data. The capability therefore records `dynamic_origin: false`,
`origin_authority: openapi-server-configuration`, and a `network-origin-policy` edge rather than an
AV-NET001 review. Six mutations withhold that bounded proof.

A separate A2A endpoint-provenance analysis records four client-construction paths. Google ADK JS
resolves a configured URL, local file, or direct object and passes the resulting card to
`ClientFactory`; Gemini CLI resolves a configured URL or inline JSON and supplies SDK transports
through an Undici agent or configured proxy. In both TypeScript paths, the remotely supplied card can
select the later RPC origin without a proven source-origin binding, so `AV-A2A001` reports two
reviews. Gemini additionally records unpinned dispatcher DNS, configuration-dependent proxying, and
the card-selected gRPC scheme. Google ADK Python provides two guarded paths: before either cached or
per-invocation client construction, it checks every advertised RPC URL, requires HTTPS except an
explicit loopback policy, and binds the endpoint to the network card source origin. Schema v63 thus
separates two unconstrained TypeScript paths from two same-origin-constrained Python paths; configured
card selection is not mislabeled as model-controlled `AV-NET001` input.

Four additional Python edges record exact string-prefix checks at CrewAI Examples sinks. They target
`path-prefix-check`, carry `weak-string-prefix-validation`, and never satisfy path-boundary policy.
Two checks govern both a parent-directory creation and its write/copy action. The specialized
`AV-FS002` result explains the sibling-prefix weakness without duplicating `AV-FS001` at the same
sink.

Schema v63 records 14 exact MCP-forwarding control edges: one explicit allowlist, three discovery
registries, and ten fixed bindings. The fixed-binding edges split evenly between constructor-bound
instance sources and escaping returned/registered closures. Same-operation retry closures do not
qualify. The ten bindings and discovery registries retain their reviews; only the explicit allowlist
satisfies AV-MCP002's name-policy requirement.

OpenAI Agents Python contributes a separate approval-policy composition. The selected sandbox-agent
example binds one directly imported `MCPServerStdio` into `SandboxAgent.mcp_servers`; the SDK default
`require_approval=None` normalizes to `False`, missing per-tool mappings also default false, and the
result is passed into every generated `FunctionTool`. The IR records one agent→MCP-server edge and
one disabled-default `mcp-tool-approval` setting. It intentionally creates no AV-APPROVAL002 result:
the referenced policy tools are not a proven destructive capability, and the rule remains narrower
than a general missing-approval claim.

OpenAI Agents JS contributes the destructive counterpart. Five local filesystem MCP servers are
resolved in the pinned sources: four retain write access and one has an exact static read-only
allowlist. Four servers reach an Agent, producing three `AV-APPROVAL004` reviews; the fourth writable
server is unbound. The pass requires exact SDK source propagation and official imports, and supports
both literal `fullCommand` launchers and `process.execPath` plus import-proven `createRequire.resolve`.

Agno contributes a second destructive Python composition. Three pinned filesystem `MCPTools`
instances reach Agents: two retain mutating tools with the empty default confirmation list and raise
`AV-APPROVAL005`, while one exact `include_tools` list contains only read-only operations. The pass
supports direct command construction and a `StdioServerParameters`/`ClientSession` composition with
exact nested channel flow. A complete static mutation confirmation list becomes a human-approval
control, a partial list remains reviewable, and nonliteral policies remain unresolved.

Semantic Kernel contributes the reverse MCP authority: a server may ask the client to invoke a chat
model. Seven exact plugin bindings reach `ChatCompletionAgent`; six retain the SDK's fail-closed
default and one sets `sampling_auto_approve=True`. The pass verifies callback registration and
precedence, server authority over the system prompt, messages, model hint, temperature, and token
limit, the chat-model call, and the response returned to the server. Callback-controlled and dynamic
policies remain unresolved rather than being credited as human review. The specialized
`AV-MCP004` result replaces the generic auto-approval review at that source location.

The MCP sampling-consent surface adds ten exact handlers across the refreshed corpus: five Python
and five TypeScript. Nine automatically return a result and one is human-confirmed; six automatic
handlers are test-only, so `AV-MCP005` still reports three default-scope examples across two
repositories. Raw Python requires an exact `ClientSession` callback and `mcp.types` result;
PydanticAI additionally resolves four pinned `MCPToolset(sampling_model=...)` tests where the SDK
generates the callback. TypeScript requires an exact MCP `Client`, literal sampling capability,
proven receiver, and balanced `sampling/createMessage` handler. The TypeScript CLI host is the
positive control: it
displays the full request, rejects a negative awaited decision, caps requested tokens, and then calls
the model provider. All ten handlers produce protocol→model-sampling and configured-by edges; the
safe host adds one consent and one token-budget edge.

The separate elicitation surface adds 15 exact handlers: three Python and 12 TypeScript. Ten
automatically return `accept`, two decline, and three are human-confirmed; seven automatic handlers
and both decline-only handlers are under tests, so `AV-MCP006` still reports three default-scope SDK
examples. Six handlers are outside tests: the three reviews, the TypeScript CLI host, the Microsoft
Python tutorial, and FastMCP's CLI client. FastMCP contributes one test where ordinary returned data
is implicitly adapted to `accept`; its production CLI preserves decline/cancel before acceptance.
All 15 produce protocol→user-elicitation and configured-by edges. The three governed clients add
consent edges. The TypeScript host and Microsoft tutorial preserve message/request-detail disclosure,
while FastMCP's CLI proves user confirmation but displays only the request message.
Among the three human-confirmed URL-capable handlers, only the TypeScript SDK host proves full-URL
display. `AV-MCP007` reports the Microsoft Python tutorial and FastMCP CLI separately from automatic
acceptance; it does not claim either handler navigates or opens the URL.

The approval-callback resolver summarizes unique same-file functions and propagates only direct call
edges into an OpenAI built-in tool's configured approval handler. Python covers a named handler and
one transitive wrapper; TypeScript covers inline handlers that call a summarized helper. The IR adds
`tool configured-by control-setting:auto-approval` only when the helper has an unconditional true
return under an approval-specific enabled environment comparison. Schema v63 resolves three pinned
tools and three configuration edges. Unused helpers, safe callbacks, ambiguous function names, and
hosted/container shell tools do not produce `AV-APPROVAL003`.

The Python frontend inventories 449 canonical/import/callable-aliased and proven-`Path` mutations:
179 creates, 191 deletes, 46 copies, and 33 moves. Of these, 434 use non-literal path expressions;
one is reached through a statement-ordered local callable alias and 20 are `Path.rename`/`replace`
methods with explicit or immutable receiver proof. That
inventory count is intentionally broader than AV-FS001, which additionally requires an exact tool
edge and a path derived from a tool input. Expanded registry and literal tool-role reachability produces
36 filesystem reviews across ten repositories. Four CrewAI Examples sinks are specialized as
AV-FS002, leaving 32 AV-FS001 sites across nine repositories. Four newly reachable Marvin sinks
cover dynamic writes and deletion configured through module-level callable tools. Fixed paths remain inventory-only, and attribute `.open()`
is treated as filesystem access only for a proven `pathlib.Path` receiver. The Skyvern review is
`resolved.parent.mkdir(...)` in its registered state-save tool: the validator admits equality with an
allowed root, so the parent mutation is not proven to remain inside that root. No pinned mutation
destination has a statically narrow guard, so the corpus records zero guarded calls in this API
subset.

## Implemented syntax

| Frontend | Implemented observations and resolution |
|---|---|
| Python AST | Imports; known agent/model constructors; ordinary tool decorators; import-proven MetaGPT/Qwen registry decorators with literal class entrypoint resolution; literal tool/handoff lists with exact local and immutable module callables, exact selected local or absolute-SDK import bindings, import-proven constructor bindings, occurrence-qualified inline constructors, direct context-manager bindings, and OpenAI `function_tool(function)` wrapper recovery; exact same-class direct/tuple Agent-return propagation into caller composition; import-proven OpenAI built-in typed parameters with unanimous same-module constructor call sites; module-, class-, parameter-, and repeated-occurrence-qualified agent/tool IDs; shell, Python eval/exec, Playwright/Selenium/Puppeteer-context `.evaluate(...)`, filesystem, Requests/httpx/aiohttp plus import-proven `urllib.request.urlopen` and `Request(url)`, browser, MCP, and Docker SDK calls; import-bound MCP launcher constructors plus literal nested `mcpServers` dictionaries, including literal argument prefixes and exact npm/Python package pin state; exact Semantic Kernel MCP sampling callback/default/model-authority composition and exact MCP `ClientSession` sampling result/consent callbacks; browser-page execution context with direct tool-parameter/alias flow, literal discrimination, exact Playwright receiver annotations/aliases, and a provenance-locked Skyvern page factory; canonical, top-level import-aliased, and statement-ordered local callable-aliased `os`/`shutil` create/copy/move/delete mutations with compatible branch merging, destination roles, and rebinding invalidation; `Path.open`/`rename`/`replace` through proven receivers; tool-input filesystem-path state; tool-parameter HTTP origins with direct alias propagation plus fixed-origin constants, instance fields, concatenation, and `.format(...)`; exact fail-closed `urlparse`/`urlsplit` scheme+hostname controls with redirect/DNS scope; source-proven imported secure transports with initial/redirect URL, proxy, DNS, peer, default, and escape-hatch state; unique top-level imported network-function summaries plus iterative single-entrypoint registered-class summaries through direct constructors or immutable fields; repository-unique, filesystem-relative, and importer-ancestor-single-path absolute imports with exact decorated class-tool export validation; literal approval decorators; OpenAI Agents `ShellTool`/`ApplyPatchTool`/`CustomTool` approval constructors plus `ComputerTool` computer-control and safety-check-callback inventory; env-backed auto-approval flags with direct true-return branches and same-class approval short circuits; statement-ordered MCP rejection guards, internal tool-registry routing lookups, same-class rejecting registry-method summaries with literal boolean path selection, immutable constructor-bound imported registry summaries through exact package reexports, constructor-only fixed tool bindings through direct attributes or pure accessors, unchanged captured parameters in returned/registered callbacks, same-function resolved `pathlib.Path.is_relative_to()` or fail-closed `relative_to()` exception boundaries, exact same-class checked-Path return summaries, and non-suppressing string-prefix path checks with dominance and reassignment invalidation; lexically scoped OpenTelemetry spans; exact Google ADK `Runner`/`PluginManager` tool callbacks composed with the BigQuery Agent Analytics Storage Write sink; exact Skyvern Task v3 recordable dispatch/callback composition into its committed SQLAlchemy `actions` table. |
| TypeScript/JavaScript structural lexical | Known imports/providers; balanced top-level `new Agent({tools: [...]})` entries; `tool(...)`, `functionTool(...)`, `toolNamespace(...)`, OpenAI built-ins, Cline and import-aliased Mastra `createTool(...)`, MCP `registerTool(...)`, and assigned/inline `asTool(...)`; module- and repeated-occurrence-qualified agent/tool IDs; named relative imports and aliases; import-proven `StdioClientTransport` and literal `mcpServers` package launchers with literal argument prefixes and pin/auto-install state; exact MCP client `sampling/createMessage` result, consent, disclosure, and token-budget handlers; execution-callback parameter origins for global `fetch`, direct Axios aliases, and immutable same-file Axios instances with verb/`.request(...)`, fixed-base, and `allowAbsoluteUrls` discrimination; bounded summaries for uniquely named same-file free/static network helpers, object-parameter mapping, and multiline destructuring aliases; same-file `new URL(...)` validator policies with always-on scheme and configured-optional hostname scope; default-off service-versus-passthrough SSRF composition through a LangChain tool and Axios lookup/redirect hooks; Flowise variable node URLs through either fixed Axios request objects with proxy residuals or an exact Web Scraper class chain into manual `node-fetch` redirects with a post-spread pinned agent; Activepieces imported filtering-Axios composition with manifest-pinned agents and proxy residual; Composio conditional-runtime safe-fetch composition with Undici pinning and edge fallback state plus its separate schema-gated CLI tool-upload flow to raw fetch; Google ADK OpenAPI tool generation with spec-configured origin, encoded model path segments, declared server-variable values, and query-only credential URL mutation; imported filesystem guards whose nested predicate normalizes both paths, uses separator-aware root containment, and rejects before the write, with suppression only for statically narrow literal roots; child-process and Bun `sh -c` calls with literal/dynamic distinction; direct eval; filesystem calls; MCP forwarding object shapes; literal tool approval settings; inline and module-flag env-backed auto-approval branches. Comments, strings, and regex literals are masked before policy matching. |
| MCP JSON | Common `mcpServers` configuration, transport/command/URL, redacted arguments, environment-variable names, and literal `npx`/`uvx` package/version/auto-install state. Configuration is read as data; servers are never launched. |
| Container configuration | Compose/devcontainer Docker socket, privileged/host network/root mounts, and exact short-syntax host credential binds; Kubernetes/Helm privileged, host namespace, privilege escalation, service-account token, and `hostPath`; literal privileged Python Docker SDK calls. |

Cross-file structural passes additionally cover ADK JS's import-proven AgentCard resolver, Gemini
CLI's Undici agent/proxy dispatcher, and ADK Python's all-interface HTTPS/loopback plus same-origin
validation before A2A client construction. These exact families produce `a2a-rpc` capability and
`a2a-card-rpc-origin-policy` control edges independently of model-controlled URL analysis.
The Activepieces pass separately proves the exact `safeHttp` named import, filtering-agent package
pin and construction, and MCP transport/entry flow before emitting its configured-origin capability
and `network-ssrf-policy` edge.

## Explicitly unsupported or unresolved

- Go, Rust, Java, C#, Ruby, shell, and other language source frontends are not implemented. Their
  repositories may still contribute supported JSON/YAML or embedded Python/TypeScript files.
- Framework taxonomy recognizes exact Python/TypeScript imports for Google ADK, Semantic Kernel,
  LlamaIndex, Agno, Mastra, smolagents, Microsoft Agent Framework, CAMEL, Qwen-Agent, Lagent,
  MetaGPT, Marvin, AgentScope, and Vercel AI SDK alongside the original signatures. The `ai` package
  is TypeScript-only evidence. Package reexports, Pydantic wrappers beyond direct imports, and custom
  agent bases may still leave a generic `Agent` without framework attribution.
- Google provider taxonomy requires an exact GenAI/Vertex/AI SDK import or a Gemini model prefix.
  AWS Bedrock requires its exact TypeScript runtime SDK, a recognized `langchain_aws` constructor
  import, or a literal `bedrock-runtime` service selection. Mistral, Groq, Cohere, and Ollama support
  exact Python SDK imports plus import/alias-proven native and LangChain wrapper calls. Rebinding
  withholds call attribution. The official Mistral, Groq, and Cohere TypeScript AI SDK providers also
  support exact named/dynamic imports, factories, and immutable configured instances; community
  Ollama providers are not conflated. Literal call-model arguments inherit the proven provider, and
  selected Mistral-owned prefixes are recognized; third-party model names hosted by Groq or Ollama,
  indirect factories, and reexports remain unresolved.
- Python registry classes reexported through exact selected `__init__.py` imports are resolved only
  for immutable constructor-bound attributes. General package reexports, wildcard imports,
  module-qualified or dynamically selected constructors, imported policy objects, callback approval
  results, cross-class approval-attribute flows, and branch-local allowlist proofs remain unresolved.
  Framework/provider/capability names remain taxonomies rather than source symbols.
- MCP package launchers require literal `npx`/`uvx` commands in MCP JSON, literal nested Python or
  TypeScript `mcpServers` objects, or known constructors imported from an MCP module/package. The
  TypeScript constructor proof is limited to an unchanged named `StdioClientTransport` import from
  `@modelcontextprotocol/sdk`; dynamic package selection, shell wrappers, `npx --package`/`--call`,
  module-qualified, shadowed, or rebound constructors,
  arbitrary command strings, and non-exact version ranges remain unresolved. `npx` is automatic
  only with `-y`/`--yes`; `--no-install` and prompt/cache-only invocation remain inventory negatives.
- Semantic Kernel MCP sampling proof requires the pinned callback/default/model-call propagation,
  exact plugin and `ChatCompletionAgent` imports, a directly bound async context, and a literal
  plugin list. Assigned/transitive plugin containers, reexports, other MCP clients, callback decision
  logic, model quotas, and runtime server trust remain unresolved. A configured callback is not
  assumed to be human consent.
- Generic MCP sampling consent requires exact Python or TypeScript client imports, a literal
  TypeScript sampling capability, a direct named Python async callback or inline TypeScript arrow
  handler, and an exact sampling-result shape. The PydanticAI adapter additionally recognizes an
  immutable direct `MCPToolset` import with a non-null `sampling_model` and no conflicting handler.
  Python methods/classes, callback aliases, normalized decision variables, nested decision blocks,
  TypeScript named handler functions, receiver fields, alternate UI libraries, and indirect budget
  propagation remain unresolved. A decision after provider invocation is not a governing control.
  The rule describes automatic protocol fulfilment; a canned example
  is not claimed to have spent model quota.
- Generic MCP elicitation consent requires exact Python or TypeScript client imports, literal
  `ElicitResult`/returned action objects, a literal TypeScript elicitation capability, and an immutable
  connected receiver. Direct awaited input/confirmation can govern later accepting branches; one unique local
  imported TypeScript helper is supported when it collects input and preserves decline/cancel.
  FastMCP direct returns are recognized through its implicit-accept adapter, but rebound handlers or
  response factories remain unresolved. Python methods, TypeScript named handlers, client factories, stateful
  decisions, other UI APIs, multi-round-trip input-required responses, and indirect helpers remain
  unresolved. URL validation and navigation safety remain separate from the consent edge.
- MetaGPT/Qwen registry decorators are recognized only through exact direct imports or unchanged
  aliases. Framework reexports, wildcard imports, rebound aliases, computed Qwen names, nonliteral
  MetaGPT entrypoint lists, inherited entrypoints, and indirect method adapters remain unresolved.
- The TypeScript frontend is not an AST/type-checker. Computed property names, conditional tool
  expressions, object-composed Agent options, unrecognized wrapper factories, CommonJS alias flows,
  callback approval results, and type-driven resolution can be missed. Its relative-import resolver
  found zero qualifying real edges in this selected snapshot and is currently regression-validated
  separately from the 81 resolved local tool edges.
- TypeScript network helper flow is same-file and shallow. Immutable same-file Axios instances are
  recognized, including direct verbs, `.request(...)`, `baseURL`, and literal
  `allowAbsoluteUrls: false`; the generic instance syntax has regression-fixture coverage but no
  occurrence in the selected real snapshot. Arrow-assigned, imported or transitive helpers, general
  cross-file request objects, mutated instances, interceptors, computed configuration/callback
  properties, redirects, and general hostname-validation helpers remain unresolved.
- TypeScript network-origin policy proof is limited to a unique same-file function with direct
  `new URL(parameter)`, a fail-closed literal scheme set, and an exact/subdomain predicate over one
  immutable normalized environment list with an explicit empty default. Only a direct result
  assignment and immutable aliases propagate; late, rebound, nested-call, scheme-only, imported,
  default-closed, and other predicate shapes remain unresolved. A separate exact Google ADK OpenAPI
  composition proves configured-origin retention; it does not generalize to arbitrary OpenAPI
  generators, server overrides, request middleware, or credential handlers.
- TypeScript secure-network composition proof recognizes six exact structural families. The n8n
  family requires a literal boolean default, service-versus-passthrough ternary, two-stage guard
  propagation, LangChain tool factory, and Axios helper with custom lookup plus bounded redirect
  hooks; its proxy scope remains unresolved. The Flowise Axios family requires a CommonJS-registered `INode` class,
  variable URL descriptor and exact `nodeData.inputs.url` flow, fixed request-object URL property,
  default-on deny list, manual redirects, mapped-address normalization, and a pinned agent lookup;
  environment proxy routing remains conditional. The Flowise `node-fetch` family requires the exact
  `Tool` subclass, direct or one-star-barrel helper import, and three-method parameter chain plus
  manual redirects and a post-spread pinned agent. The Google ADK family requires the exact imported
  `FunctionTool`, URL callback, public-address preflight, mapped-IP normalization, and disabled
  redirects; its global fetch remains unpinned. The Activepieces family requires its exact named
  `safeHttp` import, MCP transport chain, manifest-pinned `request-filtering-agent` 3.2.0, both agents
  after caller options, and no caller proxy/agent override; configured IP/CIDR exceptions and
  environment-proxy dependence remain explicit. The Composio family additionally requires the
  conditional package-import map, both Node and edge helpers, pinned Undici dispatcher, all-address
  validation, and bounded manual redirects; configured routes and the edge-runtime unguarded
  fallback remain explicit. Other dependency injection containers, imported clients,
  mutable/general instances, request objects, global fetch or Undici transports beyond the exact
  Gemini A2A and Composio dispatchers, reexports, and configuration shapes remain
  unsupported; domain approval is kept independent from address policy.
- A2A card endpoint proof is limited to the two exact TypeScript SDK compositions and ADK Python's
  exact validation methods. Other SDK versions, custom factories, interface negotiation, redirects,
  authenticated/extended-card replacement, DNS pinning, proxy behavior, and non-HTTP transports are
  unresolved unless explicitly recorded; configured card sources are not model-controlled origins.
- Python imported network summaries cover exact named imports of unique top-level free functions and
  direct HTTP calls only. Absolute imports may use one exact importer-ancestor candidate; multiple
  candidates remain unresolved. Module-qualified calls, package reexports, nested or transitive helpers,
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
  preserved separately. Schema v63 observes zero such controls on the Python corpus reviews.
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
  or sensitivity of arbitrary mounted paths are not inferred. Compose credential classification is
  limited to short-syntax bind sources with exact sensitive path segments; long-syntax mounts,
  Windows paths, interpolation beyond `$HOME`/`${HOME}`, and credential contents are unresolved.
- An OpenTelemetry span proves lexical instrumentation only; exporter configuration, delivery,
  retention, actor attribution, and durable storage remain unresolved. The exact Google ADK
  BigQuery Agent Analytics composition proves attributable durable storage, but its delivery remains
  best-effort with drop accounting, retention is unresolved, and nonliteral plugin filters/config are
  conservatively withheld. Skyvern Task v3 proves one production durable execution record for
  billable/recordable browser actions, but its post-action persistence is best-effort and
  `created_by` is nullable and unset, so actor attribution remains unresolved.
- Selected-path scans parse only selected files. The research corpus adds at most 20 local source
  dependencies to each 220-file root sample: versioned audited evidence hints plus bounded Python
  import closure, all charged against the same cap. This refresh added 176 files across 21 repositories. Unselected definitions
  and controls are not evidence of repository-wide coverage or absence.

## Quality interpretation

The 511-label rule truth set and 652-label IR component/relationship set are curated regression
suites. They guard known positives and negatives; they are not an unbiased accuracy estimate. A
future holdout must be sampled separately across the categories above, externally reviewed, and kept
sealed while rules change. Until then, precision/recall values apply only to the published seed
labels.

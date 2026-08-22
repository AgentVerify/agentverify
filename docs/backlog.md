# Issue-ready backlog

Items are ordered by evidence-backed roadmap priority. They are written to become GitHub issues once
the local repository has an approved remote.

## P0 — framework and provider taxonomy

Schema v63 retains fourteen recurring framework families and six provider families beyond the
original taxonomy. The selected corpus now reports framework evidence in 40 repositories and
provider evidence in 49. New exact-import observations include Vercel AI SDK in five repositories,
Microsoft Agent Framework in two, and CAMEL, Qwen-Agent, Lagent, MetaGPT, Marvin, and AgentScope in
one each. Groq appears in seven repositories, Ollama in five, and Mistral, Cohere, and xAI in three
each.
Python and TypeScript signatures are separated so the TypeScript-only `ai` package does not classify
a Python import. Google model attribution additionally accepts Gemini prefixes, while Bedrock
requires an exact runtime SDK/import or literal `bedrock-runtime` service selection. Schema v73 adds
import- and rebinding-aware native SDK calls plus exact LangChain wrappers for Mistral, Groq, Cohere,
and Ollama. Literal model arguments inherit that constructor proof, while Mistral-owned prefixes are
recognized separately; Groq/Ollama third-party model IDs do not establish provider identity alone.
Schema v74 adds official TypeScript AI SDK imports, dynamic imports, factories, immutable configured
instances, and direct model calls for Mistral, Groq, and Cohere. Schema v75 adds AgentScope's public
Ollama model reexport plus exact PydanticAI provider, model, and embedding wrappers. Schema v76 maps
the AgentScope module's OpenAI Chat/Responses, Anthropic, Gemini, and Ollama exports independently.
Schema v100 extends that symbol-specific map to the exact `DashScopeChatModel`, `DeepSeekChatModel`,
`MoonshotChatModel`, and `XAIChatModel` exports. The pinned AgentScope sample adds nine production
calls and literal models: four Alibaba DashScope, one DeepSeek, two Moonshot AI, and two xAI.
Schema v101 adds exact PydanticAI Anthropic, Google/Google Cloud, AWS Bedrock, xAI, and DeepSeek
provider, model, and embedding modules. It deliberately excludes the generic OpenAI-compatible
model/provider wrappers, which the corpus configures for Azure, DeepSeek, AIMLAPI, and custom
gateways. Schema v102 adds exact Agno public/direct model modules for OpenAI Chat/Responses, Google
Gemini, Anthropic Claude, Azure OpenAI, and Groq. Both `id=` and positional literal model IDs are
accepted only for those model wrappers; rebinding or a custom OpenAI/Groq `base_url` withholds
attribution. Schema v103 expands official TypeScript AI SDK call proof to OpenAI, Anthropic, Google,
and xAI, including direct, dynamic, image, factory-created, and inline embedding forms. A factory is
accepted only with no arguments or a literal, spread-free configuration without `baseURL`; generic
compatible packages, unknown configs, rebindings, and custom endpoints remain unresolved. The 318
component labels pin 237 local/real positives and 81 unrelated, rebound, custom-endpoint, or
near-name negatives. Schema v104 adds exact ESM constructors from the native OpenAI, Anthropic, and
Google GenAI TypeScript SDKs. No-argument or literal spread-free default-endpoint configuration is
required; CommonJS imports, unknown or custom-endpoint configs, and rebound constructors remain
unresolved. The 337 component labels now pin 247 positives and 90 negatives.
Schema v105 admits the observed CommonJS default-export form only for one immutable module-level
`const Client = require(exact-package)` binding from the OpenAI or Anthropic SDK. Four GPT Pilot
template calls expand the native TypeScript total to 21; rebound bindings and custom or unknown
configs remain excluded. The 348 component labels now pin 253 positives and 95 negatives.
Schema v106 follows an immutable native SDK constructor result into exact OpenAI
`chat.completions.create`/`responses.create`, Anthropic `messages.create`, or Google
`models.generateContent` calls. Only a direct literal `model` property is promoted; rebound clients,
nonliteral request objects, unrelated methods, and typed-parameter flow remain unresolved. Three
pinned OpenAI calls add exact model identity, and the 369 component labels now pin 271 positives and
98 negatives.
Schema v107 distinguishes TypeScript type references from real parameter shadowing and propagates
native provider identity through unique, non-exported same-file functions only when every direct
call site resolves to the same exact default-endpoint constructor and the function never escapes as
a value. A fixed-point pass covers the
four-hop OpenAI Agents JS helper chain; exported functions, mixed/unproven call sites, rootless
cycles, and actual constructor-name parameters remain unresolved. It also recovers one Anthropic
constructor previously hidden by qualified SDK types. The 381 component labels now pin 278
positives and 103 negatives.
Next generalize selected package reexports without trusting generic `Client` names or
framework-adjacent packages.

## P0 — module-qualified symbols and graph identities

Python and TypeScript agent/tool components now carry module-qualified IDs, including Python class
methods, built-in tools, tool namespaces, and Cline/OpenAI inline factories. The structure-aware
TypeScript tools-array reader resolves all 81 observed agent-to-tool edges and 14 agent-as-tool
delegations in the pinned sample without treating nested tokens as tools. Repeated constructor and
decorated-tool bindings now receive occurrence-qualified IDs for exact source edges. Python target
references are scope-aware for unique and repeated names; repeated targets resolve for a single
direct, earlier definition in the same lexical/module scope, plus an exact single-mutation definition
that dominates use in the same branch/with body.
Schema v63 additionally inventories 15 import-proven OpenAI Agents Python `ComputerTool` instances
and resolves ten agent links to them, including three formerly ambiguous repeated bindings. Literal
Python Agent tool lists now recover 755 exact role-proven tools: 181 callable definitions, 100
constructor-bound instances, 444 inline constructors, four direct context-manager bindings, 21
Agent-as-tool adapters, and five absolute-import boundary tools. They produce 812 exact Agent links;
526 tools are outside tests and 30 capability edges become reachable. Constructor promotion requires
one immutable import from a module whose path establishes a tool namespace, while local subclasses
require an exact imported tool base. Exact imported `from_settings` factories are limited to a
known method on a role-proven class; `HostedMCPTool`, `LangchainTool`, and `Agent.as_tool()` use
separate exact adapter proofs. Four of the callable
tools resolve through one exact selected local export; three unavailable SDK definitions remain
explicit import-boundary identities with no inferred capabilities. These proofs resolve the final
six former default-scope misses. The benchmark now reports zero unresolved among 610 non-test Python
Agent→tool edges; all 70 unresolved edges occur in tests or conservative fixtures. Import-proven OpenAI
`function_tool(function)` assignments now recover 12 exact wrapper tools and Agent edges, including
the two repeated SDK targets; three enable approval and all occur under tests. Exact same-class
direct/tuple Agent-return summaries resolve three CrewAI composition edges to two source Agent
definitions. Exact imported-class summaries additionally resolve 14 production CrewAI delegations
across four example projects. Each proof requires one contextual import path, one exact class export,
an immutable same-block instance, and a unique undecorated method that directly returns an Agent;
the edge retains the imported Agent symbol and file. The final repeated-binding miss now resolves through an occurrence-qualified typed
parameter only when its OpenAI built-in annotation is import-proven and every direct same-module
call site supplies the same exact constructor type. The pinned `ApplyPatchTool` helper records ten
verified call sites and ten concrete target IDs without selecting one runtime instance or inheriting
instance-specific policy. Schema v82 resolves the final two `ambiguous-repeated-binding` targets by
proving eight test-scoped OpenAI handoff edges through two unique same-block local Agent factories.
Conditional/indirect returns, forward or rebound helpers, constructor shadowing, result mutation,
cross-branch flow, inconsistent/untyped parameters, external receivers, and lambdas stay withheld.
Schema v83 adds five exact-import OpenAI `LocalShellTool` test assets, five shell-capability edges,
and four resolved Agent links while explicitly recording that the SDK exposes no approval parameter.
Two resumed-state references remain ambiguous instead of selecting a repeated tool occurrence.
Schema v84 adds five exact-import OpenAI `CodeInterpreterTool` assets across two repositories, five
hosted-sandbox code-execution edges, and two production Agent links. Literal auto-container configs
are distinguished from symbolic/casted unresolved configs; neither becomes an AV-EXEC002 finding.
Schema v85 adds 13 exact provider-hosted OpenAI web-search, file-search, and image-generation assets
across three repositories, with 13 capability edges, seven production assets, and eight resolved
Agent links. Hosted configuration state is preserved without treating provider execution as local
network reachability or inventing approval controls.
Next add broader
branch/reassignment dataflow and resolve Python/TS package re-exports, wildcard imports, other
wrapper factories, and type-driven symbols. Schema v77 already gives exact IDs to import-proven
assigned Python MCP stdio servers and resolves direct literal `mcp_servers=[server]` lists only
under same-block dominance; forward, rebound, indirect-list, and module-global-to-function flows
remain explicit negatives. Schema v78 resolves the module-global case only for one earlier immutable
assignment with no lexical shadowing, and adds exact `fastmcp`/`mcp.server` in-process server
constructors. Conditional definitions, indirect containers, local imports, and other server
frameworks remain future work. Schema v79 narrowly resolves a top-level fail-closed `try` import and
links immutable FastMCP registrars to exact registered tools, enabling
Agent→server→tool→capability context. Optional imports, general control-flow imports, rebound
registrars, and cross-file server/tool registration remain unresolved.
Schema v80 resolves exact MCP constructors bound by `with`/`async with` only for a direct in-body
Agent use before rebinding, and gives exact-import OpenAI `SandboxAgent` calls stable identities.
Duplicate or escaped context bindings, prior reassignment, near-module Agent imports, nested Agent
statements, and indirect server containers remain unresolved.
Contextual absolute-import proof additionally resolves 25 project-local CrewAI Agent-to-class-tool
edges across eight exact decorated method targets, the 14 Agent-factory delegations, and nine Google
ADK imported-helper network call sites. Multiple ancestor candidates, missing exports, reimports,
indirect returns, inheritance, dynamic lookup, and any receiver/result rebinding stay unresolved.
Preserve unresolved state for ambiguity and validate on larger real monorepository graphs.

Exact module-level Python `mcp.tool(...)(function)` applications now resolve through unique local or
relative-imported definitions when both registrar and target bindings are immutable. The pinned
Skyvern module contributes 115 recovered tools and 22 capability edges. Twenty-two tools pass through
structurally proven metadata-preserving forwarders, including one two-wrapper chain. Next support
package reexports and additional wrapper forms without falling back to display-name matching.

Python browser-page execution now inventories import-gated `.evaluate(...)` calls and promotes only
direct tool-parameter/alias script flow. Dynamic calls additionally require an exact Playwright
receiver annotation, one immutable alias of that parameter, or Skyvern's exact imported `get_page`
factory result. Schema v86 adds exact class/`__init__` Playwright annotations and immutable
`TYPE_CHECKING` imports, proving 15 more production receivers across CAMEL, LaVague, and MetaGPT.
Schema v87 additionally proves 13 Devika receivers through an exact imported Playwright runtime,
straight-line browser/context construction, one immutable `self.page` assignment in `__init__`, and
one immutable local alias. Thirty-five of 80 corpus receivers are now proven and the other 45
fixed-script observations retain explicit unresolved state. Conditional, later, repeated, near-factory,
and shadowed-factory bindings remain negative. Before chained-call inventory, Skyvern contributed 30
evaluator observations but one finding; normalized numeric scroll JavaScript remains inventory-only.
Schema v88 structurally
inventories six chained evaluators that the earlier dotted-name gate missed and proves one Skyvern
Locator chain rooted in `get_page`. Schema v89 proves one exact Playwright-returning property in
OpenAI Agents Python and three straight-line local page constructions in Aider and Skyvern, bringing
the totals to 40 proven of 86 and 46 unresolved. Schema v90 proves Browser-Use's uniquely annotated
module page through a fail-closed dependency guard and same-branch Locator assignment, bringing the
`.evaluate(...)` totals to 41 proven and 45 unresolved. Schema v91 extends structural inventory to
Playwright `evaluate_handle(...)`, `eval_on_selector(...)`, `eval_on_selector_all(...)`, and Locator
`evaluate_all(...)`, with API-specific script positions and exact `expression=` keyword handling.
The pinned corpus adds seven alternate-API observations, all from Skyvern tests: three locally
constructed pages are proven and four remain unresolved. Current browser-evaluator totals are 44
proven of 93 and 49 unresolved; the API split is 86 `evaluate`, five `eval_on_selector`, and two
`eval_on_selector_all` calls. A dynamic selector paired with a fixed script remains inventory-only,
and production code without selected-file Playwright provenance is deliberately excluded. The sole
dynamic production path and all 51 `AV-EXEC002` findings are unchanged. Known
Playwright locator/get-by/filter/nth/and/or/first/last derivations and immutable aliases are supported, while
ordinary same-named and unknown derivations stay negative. Schema v92 additionally summarizes a
unique local `@contextlib.asynccontextmanager` only when it contains one exact Playwright
runtime→browser→context→page chain and one unconditional page yield. Four Skyvern test consumers
move from unresolved to `local-playwright-contextmanager-yield`, bringing current totals to 48
proven of 93 and 45 unresolved; branch-dependent, ordinary-object, and reassigned yields remain
withheld. Schema v93 additionally accepts exact `typing.Literal`-bounded browser selection through
`getattr(playwright_runtime, self.browser_type)` and propagates the resulting local browser through
private same-class helper parameters only when every direct or immutable bound-method-alias call
agrees. This proves two fixed-script MetaGPT production evaluators, bringing current totals to 50
proven of 93 and 43 unresolved. Mixed calls, mutable or escaped aliases, invalid selector literals,
external calls, and mutable lifecycle flows remain withheld; findings remain unchanged.
Schema v94 accepts one narrower lifecycle form: a field initialized exactly once to `None` in
`__init__`, then assigned exactly once by a straight-line async
Playwright-runtime→browser→page chain in one undecorated method. Three Devika production evaluators
move to `lifecycle-bound-playwright-page`, bringing totals to 53 proven of 93 and 40 unresolved.
Conditional initialization, any page/browser reassignment, and shadowed factories remain withheld.
Schema v95 propagates exact local context-manager pages into private top-level helpers only when
every selected-module call passes such a page directly. Three Skyvern test evaluators move to
`same-module-contextmanager-page-parameter`, bringing totals to 56 proven of 93 and 37 unresolved.
Mixed calls, function escape, lambda-hidden calls, and caller-local helper or factory shadowing remain
withheld.
Schema v96 proves branching lifecycle fields only when every non-`None` assignment stays on an exact
Playwright runtime→browser/context→page graph, including exact popup page events. Twelve CAMEL
production evaluators move to `branching-lifecycle-playwright-page`, bringing totals to 68 proven of
93 and 25 unresolved. Unknown or tuple field writes, dynamic `setattr`, non-popup events, and
shadowed runtime factories remain withheld.
Schema v97 resolves Skyvern's exact imported-page wrapper scope only when the receiver comes from the
pinned `get_page` factory and an unshadowed built-in `getattr` selects exactly `_locator_scope` or
falls back through `.page` to the same receiver. One production evaluator moves to
`imported-browser-wrapper-scope`, bringing totals to 69 proven of 93 and 24 unresolved. Wrong
attributes or fallbacks, shadowed `getattr`, and assignments that do not dominate the evaluator stay
unresolved.
Schema v98 indexes exact Playwright-annotated fields on uniquely defined imported classes. A consumer
must resolve one unrebound class import, annotate an immutable parameter with that class, and copy
the field into one immutable local. Skyvern's popup content-type probe moves to
`imported-class-playwright-field-alias`, bringing totals to 70 proven of 93 and 23 unresolved.
Ordinary or duplicate fields, near or rebound imports, and reassigned context parameters or aliases
stay unresolved.
Schema v99 indexes undecorated sync/async methods with exact Playwright receiver return annotations
on those same uniquely imported classes. The call mode must match, the typed context and one local
alias must remain immutable, and the assignment must dominate the evaluator. An immutable outer
parameter may flow into a nested closure only when it is not shadowed or declared `nonlocal`.
Skyvern's page-fingerprint probe moves to `imported-class-playwright-method-return-alias`, bringing
totals to 71 proven of 93 and 22 unresolved. Ordinary, duplicate, decorated, rebound, mode-mismatched,
branch-only, shadowed, and nonlocal-mutated forms remain unresolved.
Next resolve inherited fields, additional bounded wrapper/locator flows, sanitizer and bounded builder
summaries, and imported helper flow without treating every dynamic JavaScript expression as
tool-controlled.

## P0 — configuration and policy resolution

Resolve environment defaults, config objects, CLI flags, MCP allowlists, tool policies, and approval
overrides into control edges. Suppress `AV-MCP002` and `AV-FS001` only when the resolved policy governs
the exact reachable path. Same-function MCP rejection guards and uncaught internal tool-registry
lookups are statement-ordered, so later checks cannot govern earlier calls. A bounded imported
TypeScript path guard now suppresses `AV-FS001` only when a normalized, separator-aware roots
predicate rejects before the write and its roots are a statically narrow literal set. MCP Servers'
dynamic CLI/MCP roots retain a review plus an explicit unresolved-scope control edge. Python now
resolves statement-ordered `Path.resolve()` plus `is_relative_to()` boundaries, including positive
branch-local and fail-closed guards. Literal narrow roots may suppress; configured roots retain the
review, and prefix checks or reassignment remain unresolved. Next resolve imported policy objects,
and bounded root constants without widening name-based inference. Fail-closed `relative_to()`
exception guards now require an exclusive check plus a terminating ValueError handler; continuing
handlers, mixed try bodies, and parent writes remain negative. Unique same-class helpers now
propagate an exact checked-and-returned Path into callers while preserving unresolved root scope;
duplicate/rebound methods, opaque transforms, and changed return values remain negative. Next add
bounded imported helper summaries and root-scope resolution without trusting semantic names.
Exact Python `str(resolved).startswith(str(root))` guards now remain non-suppressing weak-control
edges and receive the specialized `AV-FS002` review; checks after a sink and separator-aware forms
remain negative. Next recognize additional component-aware weak patterns only when a real reachable
sink justifies them.
Python filesystem inventory now models canonical and import-aliased `os`/`shutil` create, copy,
move, replace, and delete calls, using the destination rather than the source for two-path APIs.
Statement-ordered local callable aliases now cover direct assignments, conditional expressions, and
compatible branch-local `copy`/`copy2` choices. Calls before assignment, conditionally rebound
wrappers, and incompatible operation choices remain negative. Proven `Path.rename`/`Path.replace`
receivers now cover explicit constructors, exact Path annotations, and single immutable derived
locals while rejecting conditional, reassigned, and shadowed bindings. Next resolve chained callable
aliases and imported filesystem wrappers without matching arbitrary same-named methods.
Constructor-only MCP wrapper fields, pure accessors, and unchanged parameters captured by
returned/registered callbacks now produce fixed-binding edges. Mutable fields, rebound parameters,
and same-operation retry closures remain unresolved. Same-class methods and immutable
constructor-bound imported registry managers now summarize exact `get_tool`-then-reject paths. The
collector retains a bounded dependency closure so the imported proof is reproducible. Next resolve
aliased/module-qualified constructors and deeper manager composition, without treating class names
or discovery as authorization.
Keep unresolved distinct from absent.

## P0 — approval coverage rule

`AV-APPROVAL002` now reports the narrow provable subset where an Agent directly reaches a local
OpenAI Agents Python or TypeScript shell tool and its SDK approval is explicitly or default-disabled.
It remains a review: an executor may enforce an equivalent internal control. Promote absence to a
finding only when the complete destructive path and executor policy are resolved. `AV-APPROVAL003`
now resolves the complementary positive policy flow: a reachable local shell or apply-patch tool's
same-file approval callback transitively reaches an environment-backed branch that returns true.
Three pinned Python/TypeScript SDK examples qualify; safe callbacks, unbound helpers, and hosted
shells remain negative. Next extend coverage to delegated agents and other frameworks without
treating callbacks or automatic handlers as absent controls. The exact OpenAI Agents Python MCP
composition inventories the opposite policy state:
an omitted `MCPServerStdio.require_approval` becomes `False` and is copied to every discovered
`FunctionTool`. It remains non-finding inventory until a destructive MCP capability is resolved.
`AV-APPROVAL004` now covers that destructive subset for OpenAI Agents JS: a directly reachable local
filesystem MCP package, SDK-default-disabled approval, and no proven static read-only filter.
`AV-APPROVAL005` resolves the Agno counterpart: omitted or incomplete
`requires_confirmation_tools` on a reachable filesystem `MCPTools` instance is reviewable, a list
covering all known mutations is controlled, and a static read-only `include_tools` list is a
counterexample. Dynamic confirmation lists remain unresolved. Next generalize package capability
manifests and approval mediation without inferring writes from names.

Semantic Kernel adds a different MCP authority direction: the server can request a client-side model
completion. Schema v68 proves the callback registration, fail-closed default, callback precedence,
server-controlled prompt/model hint/sampling parameters, model invocation, and response returned to
the server. `AV-MCP004` reports the one reachable sample that explicitly enables
`sampling_auto_approve`; six reachable default-denied bindings add exact consent-policy controls.
Schema v69 generalizes the client side through exact MCP Python `ClientSession` callbacks and
TypeScript `Client.setRequestHandler('sampling/createMessage', ...)` handlers. Three default-scope
examples automatically return sampling responses without a proven user decision. The TypeScript SDK
host is the counterexample: it displays the full request, fails closed on an awaited confirmation,
caps server-requested tokens, and only then calls the provider. Named external callbacks, unrelated
imports, disconnected receivers, and complex approval logic remain unresolved. Schema v70 resolves
the separate elicitation authority through exact
Python `elicitation_callback` and TypeScript `elicitation/create` registrations. Three TypeScript SDK
examples synthesize `accept` without direct user input; the SDK CLI host proves both an inline URL
confirmation and an imported form collector, while the Microsoft Python tutorial proves a
fail-closed interactive decision. Schema v71 adds two exact framework adapters: PydanticAI
`MCPToolset(sampling_model=...)` installs an SDK-generated sampling handler, while FastMCP maps a
non-`ElicitResult` handler return to protocol `accept`. Pinned test paths expose both automatic
behaviors without changing the three default-scope findings per rule; FastMCP's production CLI
remains human-confirmed and records only message disclosure. Next cover multi-round-trip
input-required configuration and indirect UI helpers without treating an
`accept` test fixture as proof of deployment.

Schema v72 separates URL disclosure from consent. `AV-MCP007` reports two human-confirmed clients
that advertise URL elicitation but do not show the server-provided URL: the Microsoft tutorial and
FastMCP CLI. The TypeScript SDK host is the governed comparison because it displays the full URL,
rejects unsafe schemes/origins, and asks before opening. Next model domain highlighting, Punycode
warnings, browser isolation, and navigation sinks without inferring navigation from acceptance alone.

## P1 — sandbox containment quality

Kubernetes privileged mode, host network/PID/IPC, service-account token mounts, explicit privilege
escalation, arbitrary `hostPath` mounts, and literal privileged Docker SDK calls are covered alongside
Compose. Schema v63 additionally reports exact short-syntax host credential binds for SSH, cloud,
cluster, registry, package-manager, netrc, and Git credential paths. Goose contributes one pinned
read-only `~/.ssh` mount; read-only prevents mutation but not credential use or exfiltration. Named
volumes, `.gitconfig`, near-name paths, and ordinary workspace binds remain negative. Next resolve
network policy, Linux capabilities, device passthrough, long-syntax binds, and rendered-template
semantics. Model containment as a control attached to the exact code/shell capability.

## P1 — network destination policy

`AV-NET001` now reports Python and structurally resolved TypeScript tool parameters and their direct
aliases when they determine the HTTP origin. Literal URLs and formatted URLs with a fixed scheme and
host remain inventory-only; Python fixed-origin state propagates through module constants, immutable
instance fields, concatenation, and `.format(...)`. TypeScript coverage includes Mastra `createTool` object properties and
MCP `registerTool` callbacks with exact tool identities. Unique same-file free/static network helpers
now propagate positional/destructured parameter flow to exact tool edges. Python additionally resolves
unique top-level functions through exact named local imports when one of their parameters directly
controls a recognized HTTP origin; local rebinding, nested helpers, and module-object calls remain
unresolved. Single-entrypoint registered classes now propagate that proven behavior through exact
direct construction or immutable constructor-bound fields for up to four graph layers. Mutable
fields, module-qualified constructors, ambiguous classes, and rebound/shadowed constructors remain
unresolved. Exact module-level `urllib.request.urlopen` imports and aliases now add network inventory;
`Request(url)` is unwrapped so a fixed host plus a dynamic query stays inventory-only, while local
shadowing and module rebinding invalidate the API proof.
Exact same-function Python `urlparse`/`urlsplit` guards now add a control edge only when immutable
tool-origin data is rejected outside a static scheme and hostname set before the request. Redirect
disabling is recorded separately; DNS and other redirect states stay unresolved. The current schema finds
zero such controls on the Python corpus reviews, making the absence visible without calling every review
SSRF. A same-file TypeScript validator summary now resolves MCP Servers' scheme allowlist and
environment-backed exact/subdomain predicate, while preserving its empty hostname default as open.
The current schema separately proves two CrewAI loader calls through a locally defined `safe_get` transport:
both validate every redirect hop, pin the connected peer after DNS checks, disable proxies, and are
enabled by default. The `CREWAI_TOOLS_ALLOW_UNSAFE_PATHS` opt-out and
`CREWAI_TOOLS_FORCE_SAFE_PATHS` override remain explicit governance state. Next resolve normalized
predicates and other imported validators or transports without generalizing from names. Two Composio
session-file calls are also proven, but retain proxy-dependent DNS pinning as an explicit residual:
one disables redirects and one validates each bounded hop. Ten Langflow connector call sites are now
proven through default-on settings, explicit opt-out gates, a configured allowlist and default
literal-loopback exemption, and DNS-pinned/proxy-rejecting transports when enforcement is active.
n8n's AI Builder `web_fetch` path now resolves from its CLI composition root through the injected
guard to Axios: protection defaults off, the disabled branch is a real passthrough, enabled requests
use preflight validation, a custom lookup, and bounded redirect hooks, while proxy behavior remains
unresolved and independent domain HITL does not satisfy address policy. Flowise's Agentflow HTTP node
now resolves its variable URL through a fixed Axios request object into a default-on helper that
normalizes mapped addresses, validates each redirect, and pins direct DNS; environment proxy routing
and the explicit opt-out remain residuals. Its Web Scraper path also resolves through `secureFetch`,
whose post-spread pinned agent overrides caller transport options on every validated hop. Google ADK
JS's `LOAD_WEB_PAGE` now preserves the opposite transport state: always-on public-address preflight
and disabled redirects, but unpinned global fetch with a DNS-rebinding residual. Immutable same-file
Axios instances now preserve verb/`.request(...)` flow and `allowAbsoluteUrls: false` origin locking.
Activepieces' configured MCP transport additionally resolves through imported `safeHttp.axios` into
`request-filtering-agent` 3.2.0: both HTTP agents are forced after caller options and filter each
direct connection, while `AP_SSRF_ALLOW_LIST` exceptions and environment-proxy routing remain
explicit. Composio's TypeScript guard now proves four imported fetch paths through a default Node
backend that validates every redirect and pins an Undici dispatcher unless a caller/global/env route
is configured. Its edge backend fails closed for caller URL uploads but deliberately leaves three
`WhereSupported` API-response transfers unguarded. The CLI's separate tool-file pipeline now proves
an actionable gap: schema-marked `params.arguments` recursively reach raw global fetch for URL file
inputs, producing one AV-NET001 review. Google ADK's generated OpenAPI tools provide the
configured-origin counterexample: model path values are segment-encoded with dot segments rejected,
server variables come only from declared defaults/enums, and credential application changes headers
or query parameters without replacing the origin. Next resolve general imported clients,
mutated/interceptor-configured instances, other fetch/Undici dispatchers, and runtime egress controls.

## P1 — A2A AgentCard endpoint provenance

`AV-A2A001` distinguishes configured card discovery from the downstream origin selected by a
remotely supplied AgentCard. Exact TypeScript compositions cover Google ADK JS and Gemini CLI; both
pass the resolved card into `ClientFactory` without a proven source-origin binding. Gemini's edge
also preserves its Undici agent/proxy choice, unpinned DNS state, and insecure-gRPC possibility.
Google ADK Python is the guarded counterexample: both cached and per-invocation client paths validate
every advertised RPC interface, require HTTPS except explicit loopback development, and bind it to
the network card source origin before client construction. Next generalize across A2A SDK versions,
custom client factories, redirect policy, and authenticated-card replacement without converting
configuration-controlled card URLs into model-controlled SSRF findings.

## P1 — consequential-action audit coverage

Lexically scoped OpenTelemetry spans create action-level instrumentation edges without treating
imports or sibling spans as coverage. An exact Google ADK Python composition now proves tool callback
identity through `Runner` and `PluginManager` into the BigQuery Agent Analytics Storage Write sink,
including start/completed/error events and actor/session/invocation attribution. The pinned corpus has
one available framework control and two test deployments, but no production deployment; delivery is
best-effort with drop accounting. Skyvern Task v3 adds one production action-record deployment: its
post-dispatch callback commits completed/failed browser-action rows with organization/workflow/task/
step/action identity, but `created_by` is nullable and unset and persistence failures are contained.
`AV-AUDIT001` is now enabled only for this explicit durable-record/actor-gap edge; generic untraced or
unrecorded actions remain unresolved rather than findings. Next cover more framework middleware/
exporters, actor identity, retention, and loss guarantees before generalizing the rule.

## P1 — benchmark truth set

The curated regression set has reached 642 pinned positive/negative locations, with 1,175 separately
scored IR component/relationship labels. Schema-v107 engine results and
`docs/frontend-coverage.md` publish category-stratified observations and unsupported syntax. Next
create a separately sampled, externally reviewed holdout set and keep its labels sealed until rule
changes are complete. Keep discovery sampling metrics separate from detection-quality metrics.

## P2 — CI adoption workflow

The repository now includes a GitHub code-scanning workflow and copy-ready SARIF upload guidance
with a stable category, an auditable `--paths-from` mode for changed-file scans, and baseline diff
counts that avoid false resolution claims on partial scans. Machine-readable CI artifacts use the
first-class `--output`/`-o` path instead of shell redirection; write failures are explicit usage
errors while policy and severity gate exits remain intact. Inline suppressions now retain optional
expiry status, and CI can require an active ISO date. A distributable pre-commit manifest and local
setup are included; publishing its remote form waits for an approved repository URL and release tag.
Schema-backed JSON policies now provide per-rule/result-kind/severity count budgets with decision
evidence in every report. Local organization policy composition resolves relative files depth first,
rejects cycles and duplicate gate IDs, and preserves file and gate SHA-256 provenance without
weakening strict unknown-field validation. Next add signed policy provenance with explicit trust-root
configuration; a content hash alone must not be presented as author authenticity.

## P2 — AI BOM standards adapters

The native schema-backed AI BOM 1.2 now preserves assets, relationships, evidence, governance,
composed-policy source provenance, summaries, risks, and ambiguous identities without information
loss. Exact relationship evidence
resolves capability/control endpoints while genuinely ambiguous agent/tool references remain explicit.
Next design separately validated CycloneDX
and SPDX AI-profile adapters. Map only concepts supported by the target specification and retain a
link to the native evidence graph rather than presenting agent-specific extensions as standard fields.

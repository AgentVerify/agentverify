# Initial findings

These findings describe the bounded 71-repository corpus scan, not universal ecosystem prevalence.
Counts are repository-level presence signals. Candidate-risk matches require rule-specific triage.

## 1. Privileged actions are the norm

69/71 repositories contain browser, filesystem, code, or shell-execution signals; 42 contain at
least three of those four capability classes. Shell execution appears in 42 repositories and
writable-filesystem operations in 59. Agent discovery therefore needs a capability and trust-boundary
inventory before it attempts policy judgments.

The initial matcher found `shell=True` in eight repositories. Reviewable examples include:

- [Aider](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/editor.py#L134)
- [Trae Agent](https://github.com/bytedance/trae-agent/blob/e839e559ac61bdd0e057c375dd1dee391fee797d/trae_agent/tools/bash_tool.py#L44)
- [MetaGPT](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/tools/libs/shell.py#L51)
- [SWE-agent](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/environment/repo.py#L115)

The links are locked corpus snapshots; only an explicit collector `--refresh` pins newer commits.

Schema v63 reports 20 exact container/host boundary reviews across ten repositories. The new pinned
case is Goose's development container mounting the developer's entire
[`~/.ssh` directory read-only](https://github.com/block/goose/blob/48d480f91163bbcdc0f69f01befa3841a93a1d3e/documentation/docs/docker/docker-compose.yml#L15).
Read-only prevents the container from changing a private key but does not prevent an agent from using
or exfiltrating it. The adjacent `.gitconfig` bind, named volumes, `.ssh-public`, and ordinary
workspace binds are explicit negatives; the rule requires a host-source credential path rather than
inferring sensitivity from the container destination.

Filesystem mutation is broader than `open()` and `write_text()`. Schema v63 resolves 449 Python
filesystem mutations in selected files: 179 creates, 191 deletes, 46 copies, and 33 moves. The move
inventory includes 20 `Path.rename`/`Path.replace` calls proven through explicit constructors or
immutable Path-derived bindings, including ChatDev's
[`source_path.rename(target_path)`](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/server/services/workflow_storage.py#L137).
Exact tool reachability narrows this inventory to 36 filesystem reviews across ten repositories:
32 generic AV-FS001 sites across nine repositories and four specialized AV-FS002 sites in CrewAI
Examples. Literal role proof newly exposes four Marvin dynamic write/delete sinks whose callable
definitions are immutable module globals referenced from a nested Agent configuration. Other newly exposed cases include ArcadeAI's
[`os.replace`/`shutil.move` destination branches](https://github.com/ArcadeAI/arcade-ai/blob/597debaa1593b54172061ce36a414cc29aa8fc6a/examples/mcp_servers/local_filesystem/src/local_filesystem/tools.py#L287-L301)
and its [conditional `copy`/`copy2` callable](https://github.com/ArcadeAI/arcade-ai/blob/597debaa1593b54172061ce36a414cc29aa8fc6a/examples/mcp_servers/local_filesystem/src/local_filesystem/tools.py#L329-L331),
and CrewAI Examples'
[`copytree` destination](https://github.com/crewAIInc/crewAI-examples/blob/da94a91e691e1cf5b3151416bb15b5b62729bea8/crews/landing_page_generator/src/landing_page_generator/tools/template_tools.py#L86-L90).
That copy and three sibling sinks rely on `str(resolved).startswith(str(root))`; schema v65 preserves
the checks as weak, non-suppressing control edges because string prefixes do not enforce path-component
boundaries. AV-FS002 takes precedence at those sinks and recommends `Path.is_relative_to`,
`Path.relative_to`, or `os.path.commonpath`.
The direct-callable recovery also exposes Marvin's `write_summary_of_work` and `write_file`
functions: both accept a dynamic path and are passed literally to an Agent. Skyvern's separate
additional review comes from post-definition FastMCP registration. Exact relative
import resolution links `skyvern_state_save` to its body and exposes
[`resolved.parent.mkdir(...)`](https://github.com/Skyvern-AI/skyvern/blob/486c8975e9864a53037d4701b781f8619e698c40/skyvern/cli/mcp_tools/state.py#L89).
Its validator admits a candidate equal to an allowed root, so the parent operation lacks a proven
descendant boundary. Across Skyvern, 115 recovered registrations—including 22 through structurally
proven transparent wrappers—yield only 21 capability edges and
this one additional filesystem review.
The IR records the destination—not the source—as the governed path for two-path APIs. Import aliases
are resolved only when unshadowed; string `.replace()` calls and caller-shadowed `shutil` names are
regression negatives.

Browser-page evaluation is a separate execution boundary. Schema v63 inventories 80
import-context `.evaluate(...)` calls across the corpus and proves seven receivers: two exact
Playwright `Page` parameters in SWE-agent and five exact imported Skyvern page-factory results. The
remaining 73 fixed-script observations retain explicit unresolved receiver state. Only one proven
receiver is directly controlled by a tool parameter: Skyvern's registered
[`skyvern_evaluate`](https://github.com/Skyvern-AI/skyvern/blob/486c8975e9864a53037d4701b781f8619e698c40/skyvern/cli/mcp_tools/browser.py#L2458).
That exact post-definition tool edge raises `AV-EXEC002` to 51 findings across 15 repositories.
Skyvern's scroll evaluator at line 1664 is a real negative because the generated JavaScript contains
only normalized numeric intermediates. Literal scripts, an ordinary `.evaluate` method even inside
a browser-import context, and a reassigned typed page are pinned negatives; dynamic syntax and an
ambient browser import alone are not treated as tool flow.

Decorator provenance materially changes reachability. Exact MetaGPT and Qwen-Agent `register_tool`
imports recover 56 registry tools—five functions and 51 classes—and 26 capability edges from 34
resolved entrypoints. MetaGPT's literal class `include_functions` and Qwen's literal name plus direct
`call` method keep helper methods out of the graph. The added reachability exposes four MetaGPT
filesystem reviews and two Qwen network-origin reviews. Rebound aliases, unrelated decorators,
nonliteral entrypoint selections, fixed write paths, and fixed HTTP origins are regression negatives;
the scanner does not treat a familiar decorator name as proof by itself.

## 2. MCP creates a cross-process trust boundary

MCP signals occur in 50 repositories. Seventeen contain generic tool-call forwarding shapes, and 17
MCP-positive repositories had no allowlist term in the bounded sample. The latter number is a triage
queue, not proof that allowlist enforcement is missing.

Representative forwarding shapes occur in
[Goose](https://github.com/block/goose), [CrewAI](https://github.com/crewAIInc/crewAI),
[Semantic Kernel](https://github.com/microsoft/semantic-kernel), and
[AutoGPT](https://github.com/Significant-Gravitas/AutoGPT). AgentVerify should resolve the configured
server, discovered tool set, transport, authentication, argument flow, and enclosing approval policy.

The structure-aware engine retains every selected dynamic forwarding capability and reports 49 for
review across 23 repositories. The MCP Python SDK's `SessionGroup` path is proven to be governed by
an internal tool registry: two uncaught mapping lookups occur before forwarding, so unknown names
terminate before the call. This routing fact is represented as an Agent IR edge but does not suppress
the review, because the registry contains server-advertised tools rather than an explicit
authorization policy. Caller-owned mappings and post-call lookups remain unresolved.

Five additional calls across CrewAI, Lagent, AgentScope, and Trae bind the forwarded name once in a
wrapper constructor. The engine records exact `fixed-tool-binding` edges—including pure property and
getter accessors—but retains all five reviews because per-instance routing is not an authorization
allowlist and does not constrain the argument map. A mutable local regression prevents class-wide
name matching from inventing this control.

Five more calls bind a tool source through an escaping callback: three browser-use actions are
registered and two ArcadeAI wrappers are returned. Equivalent retry closures in the MCP Python SDK
and FastMCP do not qualify because the public caller still selects the name for each operation.
Schema v64 therefore reports five instance and five closure fixed-binding edges, without suppressing
any review.

FastMCP adds an interprocedural routing fact: its middleware recursion reaches a same-class callee
that resolves `get_tool(name)`, rejects a missing tool, and only then executes. The literal
`run_middleware=False` call argument proves that the earlier recursive return is bypassed and is
retained as a required edge argument. This becomes the second `tool-registry` edge. A default-tool
fallback remains unresolved, demonstrating why semantic names are not enforcement evidence.

The collector's bounded dependency closure and audited evidence hints add 168 local source files
across 18 repositories. It
exposes the MCP Python SDK's `ToolManager` reexport and implementation: `MCPServer` binds one imported
manager in its constructor, and that manager resolves `get_tool(name)` and rejects a miss before
execution. This is the third routing-only `tool-registry` edge. Mutable manager fields, fallback
managers, and rebound constructor imports are regression negatives. The same dependency refresh
exposes six OpenAI Agents SDK forwarding reviews and CAMEL's parameter-fed `exec` helper; both new
rule observations are pinned in the 423-label truth set.

MCP configuration is also executable dependency configuration. Schema v65 resolves 50 literal
`npx`/`uvx` package launchers in the bounded corpus: 45 unpinned, three floating, and two exact,
spanning 23 Python and 27 TypeScript observations. Thirty-four default-scope automatic installs
across Marvin, Qwen-Agent, Agno, CAMEL, and the TypeScript SDK raise `AV-MCP003`; the two exact pins
occur together in an OpenHands SDK example and remain inventory-only. The TypeScript SDK examples
mostly auto-install unpinned `tsx` to execute local server source, so this is a mutable launcher-
dependency fact, not a claim that `tsx` is the server implementation.
The rule requires MCP structure and literal package selection, so ordinary package scripts,
prompt/cache-only `npx`, `--no-install`, and dynamic launcher expressions are not promoted. This is a
dependency-review signal, not evidence that a named package or registry is compromised.

## 3. Approval exists, but bypass behavior recurs

Human-approval vocabulary appears in 52 repositories, while auto-approval or skip-confirmation
vocabulary appears in 18. Some matches are deliberately safe tests or demonstrations; others are
production configuration. A useful analyzer must model approval scope and bypass paths rather than
only checking whether an approval API exists.

OpenAI Agents Python demonstrates why disabled policy inventory and findings must remain separate.
Its selected sandbox-agent example omits `MCPServerStdio.require_approval`; the SDK normalizes the
`None` default to `False`, uses false for missing per-tool mappings, and passes the result to each
generated MCP `FunctionTool`. AgentVerify records the exact agent→server binding and disabled-default
setting, but does not emit AV-APPROVAL002 because the example's policy tools are not a proven
destructive capability. Two negative rule labels and three IR labels pin that distinction.

The structure-aware engine reports 15 default-scope approval-bypass reviews. Eight are explicit
environment-enabled approval short circuits in pinned OpenAI Agents Python/JavaScript examples; the
remaining seven are enabled configuration candidates found previously. Examples are not treated as
vulnerabilities, but they prove that deployment-time approval overrides recur in real agent code and
need auditable policy. Status flags and branches with an additional safety condition are regression
negatives.

Schema v64 promotes three of those reviews into a separate demonstrated flow without redefining the
examples as vulnerabilities. OpenAI Agents Python's local shell callback reaches
`SHELL_AUTO_APPROVE`; OpenAI Agents JS has the corresponding local-shell flow and an apply-patch
callback reaching `APPLY_PATCH_AUTO_APPROVE`. In each case the engine proves the same-file callback
chain, the privileged built-in tool, and a resolved Agent-to-tool edge. Safe callbacks, unused
environment helpers, manual HITL, and hosted/container shells are exact negatives. `AV-APPROVAL003`
therefore has three positive and six negative pinned rule labels plus six positive and two negative
IR labels.

## 4. Provider identity is a governance dependency

OpenAI signals appear in 51 repositories, Anthropic in 37, Google in 28, Azure OpenAI in 18, and AWS
Bedrock in 14. Forty-four repositories contain two or more provider signals. An AI bill of
materials should report providers and model configuration even when no security issue is present.
The stricter schema-v65 engine promotes a subset only when selected source proves an exact SDK
import, literal service selection, or recognized model prefix: OpenAI appears in 41 repositories,
Google and Anthropic in 17 each, Azure OpenAI in 11, AWS Bedrock in six, Groq in five, Ollama in
four, and Mistral and Cohere in three each. The four added SDK families enrich provider identity but
do not increase the 48-repository provider-presence total because each occurs alongside another
recognized provider. The difference from the research-wide lexical census is retained as
unsupported/unselected evidence, not silently upgraded.

## 5. Controls are layered

Sandboxing vocabulary appears in 64 repositories, audit/tracing in 57, human approval in 52, and
allowlisting in 39. These controls live in infrastructure, framework middleware, configuration, or
individual tool wrappers. The Agent IR must preserve which control governs which action instead of
producing repository-wide flags. One pinned MCP Servers write now demonstrates why exact control
edges matter: its imported validator normalizes candidate and root paths, rejects separator-aware
boundary failures before `mkdir`, and is represented as a `path-boundary` control rather than a
repository-wide “filesystem safe” flag. Its configured root scope remains unresolved, so the review
is retained rather than treating the presence of validation as sufficient policy.
ChatDev contributes the Python exception form: its local-tool creation route resolves a candidate,
calls [`target_path.relative_to(tools_dir)`](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/server/routes/tools.py#L58),
and terminates the `ValueError` handler before writing. Schema v63 records this as a distinct
`Path.relative_to` control edge with unresolved root scope; handlers that continue are not controls.
OpenAI Agents Python demonstrates the interprocedural variant: its `_resolve()` helper returns the
same checked Path to create, update, and delete callers. Three sink edges retain the helper's exact
check location and `same-class-return` provenance. The configured root remains unresolved, and
duplicate/rebound helpers or changed returns do not qualify.

Audit evidence has the same layering problem. Tracing vocabulary appears in 57 repositories, but a
generic span does not prove durable or attributable records. In pinned Google ADK Python source, the
BigQuery Agent Analytics plugin receives tool start/completed/error callbacks through `Runner` and
`PluginManager`, records event, agent, user, session, invocation, and tool identity, and writes through
the BigQuery Storage Write API. Schema v63 therefore records one available durable audit control and
one storage edge. Both observed compositions are tests, however: production deployments and governed
production external actions are zero, delivery is best-effort with drop accounting, and retention is
unresolved. Skyvern supplies the production comparison: its Task v3 loop records each billable or
recordable browser action after dispatch and commits an `ActionModel` row with organization,
workflow, task, step, type, status, and ordering fields. Schema v63 records one production
`durable-action-record`, one governed external action, and one SQL storage edge. The record is not a
fully attributable audit because `created_by` is nullable and unset in this path, and callback/database
failures are contained. Schema v63 raises one `AV-AUDIT001` review only on that explicit production
actor gap. It does not infer a finding for generic unrecorded actions, OpenTelemetry instrumentation,
or the attributable ADK control; two positive and two negative labels pin that narrow contract.

## 6. Tool configuration needs structure, not token matching

Real TypeScript Agent configurations place tool arrays beside nested instructions, callbacks,
schemas, and runtime options. A token-level audit of the pinned sample produced hundreds of apparent
tool names such as `async`, `return`, and words from descriptions. Balanced top-level parsing reduces
the observed graph to 95 evidence-backed agent edges: 14 agent-as-tool delegations and 81 tool edges,
all 81 resolving to an observed component.

Framework-specific wrappers also carry security meaning. The Cline SDK example wraps
[`Bun.spawn(["sh", "-c", input.command])`](https://github.com/cline/cline/blob/80b3b0348e694bafc48e3dcd70154de3cf4289d9/apps/examples/cli-agent/src/index.ts#L19)
inside an inline `createTool`; recognizing only the outer `Agent` would miss the reachable dynamic
shell path. OpenAI Agents JS similarly expresses multi-agent delegation through both inline and
assigned `asTool()` adapters. Frontend coverage therefore needs conservative structural parsing plus
framework-qualified factories, not a growing bag of identifier regexes.

## 7. Governance exports need evidence-local identity

Display-name-only AI BOM resolution produced 1,299 ambiguous relationship endpoints in the pinned
corpus. The current schema resolves 521 endpoints by exact relationship evidence. Reused Python
and TypeScript bindings were a second identity failure: one file-level ID could describe many
constructor occurrences. Occurrence-qualified IDs resolve all 688 source agent/tool ambiguities, and
141 unsafe target IDs become unresolved instead of pointing at multiple assets. Intermediate
benchmark schema v5 recorded all 289 target references whose duplicated raw binding ID was withheld.
Schema v63 resolves 359 repeated-name targets from one earlier lexical definition, 20 targets from a
sole same-block assignment or callable definition, three CrewAI composition edges from exact
same-class direct/tuple Agent returns, 14 production CrewAI composition edges from exact imported
class Agent factories, and the final repeated-binding miss through an exact typed
tool-parameter abstraction. The OpenAI helper's import-proven `ApplyPatchTool` annotation agrees
with all ten direct same-module constructor call sites, so the parameter receives its own source ID
and records all ten possible concrete target IDs rather than selecting one occurrence. Import-proven OpenAI Agents Python
`ComputerTool` constructors add 15 computer-control assets and ten exact agent links; three of those
links replace ambiguous repeated bindings. All 15 observed instances are local, two configure a
safety-check callback, and only one is outside test paths. Literal Agent tool lists additionally
recover 753 role-proven tool components: 181 callables, 100 constructor-bound instances, 444 inline
constructors, two direct context-manager bindings, 21 Agent-as-tool adapters, and five absolute-import
boundary tools. They create 810 exact Agent edges; 524 tools are outside tests and 30 capability edges
become reachable. Each Agent-as-tool adapter delegates to one exact same-block Agent receiver.
Four imported callable definitions resolve through exact local exports; three unavailable production
SDK sources remain import-boundary identities without inferred capabilities. Exact imported
`from_settings` factories, `HostedMCPTool` and `LangchainTool` constructors, and same-block
`Agent.as_tool()` adapters resolve those final six former production misses. All 598 non-test Python
Agent→tool edges now resolve; 72 unresolved edges remain only in tests and conservative fixtures.
Import-proven OpenAI `function_tool(function)` assignments
recover 12 wrapper tools and 12 exact Agent edges; three enable approval, all occur under tests, and
their selected bodies add no capability edges. Twenty-five project-local CrewAI class-tool imports
resolve through one importer-ancestor path and one exact decorated export. The 14 factory edges span
four production example projects and require one exact imported class, immutable local construction,
and a direct Agent return. The final export resolves 3,371 endpoints by symbol ID, 544 by exact
evidence location, and 18 by unique display name; 29 remain ambiguous control/tool targets, and 68
unresolved. No `ambiguous-repeated-binding` target remains in the pinned corpus;
cross-branch, forward, inconsistent/untyped parameters, conditional/transformed returns,
external receivers, shadowed factories, lambdas, and reassigned fixture cases stay unresolved. Two apparent CrewAI
re-export misses were false identities:
a function parameter and a local assignment shadowed the imported `tool` binding. Scope-isolating
module and function imports now withhold those IDs, so all 3,371 identified endpoints resolve.
A governance export that collapses those references
by name would silently attach controls or risks to the wrong asset.

## 8. Dynamic network origin is rarer but high impact

Twenty-three default-scope tool paths in the bounded corpus pass a tool parameter directly or through a
resolved function/class helper to an HTTP origin: [Goose's Wikipedia MCP tool](https://github.com/block/goose/blob/48d480f91163bbcdc0f69f01befa3841a93a1d3e/examples/mcp-wiki/src/mcp_wiki/server.py#L29)
and [AgentOps' smolagents webpage tool](https://github.com/AgentOps-AI/agentops/blob/f8e907b92dabe47232978023fdcb01e2a7d4b752/examples/smolagents/multi_smolagents_system.py#L73),
the MCP TypeScript SDK's [registered `fetch-data` tool](https://github.com/modelcontextprotocol/typescript-sdk/blob/3924de99df834302d89f5997a1b64ca268282284/packages/server/src/server/mcp.examples.ts#L130-L138),
Mastra's [helper-backed `httpRequest` tool](https://github.com/mastra-ai/mastra/blob/1da5fb00e141b78c2148b21ee085ec24112cf2a5/packages/agent-builder/src/defaults.ts#L1045),
MCP Servers' [helper-backed gzip resource fetch](https://github.com/modelcontextprotocol/servers/blob/599dafc1054550a6eeb87a6545c1e1b03b3ca827/src/everything/tools/gzip-file-as-resource.ts#L85),
two Qwen-Agent registry tools that fetch caller-selected remote image URLs, Qwen's registered
document parser calling an exact imported downloader, smolagents' visualizer calling a
function-local self-imported image encoder, and five Google ADK Python issue/PR-maintenance calls
through project-local helpers. These imported helper summaries retain the helper definition and HTTP
sink lines on their call-site capability evidence. Google ADK uses package-qualified absolute imports
inside two sample roots; each resolves only because the importer ancestor chain contains one exact
module candidate. Four sibling fixed-origin calls remain inventory-only.
Composio's CLI contributes a separate TypeScript path: a schema-marked tool argument is recursively
hydrated as a URL-backed file and reaches raw global `fetch`, rather than the guarded core transport.
Four additional Qwen paths propagate that proof through registered classes: three call
`SimpleDocParser` directly or through an immutable constructor field, while `Retrieval` reaches the
newly summarized `DocParser` on the second graph iteration. The class pass requires a unique
single-entrypoint tool and an exact imported constructor; fixed arguments remain inventory, and
mutation, `setattr`, shadowing, module-qualified calls, and rebound constructors are pinned negatives.
Schema v38 also inventories 22 exact `urllib.request.urlopen` calls. Two are reachable from Qwen's
registered weather tools. Both wrap a fixed `https://ali-weather.showapi.com` URL with dynamic query
data in `Request` objects, so preserving the constructor's original URL produces exact inventory
edges without adding reviews. Module or named aliases are import-proven; local shadowing and rebound
openers are withheld.
Schema v38 separately models fail-closed Python scheme and hostname checks as
`network-origin-allowlist` controls on the exact request. The proof requires an import-proven
`urlparse`/`urlsplit`, immutable URL and parse-result bindings, static nonempty allowlists, and checks
that terminate before the sink. It records explicit redirect disabling while leaving DNS scope and
all other redirect behavior unresolved. None of the Python corpus review paths carries this exact
same-function control. That zero is a bounded governance observation—not proof that no repository has
an external validator or runtime egress policy. The 2-positive/7-negative IR fixture category pins
late checks, scheme-only checks, continuing guards, rebound parse results, shadowed parsers, and
mutable hostname collections, and requests inside the rejecting branch as non-controls.
The same schema resolves MCP Servers' `validateDataURI` as a distinct TypeScript
`network-origin-policy` on the gzip fetch. It always restricts schemes to `data`, `http`, or `https`,
and its exact/subdomain predicate consumes a normalized `GZIP_ALLOWED_DOMAINS` environment list.
Because that list explicitly defaults to empty and the predicate runs only when it is nonempty, the
edge records `configured-optional` and `hostname_default: open`. DNS and redirect scope remain
unresolved, and the AV-NET001 review remains. Two positive and five negative IR labels cover the real
edge, a local equivalent, late and rebound validation, nested validator calls, scheme-only checks,
and branch-only validation.
Schema v38 additionally proves CrewAI's `safe_get` transport at two production loader calls. Unlike
an initial hostname check, the helper validates every redirect, disables environment proxies, rejects
private/reserved resolution results, and verifies the connected peer before returning the socket.
Both edges are enabled by default but preserve `CREWAI_TOOLS_ALLOW_UNSAFE_PATHS` as a configured
opt-out and `CREWAI_TOOLS_FORCE_SAFE_PATHS` as an override. Ten test-scope calls remain inventoried
outside the production metric. Four positive and two negative IR labels pin the real/local edges,
alias propagation, missing redirect validation, and import rebinding.
Composio contributes two structurally different production edges from its session-file router. Its
validator rejects non-HTTP(S) targets and any non-public resolution; direct requests pin the
validated addresses and assert the connected peer. `safe_get` disables redirects, while
`safe_request` manually validates each bounded redirect hop. Environment and caller proxies are a
documented residual because the proxy performs DNS remotely, so the analyzer records
`connection-pinned-unless-proxied` and `environment-or-caller-dependent` instead of full pinning.
Four positive and one negative IR labels cover the local and pinned production calls, including the
ordinary-request near miss; a regression mutation also proves that removing the peer assertion
withholds both control edges.
Langflow adds ten production connector edges through four exact imported helper forms. The analyzer
requires the pinned settings defaults, both global and connector gates, literal-loopback exemption,
configured allowlist-aware validator, async and sync DNS-pinning backends, protected transports, and
ordinary-client fallbacks to compose before applying the summaries. Five synchronous GET calls
disable redirects by default and validate every bounded hop when explicitly enabled; the other five
GET/POST calls reject automatic redirects. When both protection gates are active and validation
returns addresses, connections use those pinned addresses and reject proxies. This is intentionally
not reported as unconditional protection: either gate can be disabled, configured allowlists and the
default literal-loopback exemption return no pinned addresses, and the ordinary clients then apply.
Four positive and one negative IR labels cover local sync/async applications, two pinned production
calls, and an ordinary `httpx.get` near miss; mutations of the enabled default or pinned backend
withhold the control edges.
n8n contributes a TypeScript composition case rather than another always-on helper. Its AI Builder
`web_fetch` tool accepts a model-controlled URL and calls an Axios helper. The CLI injects the real
`SsrfProtectionService` only when `N8N_SSRF_PROTECTION_ENABLED` is true; the setting defaults false,
and the other branch injects a passthrough whose validators succeed and whose lookup is ordinary DNS.
When enabled, the service checks configured hostname/IP policy during preflight and returns a custom
lookup used by Axios at resolution time. Redirects are capped at five; direct-IP targets are checked
inside `beforeRedirect`, cross-host auto-follow is stopped, and the redirected URL is revalidated
before a second fetch. The analyzer retains two residuals: selected source does not prove Axios proxy
behavior, and domain HITL is independent of address enforcement. A default-on mutation changes the
recorded state, while mutations of the composition branch, lookup, or redirect hook withhold the
edge; the pinned edge and raw Axios near miss prevent default-off policy from becoming unconditional
safety.
Flowise adds two exact composition cases. Its Agentflow HTTP node marks URL as a variable input,
derives `finalUrl`, assigns that value to a fixed Axios config, and invokes the imported
`secureAxiosRequest`. The pinned helper defaults its deny list on, normalizes IPv4-mapped IPv6,
validates every DNS result and redirect hop, and pins the chosen address through an agent lookup.
The exact caller exposes no transport override field, but an environment proxy can still resolve the
destination outside that lookup. AgentVerify therefore records connection pinning only when not
proxied, an environment-dependent proxy residual, and the `HTTP_SECURITY_CHECK=false` opt-out. A
same-named helper and six incomplete-composition mutations remain negative. Its Web Scraper tool
propagates `_call(initialInput)` through `scrapeRecursive` and `scrapeSingleUrl` into `secureFetch`;
the import is proven through Flowise's selected `src/index.ts` star-export barrel.
That helper replaces the caller's redirect mode with a bounded manual loop and supplies a pinned
agent after spreading caller options on every validated hop. The second edge therefore records
connection pinning, `pinned-agent` proxy scope, and `caller-agent-overridden` transport scope. A
same-named helper plus default-off, automatic-redirect, unpinned-agent, and broken parameter-chain
mutations remain negative.
Google ADK JS adds an imported-constructor global-fetch case. `LOAD_WEB_PAGE` maps its model URL
directly into `loadWebPage`, which restricts schemes, rejects localhost and explicit non-global
IPv4/IPv6 ranges, checks every preflight DNS answer, normalizes mapped IPv6, and disables redirects.
Because global `fetch` performs a second unpinned lookup, AgentVerify preserves the DNS-rebinding and
unresolved-proxy residuals rather than calling the path connection-pinned. Two positive and one
negative IR labels plus six incomplete-composition mutations pin that distinction.
Activepieces adds an imported Axios-client control for its configured MCP server transport. The
selected entrypoint passes `tool.serverUrl` into `createMcpClient`, whose exact `safeHttp` import calls
`safeHttp.axios.request`. The helper constructs both HTTP and HTTPS agents after spreading caller
configuration, and the nearest manifest pins `request-filtering-agent` 3.2.0. Direct IPs and every
connection-time DNS result are filtered unless matched by `AP_SSRF_ALLOW_LIST`; an environment proxy
can still shift the filtered connection from the destination to the proxy. AgentVerify therefore
records an always-on configured-exception policy with
`connection-time-filtered-unless-proxied`/`environment-dependent` residuals. Two positive and one
negative IR labels, plus import, manifest, ordering, and caller-override mutations, prevent a
same-named imported client from inheriting the control.
Composio's TypeScript SDK adds four conditional-runtime edges. Its Node/default `ssrfSafeFetch`
validates every resolution result and bounded redirect, then hands the validated addresses to an
Undici dispatcher lookup. A caller dispatcher, non-stock global dispatcher, or
`NODE_USE_ENV_PROXY` route deliberately disables pinning because the proxy resolves the destination;
the analyzer keeps that preflight-only residual. Package import conditions select a fail-closed edge
implementation for caller-selected upload URLs. Three API-response transfers use the distinct
`ssrfSafeFetchWhereSupported` export, whose edge implementation is intentionally raw fetch. Four
positive and one negative IR labels, plus runtime-map, redirect, dispatcher, import, and fail-closed
mutations, pin these distinctions.
The same repository exposes an unsafe contrast in its CLI service. `ToolsExecutor.execute` passes
schema-resolved `params.arguments` into `uploadToolInputFiles`; recursive `file_uploadable` hydration
routes HTTP(S) string values through `readFileFromUrl`, whose sink is raw `fetch(url)`. No core
`ssrfSafeFetch` import governs that path. AgentVerify emits one AV-NET001 review and
records a symbolized `Composio ToolsExecutor.execute → network` edge. Local and pinned positive
labels plus guarded-fetch, fixed-argument, schema-gate, and import mutations prevent generic CLI
fetches from inheriting this reachability.
Google ADK JS provides the fixed-origin contrast through its generated OpenAPI tools. The exact
toolset/parser/factory path produces `RestApiTool.runAsync`, whose model arguments affect encoded
path segments, query, headers, and body while the first OpenAPI server determines the origin.
Declared defaults/enums resolve server variables, dot segments are rejected, and credentials only
append query data or headers. AgentVerify inventories the raw `globalThis.fetch` tool capability but
adds a `network-origin-policy` edge and no AV-NET001 review. Two negative rule labels and three IR
labels pin the local and real behavior.
The first four accept arbitrary HTTP destinations; Goose checks the scheme but does not constrain the
host. MCP Servers has an optional environment-configured hostname allowlist, but its empty default
permits arbitrary HTTP/HTTPS origins; size and timeout limits constrain impact rather than
destination. A
[fixed Devpost origin with a dynamic search query](https://github.com/microsoft/ai-agents-for-beginners/blob/01777b05e8afeba6bf5a6dbe74cc2293372d3693/11-agentic-protocols/code_samples/github-mcp/app.py#L118)
and the SDK's [fixed weather host with a dynamic query](https://github.com/modelcontextprotocol/typescript-sdk/blob/3924de99df834302d89f5997a1b64ca268282284/examples/guides/get-started/firstServer.examples.ts#L20-L40)
are real negatives. Qwen's fixed AMap host and two urllib weather Request objects are additional
negatives: fixed-origin state survives an immutable
instance field and `.format(...)`, so a dynamic query does not become a dynamic destination. This
small but high-impact set supports a narrow review rule, not a claim that
every variable URL is SSRF.

## 9. A2A cards create a second network-origin authority

An A2A client can begin from a deployment-configured card URL yet later send RPC traffic to an
origin advertised inside the remotely returned card. That is not model-controlled URL flow, but it
is a distinct provenance boundary. In the pinned Google ADK JS path,
`resolveAgentCard()` returns the SDK-resolved card and `RemoteA2AAgent` passes it directly to
`ClientFactory.createFromAgentCard`. Gemini CLI follows the same authority transition after an
unauthenticated-first card fetch; its SDK transports use an Undici agent or configured proxy, while
the card-selected gRPC URL chooses secure versus insecure channel credentials. Neither exact
TypeScript path proves that every advertised endpoint is HTTPS or bound to the configured card
origin, so schema v65 emits two `AV-A2A001` reviews.

The pinned ADK Python client demonstrates the corresponding control. Both its per-invocation and
cached construction paths call `_validate_agent_card` first. The validator enumerates every RPC URL,
requires HTTPS except for explicit loopback development, and compares normalized scheme, host, and
port with the network card source origin. AgentVerify records two governed `a2a-rpc` edges and no
finding. Four real and five local/guarded rule labels, plus eight positive and one negative IR labels,
pin the distinction between remote-card authority, locally trusted cards, and source-origin binding.

## Limitations

- The collector is presence-based and scans a bounded subset of files.
- Generic words such as approval, trace, and sandbox can produce contextual false positives.
- Framework repositories contain tests and examples that are not enabled by default.
- Data flow and configuration resolution are required before absence or reachability claims.
- Every promoted detection needs a hand-reviewed real case and regression fixture.

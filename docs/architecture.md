# Architecture

```text
Repository
  ├─ Python AST frontend
  ├─ TypeScript/JavaScript frontend
  └─ MCP configuration frontend
           │
           ▼
Agent IR: components + source evidence + relationships
           │
           ▼
Context analysis: reachability + governing controls + unresolved state
           │
           ▼
Rule engine: inventory, review candidates, and findings
           │
           ▼
Deterministic text / JSON / native AI BOM / SARIF reports
```

## Agent IR

Components represent frameworks, providers, agents, tools, MCP servers, capabilities, controls, and
control settings. Relationships currently represent `uses`, `delegates-to`, `contains-control`, and
`governed-by` edges. Every object carries source path, line, and excerpt evidence.

Framework and provider taxonomy is evidence-backed rather than inferred from repository names.
Python module boundaries and TypeScript package/subpath boundaries identify the supported framework
families. Frontend-specific boundaries keep Python-only framework roots separate from the
TypeScript-only `ai` package used by Vercel AI SDK. Google provider evidence requires an exact GenAI,
Vertex, or AI SDK import, or a configured Gemini model prefix. AWS Bedrock requires the exact runtime
SDK, a recognized `langchain_aws` constructor import, or a literal `bedrock-runtime` service
selection. Mistral, Groq, Cohere, and Ollama require their exact Python SDK module. Schema v73 also
resolves their native client calls and exact LangChain provider wrappers through import aliases until
rebinding; a literal `model`/`model_name`/`model_id` on those calls inherits the proven provider.
Recognized Mistral-owned model prefixes provide a separate literal configuration proof, while Groq
and Ollama model names remain unresolved without the constructor because they commonly host
third-party models. Generic Google Cloud/AWS SDKs, near-name packages, and Gemma model names do not
establish provider identity. Taxonomy components intentionally have no source-symbol ID; exact
positive and negative component labels are scored separately from relationship and finding labels.
Schema v74 extends call attribution to official `@ai-sdk/mistral`, `@ai-sdk/groq`, and
`@ai-sdk/cohere` TypeScript exports. It resolves named aliases and destructured dynamic imports,
provider factory calls, model calls through an immutable factory-created instance, and direct
language/embedding/reranking calls. Reassignment, local shadowing, and near-name packages withhold
attribution.
Schema v75 recognizes exact AgentScope and PydanticAI provider wrapper APIs. AgentScope's public
`agentscope.model.OllamaChatModel` reexport and PydanticAI's provider, model, and embedding modules
retain identity through direct imports, module aliases, and function-local imports until rebinding.
Literal keyword model values and model-wrapper-only positional strings inherit the proven provider;
provider constructor positional arguments are never treated as model IDs.
Schema v76 makes provider identity symbol-specific within a public wrapper module. The same
`agentscope.model` reexport can therefore prove OpenAI Chat/Responses, Anthropic, Google Gemini, or
Ollama without assigning one provider to every symbol in the module. Module aliases and named
imports share the same exact export map, while reassignment still invalidates the binding.
Schema v100 adds the exact AgentScope DashScope, DeepSeek, Moonshot, and xAI chat-model exports to
that symbol map. Literal model arguments inherit the corresponding provider only while the module
alias or named import remains unrebound; adjacent or arbitrary model-class names remain unresolved.
Schema v101 extends exact-module attribution to PydanticAI's dedicated Anthropic, Google/Google
Cloud, AWS Bedrock, xAI, and DeepSeek provider surfaces. Dedicated model and embedding constructors
may contribute a positional literal model ID; provider constructors may not. The generic
OpenAI-compatible model/provider modules remain unresolved without endpoint/provider provenance.
Selected local package reexport chains of exact AgentScope and PydanticAI provider-wrapper symbols
now preserve attribution when every hop imports a known symbol/proven alias and does not rebind the
exported alias. Star imports from proven local reexport modules are supported when the exported name
is visible through literal `__all__` or the normal non-underscore wildcard rule. Simple imported
local wrapper factories are supported when they have one return path to a proven provider-wrapper
constructor and the model comes from a literal or factory parameter; factory summaries also survive
direct local reexport chains and star imports when visible through literal `__all__` or the normal
non-underscore wildcard rule. Rebound aliases, ambiguous factory returns, shadowed constructors, and
generic same-named classes remain unresolved.
Schema v102 adds Agno's exact public and direct OpenAI, Google, Anthropic, Azure OpenAI, and Groq
model modules. Literal model identity may come from Agno's `id=` field or first positional argument;
the proof is invalidated by import rebinding or a custom OpenAI/Groq `base_url` and is not generalized
to similarly named classes.
Schema v103 expands exact official TypeScript AI SDK call attribution to OpenAI, Anthropic, Google,
and xAI. Direct singleton and dynamic-import calls, image calls, immutable factory-created instances,
and observed inline embedding methods retain provider and literal model identity. Factory proof
requires no config or a literal, spread-free object without `baseURL`; a custom endpoint, unknown or
spread config, rebinding, near-name module, or generic compatible provider invalidates attribution.
Schema v104 applies the same default-endpoint boundary to native TypeScript provider constructors.
Exact ESM default or named imports from `openai`, `@anthropic-ai/sdk`, and `@google/genai` establish
constructor identity until rebinding. Calls with no arguments or a literal, spread-free config
without `baseURL`/`baseUrl` are accepted; CommonJS imports, unknown configs, nested custom endpoints,
and similarly named constructors remain unresolved.
Schema v105 adds a separate CommonJS proof for the exact OpenAI and Anthropic default-export shape:
one direct module-level `const Client = require(exact-package)` declaration and no other declaration, assignment,
parameter shadow, or custom/unknown endpoint configuration. Exact top-level direct or aliased named
destructures such as `const { GoogleGenAI } = require('@google/genai')` and
`const { GoogleGenAI: GeminiAliasClient } = require('@google/genai')` are also accepted for Google
GenAI. Property-selected, mutable, scoped, and other CommonJS forms are not generalized from this evidence.
Schema v106 retains an immutable constructor result and recognizes only provider-owned downstream
model methods: OpenAI chat completions/responses, Anthropic messages, and Google GenAI content
generation. A direct literal `model` property creates provider-call and model components at the
request location. Mutation, nonliteral request objects, generic `.create` matching, and parameter
flow invalidate or withhold this propagation without removing the original constructor inventory.
Schema v107 parses actual TypeScript parameter bindings so a constructor used only as a type is not
mistaken for a shadow. For exact imported client annotations on unique non-exported free functions,
a fixed-point dataflow resolves a parameter only if every direct same-file call argument is the same
provider: an inline default-endpoint constructor, an immutable constructor binding, or an already
resolved typed parameter. Function-name references must all be definitions or direct analyzed calls,
so callback/value escape withholds proof. Cycles need a concrete root; exports, mixed call sites,
mutation, and real parameter-name shadowing also withhold the downstream proof.
Schema v108 treats provider-request and model-value attribution as separate facts. Once an exact
native client receiver is proven, only the provider-owned OpenAI chat/responses, Anthropic messages,
or Google content-generation method is needed for a provider-call component; a nonliteral request
does not invent a model component. The same receiver proof may cross a class field only when its
declaration is readonly, the default-endpoint constructor is assigned exactly once inside the same
balanced class, and the request method is also inside that class. Mutable or multiply assigned
fields, custom endpoints, and generic `.create` methods stay unresolved.
Schema v109 admits a same-class lazy accessor only when a private getter is a single direct
`return this.<backing> ??= new ExactClient(defaultConfig)` expression. The backing field must be
private, declared once with null/undefined or no initializer, and have no other writes; the getter
must have no setter. Provider-owned requests on `this.<getter>` then inherit the constructor proof.
Public or uncached getters, resets, custom endpoints, nested-class leakage, and unrelated methods do
not establish the receiver.
Schema v110 keeps receiver and model provenance independent. A model component may follow a direct
request-object identifier only when that identifier has one earlier module-level `const` binding to
a simple quoted string, exactly one assignment, and no parameter, import, catch, or destructuring
shadow anywhere in the file. The model records `immutable-module-literal-binding` separately from
the request receiver's resolution basis. A module-level template string is accepted only when every
`${...}` expression is an earlier immutable literal binding. Later declarations, mutable/rebound
bindings, runtime parameters, unknown template expressions, and helper-built request objects remain
unresolved.
Schema v111 applies that same immutable module-literal proof to the first model argument of an exact
official TypeScript AI SDK provider call. Direct singleton calls, configured instances, and chained
factory model methods may inherit the earlier string constant only after provider and endpoint
provenance are exact. The same bounded template-string proof applies; runtime parameters,
mutable/rebound names, forward declarations, unknown template expressions, and shadowed constants
remain unresolved.
The same model-binding table also accepts exact module-level literal object maps: a top-level
`const MODEL_IDS = { chat: "..." }` may prove `model: MODEL_IDS.chat` or `openai(MODEL_IDS.chat)`
when the object has one declaration, direct literal string properties, exact dot-member reads, and no
object/member reassignment. Mutable object properties, nonliteral object values, bracket reads, and
unknown template values remain unresolved.
Schema v77 gives import-proven, assigned Python MCP stdio constructors stable component identities.
An Agent receives an exact `uses` edge only when its literal `mcp_servers=[...]` list names an
earlier, unreassigned server binding in the same statement block. Package and version facts remain
conditional on literal `npx` or `uvx` package selection; a literal non-package command such as
`deno` is still valid MCP inventory without invented supply-chain metadata.
Schema v78 adds in-process server identity only for the exact `fastmcp` or `mcp.server` FastMCP
exports. It also permits one immutable module-level MCP server assignment to feed a later literal
Agent list inside a function or module control block. The assignment must be the module binding's
only mutation, precede the Agent expression, and remain unshadowed through every enclosing lexical
scope. Conditional definitions, rebinding, forward lexical order, and near-name FastMCP packages
remain unresolved.
Schema v79 admits a constructor import nested in one top-level `try` only when every exception
handler terminates, so continuation proves the imported binding exists. For an immutable exact
FastMCP assignment, `@server.tool()` and equivalent exact post-registration calls create
server→tool edges with both symbol endpoints. Capability context can then follow
Agent→server→tool→capability. Optional/fall-through imports, rebound registrars, ambiguous tool
targets, and name-only server matches remain disconnected.
Schema v80 gives an exact imported MCP constructor bound by `with` or `async with` an
occurrence-qualified server identity. A direct Agent statement inside that context can resolve the
binding only before any reassignment; duplicate `as` names, post-context, and nested/indirect uses
remain disconnected.
OpenAI's `MCPServerStdio(params={...})` shape retains identity even when its executable or arguments
are dynamic, while package provenance still requires a literal `npx` or `uvx` selection. The
OpenAI `SandboxAgent` constructor is recognized only through an exact `agents.sandbox` import.
Schema v81 extends that identity proof to a project-local adapter class only when it directly
subclasses an exact imported `MCPServer`, has one immutable module export, and directly defines both
`list_tools` and `call_tool`. A unique local import and an earlier same-scope instance can then feed
the existing literal Agent binding. Near bases, incomplete adapters, rebound imports/instances, and
forward uses remain disconnected.
Schema v82 resolves a direct local function factory only when the helper is defined once in the same
statement block before the call, is undecorated, and has one direct top-level return of an
import-proven Agent constructor, including exact module-qualified framework constructors. Each
direct assigned result may then point to that observed Agent definition. Conditional or indirect
returns, forward/rebound helpers, constructor shadowing, and result rebinding remain unresolved.

Schema v83 treats `LocalShellTool` as an OpenAI built-in only when its local name comes from one
immutable, earlier, top-level `from agents import LocalShellTool` or
`from agents.tool import LocalShellTool` binding. Aliases are canonicalized, while near-package,
conditional, duplicate, or rebound bindings are withheld. The asset records local shell execution
and `approval_policy: unavailable` / `approval_source: sdk-no-approval-parameter`; it does not infer
that the caller-supplied executor lacks an equivalent control.

Schema v84 extends that exact-import map to `CodeInterpreterTool`. The IR records a hosted-sandbox
code-execution capability, an unavailable SDK approval hook, and either `auto`,
`existing-reference`, or `unresolved` container policy. Only literal `tool_config` dictionaries
establish container policy; symbolic and casted expressions remain unresolved. Because this is
source-proven sandboxed inventory without a direct dynamic evaluator primitive, it does not satisfy
AV-EXEC002's finding contract.

Schema v85 adds `WebSearchTool`, `FileSearchTool`, and `ImageGenerationTool` to the same exact-import
map. Their execution environment and hosting policy are provider-hosted, their absent constructor
approval hook is explicit, and aliases retain canonical API identity. Web search preserves literal
or SDK-default external-access state, file search preserves literal or unresolved vector-store
scope, and image generation records a provider-hosted media boundary. These facts do not imply a
caller-selected network origin, local data access, or provider retention guarantee. Same-named
constructors from other frameworks, near packages, duplicate imports, and rebound names are withheld.

Schema v114 recognizes `dify_agent` as a Python framework boundary and resolves its conditional
shell run-layer composition without treating a request builder as a direct subprocess sink. The
input model must default both `include_shell` and the config layer to disabled, the immutable guard
must immediately dominate exact `RunLayerSpec` calls for `DifyRuntimeLayerConfig` and
`DifyShellLayerConfig`, and the shell dependency helper must return the one immutable runtime ID.
The same immutable layer list must reach the returned `RunComposition`.
The IR emits `dify.shell → shell-execution → sandbox-runtime`; the control records that execution is
routed through a deployment-selected runtime binding while leaving the external runtime's actual
containment `external-unresolved`. Missing runtime layers, enabled defaults, reordered/reassigned
guards, near packages, and rebound imported constructors withhold the composition.

Schema v115 recognizes AutoGen's current official Python package family—`autogen_agentchat`,
`autogen_core`, and `autogen_ext`—alongside the legacy `autogen` namespace. Exact imports from
`autogen_ext.models.openai` resolve `OpenAIChatCompletionClient` and
`AzureOpenAIChatCompletionClient`; `autogen_ext.models.anthropic` resolves
`AnthropicChatCompletionClient`. Literal `model=` values inherit that exact wrapper identity.
OpenAI-compatible calls with a `base_url`, near packages, and rebound imported constructors remain
unattributed; constructor names alone no longer establish the AutoGen OpenAI wrapper.

Schema v116 adds the Python-only `openhands` framework boundary and an exact module-level
OpenHands SDK composition. `Tool(name=TerminalTool.name)` and
`Tool(name=FileEditorTool.name)` must use immutable official imports, flow through one static tools
list into `Agent`, and then reach the same `Conversation`. A unique
`set_security_analyzer(...)` call creates action-risk-analysis edges. Confirmation is credited only
when that conversation also receives an exact `ConfirmRisky(...)`; literal `SecurityRisk`
thresholds and `confirm_unknown` booleans are retained, while nonliteral or multiple setters are
unresolved. Analyzer-only chains record the source-validated `NeverConfirm` SDK default instead of
mistaking risk classification for an execution gate. The file editor records writable,
agent-selected absolute paths and does not treat `workspace_root` as containment because the pinned
implementation uses it as the editor working directory rather than rejecting paths outside it.

Names are intentionally not treated as globally unique. Python and TypeScript agent/tool definitions
carry stable frontend-and-module-qualified `symbol_id` values; relationships carry `source_id` and
`target_id` when resolution succeeds. Context analysis prefers those IDs and falls back to the older
location-gated display-name logic only for unresolved syntax. Capability-to-tool resolution still
requires the relationship and capability observation to share a source location, preventing
same-named definitions in separate modules from leaking reachability or control coverage.
Unambiguous absolute Python
`from local_module import tool` references and filesystem-resolved relative imports point to an exact
repository file and can safely form cross-file agent paths. Script-root-style absolute imports in a
monorepository can also resolve by walking only the importer's ancestor directories and requiring
one filesystem candidate. An Agent-to-tool ID additionally requires that candidate to export the
exact decorated function or class-qualified method; aliases preserve the original export name. The
edge records `target_identity: contextual-absolute-import-single-export`. The same single-path proof
can apply an exact imported network-helper summary. Multiple ancestor candidates, missing members,
undecorated members, and local rebinding remain unresolved. Function parameters and local
assignments/imports are scope-isolated: a same-named local binding cannot inherit a module import's
target ID, and an explicit function-local import is restored only within that function. TypeScript
named imports resolve when a
relative module maps to exactly one in-repository `.ts`, `.tsx`, `.js`, or `.jsx` file; aliases retain
the original exported name. Imports that escape the scan root, target missing files, or have multiple
candidate files remain unresolved. Python class methods use class-qualified IDs, and assigned agent
or built-in-tool instances use their binding name. The TypeScript frontend balances delimiters and
reads only direct properties and top-level tool-array entries; it models OpenAI tool namespaces,
built-ins, inline/assigned agent adapters, and Cline inline tools without treating nested tokens as
symbols. Python constructor and callable bindings gain a target ID inside a `with`, branch, or other
statement body only when one exact assignment or function definition is the sole same-block mutation
before use. Literal Agent `tools=[...]` entries establish tool role, while identity requires an exact
local proof. A callable or constructor assignment may be the sole earlier same-block definition, or
an immutable module-level definition visible without local shadowing. Constructor results additionally
require one immutable import from a module whose path establishes a tool namespace; a local class is
eligible only with an exact imported tool base. Inline constructors receive occurrence-qualified tool
IDs. A direct `with`/`async with` binding is accepted only when the Agent statement is directly in
that body and no preceding mutation intervenes. AgentVerify does not infer capabilities from the
constructor spelling. Exact framework Agent constructors may carry provenance through top-level
absolute module imports only when the imported root is unique/unrebound and the constructor attribute
is not reassigned; the resulting Agent records the origin module, imported symbol, and
`exact-framework-agent-module-import` resolution. A narrower external wildcard path is supported
only for the same exact framework constructor modules when a single star import could provide the
constructor name and the consumer does not shadow it; ambiguous stars, near packages, and local
rebinding stay unresolved. An exact imported class may also create a tool through the known
`from_settings` factory method, provided the class import is immutable and already establishes tool
role. `agents.HostedMCPTool` and `google.adk.integrations.langchain.LangchainTool` are explicit
integration adapters; the hosted MCP adapter records MCP access but does not invent approval state.
For OpenAI built-in approval handlers, unique same-file Python/TypeScript functions can also be
summarized transitively when an approval-specific environment comparison has an immediate true
return. A resolved handler adds a tool-to-auto-approval configuration edge; ambiguous definitions,
unused helpers, safe returns, and cross-file callback chains stay unresolved.
An assigned `agent.as_tool()` adapter requires one sole same-block adapter mutation and one earlier,
unreassigned direct Agent-constructor receiver. It receives its own tool identity and an exact
tool-to-Agent delegation edge; parameters, forward receivers, arbitrary objects, and receiver or
adapter reassignment remain unresolved. A wrapper assignment can additionally preserve a callable body when
the factory is an unshadowed `function_tool` import from `agents` or `agents.tool`, the wrapper and
function are each sole earlier same-block mutations, and the function is passed as the wrapper's sole
positional argument. Literal approval on the wrapper is retained. This block-local proof takes
precedence over a broader lexical candidate, while any local binding prevents fallback to a
same-named module definition. Cross-branch definitions, reassignments, forward definitions,
unproven parameters, arbitrary factories/builtins or factory methods, ambiguous or rebound constructor imports, nested
or reassigned context bindings, tool-helper returns, lambdas, multiply wrapped functions, wrapper
tuple unpacking, and shadowed factories remain unresolved.
Dynamic lookups, conditional tool expressions, unresolved package exports, and other
wrapper-factory forms remain unresolved.

An immutable top-level `from module import name` binding used directly in a literal Agent tool list
also receives an exact import identity. If the selected repository contains one resolved module path
and one unique undecorated top-level function export, the relationship targets that definition and
its body is analyzed under the imported tool role. Contextual script-root imports require the same
single-path proof. When an absolute SDK module is not present in the bounded checkout, the import
statement itself becomes a tool-boundary component and no implementation capability is inferred.
Missing relative modules, duplicate or forward imports, module rebinding, and function/class-local
shadowing remain unresolved.

Same-class Agent factory summaries are deliberately narrower than general interprocedural dataflow.
A uniquely named method must have one direct top-level return. That return may be an Agent
constructor, one immutable local assigned from an Agent constructor, or a tuple/list containing that
local. A caller on `self`, `cls`, or the exact class must bind every returned element directly, and
the selected Agent binding must be the sole mutation before composition. The edge records
`target_identity: same-class-helper-return`. Conditional or multiple returns, transformed or
reassigned values, rebound helper/receiver names, external receivers, and cross-branch unpacking
remain unresolved.

Imported-class Agent factory summaries use a separate cross-file proof. The class import must resolve
to one repository file and one exact module-level class export. That class must be undecorated and
non-inherited, and the selected unique instance method must directly return one Agent whose
constructor import is itself framework-proven. The caller must construct one local receiver through
its sole same-block mutation, bind the method result directly, and preserve that result as the sole
mutation before composition. The edge records the imported Agent symbol, `target_path`, and
`target_identity: contextual-imported-class-factory-return` for script-root contextual imports.
Ambiguous ancestor paths, missing or rebound exports, reimports, async/indirect/conditional returns,
dynamic attribute lookup, instance method shadowing, and constructor, receiver, or result rebinding
remain unresolved.

Typed OpenAI built-in tool parameters use a separate call-site consensus proof. The helper must be a
unique, undecorated top-level function; the annotation must resolve through an unshadowed `agents` or
`agents.tool` import; the parameter cannot be reassigned; and every direct same-module positional or
keyword call must pass either the matching constructor inline or a sole same-block binding of that
constructor. AgentVerify creates an occurrence-qualified parameter tool component and records the
set of verified concrete constructor IDs on it. It does not inherit any one instance's approval or
execution policy. Missing, mismatched, starred, rebound, shadowed, union-typed, or reassigned flows
remain unresolved. The Agent edge records
`target_identity: typed-parameter-callsite-consensus`.

A repository prepass also resolves direct module-level Python
`server.tool(...)(function)` decorator applications. The registrar must be a uniquely bound
FastMCP instance, and the target must be one uniquely bound same-module definition or one exact
relative import leading to a unique module-level definition. The resulting tool keeps definition
evidence and a module-qualified ID while recording registration path, line, registrar, resolution
basis, and literal approval metadata. Exact IDs allow registration-site controls to govern a
cross-file tool body. A bounded wrapper summary follows direct wrappers and decorator factories only
when their returned callback uses `functools.wraps` for exactly one callable parameter and directly
forwards its own `*args, **kwargs` to that parameter. Wrapper chains are capped at four layers and
record every wrapper name on the tool. Metadata-only or branch-only wrappers, nested registrations,
rebound bindings, wildcard imports, duplicate registrations, and unrelated `.tool` factories remain
unresolved.

Two import-proven registry decorators extend Python tool identity without treating every
`register_tool` spelling as a framework API. MetaGPT function decorators resolve the decorated body
directly; MetaGPT classes expose only direct methods named in a literal `include_functions` list.
Qwen-Agent class decorators require a literal registered tool name and resolve one direct `call`
method. Class capabilities are attached to the class tool identity rather than inventing duplicate
method tools. Exact source modules and statement-ordered alias rebinding are part of the proof;
nonliteral entrypoints, unrelated imports, and rebound decorators remain unresolved.

Within decorated Python tools and structurally resolved TypeScript execution callbacks, tool
parameters begin as potential dynamic HTTP origins. Direct assignment aliases preserve that state,
while reassignment to a literal or a URL expression whose literal prefix contains a complete HTTP
scheme and host clears it. Python also propagates a proven fixed origin through unique module string
assignments, immutable `self` fields initialized in `__init__`, concatenation, `.format(...)`, and
f-strings whose resolved prefix contains the complete origin. Schema v112 additionally resolves an
exact named import to one selected Python module when the exported value is a single immutable
top-level HTTP(S) string literal. The capability records `origin_resolution`, `origin_path`, and
`origin_line`; aliases and one local propagation step retain that proof. Environment/computed values,
duplicate or global-mutated source bindings, consumer rebinding or function-local shadowing,
wildcards, reexports, ambiguous imports, and module-qualified access remain unresolved. Dynamic
paths and queries on a proven origin remain inventory-only. The TypeScript frontend also resolves unique module string constants used
as a template prefix. For a uniquely named same-file free function or static method containing a
recognized network call, a bounded summary records which formal parameters can control the origin;
tool calls map positional and destructured-object arguments back to those parameters. `AV-NET001`
consumes only this origin-specific attribute; it does not equate a dynamic path or query on a fixed
host with a dynamic destination. A separate Python proof recognizes exact module-level
`urllib.parse.urlparse`/`urlsplit` imports, an immutable parse result derived from a tool parameter or
one direct alias, and fail-closed scheme plus hostname rejection before the request. Static nonempty
literal collections may be local or immutable module constants. The resulting
`network-origin-allowlist` control constrains only the initial origin: explicit redirect disabling is
recorded, while redirect behavior and DNS scope otherwise stay unresolved. These controls enrich the
review path but do not suppress `AV-NET001` or claim SSRF prevention. Positive branches, helper-based
validators, normalized hostname expressions, redirects, DNS, proxies, imported/transitive helpers,
arrow functions, and general client request-object data flow remain unresolved.

The TypeScript network reader also proves immutable same-file Axios instances created through an
exact default import or CommonJS binding. Direct verbs and `.request(...)` preserve URL origin flow;
literal `baseURL` and `allowAbsoluteUrls: false` state distinguish a locked configured origin from an
absolute-URL override. Rebinding, mutation, interceptors, computed options, and generic cross-file
clients are withheld.

The Python frontend also recognizes `urllib.request.urlopen` only through an exact module-level
`urllib`/`urllib.request` import, `from urllib import request`, or named `urlopen` import. Aliases are
canonicalized to the stdlib API, while module rebinding or any same-function binding with the same
root withholds the proof. A direct import-proven `Request(url)` passed inline or through
statement-ordered local assignment is unwrapped to its original URL before origin classification,
so a fixed scheme and host are not lost behind the request object. Custom openers, locally imported
bindings, assigned opener aliases, and Request factories remain unresolved.

The TypeScript frontend can attach one same-file validator policy through a direct validated-result
assignment and immutable aliases to a direct or summarized network call. The validator proof requires
`new URL(parameter)`, a fail-closed literal scheme set, and an exact/subdomain hostname predicate over
an immutable normalized environment list. An empty environment default is represented as
`hostname_scope: configured-optional` and `hostname_default: open`; it is validation evidence, not an
allowlist that satisfies destination policy. Late validation, rebound results, nested validator calls,
scheme-only helpers, DNS, and redirect behavior remain unresolved, and `AV-NET001` is not suppressed.

A separate Python prepass recognizes two source-proven imported secure-transport families. The
fully pinned family validates the initial URL and each redirect, disables automatic redirects and
all proxy sources, mounts protected adapters for both HTTP schemes, rejects private/reserved
resolution results, and checks the connected peer. The proxy-conditional family proves the same
public-address and peer checks for direct connections, but preserves environment or caller proxy
selection as `dns_scope: connection-pinned-unless-proxied` and
`proxy_scope: environment-or-caller-dependent`; redirect-disabled and bounded each-hop helpers stay
distinct. Both produce `network-ssrf-policy` with `enforcement_default: enabled`. Environment escape
and force-safe names are retained when present, and proxy residuals are never promoted to full
pinning. Exact named imports and aliases apply the summary, while rebinding or any missing transport
proof withholds it; helper names and docstrings alone do not contribute evidence.

A third structural family models configurable connector protection without flattening its disabled
state into unconditional safety. It requires versioned, selected evidence for default-on global and
connector settings; both gate functions; configured allowlist and literal-loopback handling; the
core public-address validator; async and sync backends that connect to validated addresses; protected
transports that reject proxies; and factory fallbacks to ordinary clients. Resulting edges use
`connection-pinned-when-enforced` and `disabled-when-enforced`, retain both opt-out environment names,
and record the configured allowlist/default loopback exemption in the initial-origin scope. Helpers
that reject redirects remain distinct from the bounded synchronous GET helper that disables them by
default and revalidates each hop only when explicitly enabled. Any missing composition proof,
disabled default, unpinned backend, non-exact import, or rebinding withholds the summary.

The TypeScript composition pass handles a different boundary: dependency injection can choose a real
SSRF service or a no-op guard before the value crosses multiple constructors into a tool factory. The
current proof requires a literal boolean config default, exact service/passthrough ternary, repeated immutable
guard propagation, tool-input validation, a bounded Axios redirect configuration, custom lookup, and
redirect hook to coexist in selected source. It adds the `web_fetch → network → network-ssrf-policy`
path at the tool call while retaining the helper sink and composition/config locations as attributes.
The custom lookup is recorded as configured rather than connection-pinned, and proxy scope stays
unresolved because selected source does not prove how Axios routes proxied destinations. Missing any
stage withholds both the tool capability and control edge.

A second TypeScript composition pass resolves Flowise's CommonJS-registered Agentflow HTTP node through a
request object into its imported secure transport. It requires the variable URL descriptor, exact
`nodeData.inputs.url` flow, one fixed `url: finalUrl` config without Axios transport overrides or
spreads, a default-on deny list with mapped-address normalization, manual bounded redirects, all-DNS
answer validation, and a pinned agent lookup. The resulting edge retains the configured opt-out and
`environment-dependent` proxy scope; proxy routing can move destination resolution away from the
pinned lookup. Default-off settings, automatic redirects, caller transport fields, or incomplete
address normalization withhold the proof.

The same pass independently resolves Flowise's `node-fetch` Web Scraper path. It requires the exact
`Tool` subclass identity, an import proven directly or through one star-export barrel,
`_call(initialInput) → scrapeRecursive(url) → scrapeSingleUrl(url)`
parameter chain, a default-on helper with the same address proof, a bounded manual redirect loop,
and a pinned agent supplied after the caller-options spread. That ordering proves caller agent
options cannot replace the pinned connection for this structural family. Its edge records
`connection-pinned`, `pinned-agent`, and `caller-agent-overridden`; changing a hop to a fixed URL,
restoring automatic redirects, or moving an untrusted agent after the pin withholds the proof.

A fourth TypeScript composition pass resolves Google ADK JS's `LOAD_WEB_PAGE` only when the selected
`FunctionTool` definition is reached by an exact import and its URL callback maps directly into
`loadWebPage`. The helper must reject disallowed schemes and localhost, validate every DNS answer
against explicit IPv4/IPv6 ranges with mapped-address handling, and disable redirects before global
fetch. Because that fetch performs a separate connection-time lookup, the control is recorded as
preflight-only with an unpinned-transport residual. Removing any stage withholds both reachability and
the control edge.

A fifth TypeScript composition pass resolves Activepieces only through an exact named `safeHttp`
import and the selected MCP transport/entry chain. It requires `request-filtering-agent` 3.2.0 in the
nearest package manifest, both HTTP and HTTPS filtering agents constructed after caller config, URL
shorthand at `safeHttp.axios.request`, and no caller proxy or agent override. The control records
connection-time address filtering and `AP_SSRF_ALLOW_LIST` IP/CIDR exceptions, but retains
environment-proxy dependence because a proxy can become the directly filtered connection target.

A sixth TypeScript pass resolves Composio's conditional `#ssrf_guard` import only when its package
map selects the Node guard by default and the edge-specific implementation for edge runtimes. The
Node helper must validate every DNS answer and manual redirect, then pass those addresses to an
Undici dispatcher's lookup. Caller dispatchers, a non-stock global dispatcher, and environment-proxy
mode are retained as preflight-only route residuals. The edge helper's two exports stay distinct:
`ssrfSafeFetch` fails closed, while `ssrfSafeFetchWhereSupported` deliberately uses unguarded fetch.

A separate Composio CLI pass models a real unsafe counterpart. It requires the exact
`ToolsExecutor.execute` import and `params.arguments` mapping, schema `file_uploadable` recursion,
URL-versus-local-file split, and final raw `fetch(url)`. The pass replaces that sink's generic
inventory component with a dynamic network capability and a symbolized tool edge, allowing
`AV-NET001` to report the proven tool-execution-argument origin without generalizing from filenames.

The Google ADK OpenAPI pass models the fixed-origin counterpart. It follows `OpenAPIToolset` through
`OpenApiSpecParser` and `createRestApiTool` into `RestApiTool.runAsync`, then proves that request
arguments can affect only encoded path segments, query, headers, and body. The origin remains the
first spec server after declared-default/enum variable expansion; `applyCredential` may append a
query credential but cannot replace the URL. The raw global-fetch capability is inventoried with a
`network-origin-policy` edge and `dynamic_origin: false`. Dynamic server variables, unencoded model
paths, URL-rewriting credentials, or broken factory imports withhold the proof.

The A2A endpoint-provenance passes model a different authority transition from tool-input SSRF.
They create an `a2a-rpc` capability at SDK client construction when a network-resolved AgentCard can
select the later RPC endpoint. The ADK JS proof requires an exact named import of its resolver and a
direct resolved-card flow into `createFromAgentCard`; the Gemini proof requires configured URL versus
inline JSON resolution, card normalization, SDK interface selection, and its Undici agent/proxy
dispatcher. Both preserve `dynamic_origin: false` and `origin_authority: remote-agent-card`, allowing
`AV-A2A001` to report the missing card-source binding without changing AV-NET001's model-parameter
contract. The ADK Python counterproof requires validation to dominate both cached and per-invocation
factory calls, enumeration of every advertised RPC URL, HTTPS-or-loopback rejection, and normalized
source-origin equality. Those paths receive `a2a-card-rpc-origin-policy`; missing any stage withholds
the control rather than inferring it from validator names.

An exact OpenAI Agents Python MCP pass follows a directly imported `MCPServerStdio` context binding
into `SandboxAgent(mcp_servers=[server])`. It verifies the SDK constructor default, `None → False`
normalization, missing-name fallback, and propagation into `_build_wrapped_function_tool`. The IR
records both the agent→server edge and a disabled-default `mcp-tool-approval` setting. Explicit
approval, changed defaults, hard-coded wrapper approval, wrong imports, or a different server binding
withhold the edge; the policy does not itself create an approval finding.

The TypeScript counterpart proves a narrower destructive path. It verifies the pinned OpenAI Agents
JS sources that attach configured MCP servers to an Agent, convert every discovered MCP tool through
`tool(...)` without a `needsApproval` override, and normalize an omitted override to `false`. Exact
`MCPServerStdio` and `Agent` imports then connect a literal local filesystem package to the Agent.
The IR records agent→MCP-server→filesystem reachability plus the disabled-default setting. A static
filter is treated as read-only only when its literal allowlist contains exclusively known read-only
filesystem tools; dynamic filters, writable entries, rebinding, and unbound servers do not satisfy
that counterproof.

The Agno Python pass proves a parallel confirmation policy without conflating the two SDKs. It
verifies the pinned `MCPTools` implementation that defaults `requires_confirmation_tools` to an empty
list and copies exact name membership into every discovered function's `requires_confirmation`
field. Exact `agno.agent.Agent` and `agno.tools.mcp.MCPTools` imports connect either a direct
filesystem command or an exactly nested `StdioServerParameters` → `stdio_client` → `ClientSession`
composition to the Agent. Static confirmation lists must cover all known mutating filesystem tools;
partial lists remain reviewable, complete lists add a human-approval control, and dynamic policies
remain unresolved. A literal `include_tools` list containing only known read-only tools adds an
`mcp-tool-filter` counterproof and suppresses the destructive capability claim.

The Semantic Kernel MCP sampling pass models authority in the opposite direction. It requires the
pinned SDK source to register `sampling_callback` on the client session, deny requests when both
consent and auto-approval are absent, give a configured callback precedence, translate the server's
system prompt/messages/model hint/temperature/token limit into chat-model inputs, and return the
completion to the server. Exact `MCP*Plugin` and `ChatCompletionAgent` imports plus a directly bound
async-context plugin establish the Agent→MCP-server→model-sampling path. Literal true becomes
`auto-approved-explicit`; omitted and literal-false settings add a fail-closed
`mcp-sampling-consent` control; callback and dynamic expressions remain unresolved. An exact
specialized path suppresses the broader lexical auto-approval review so one policy is not reported
twice.

The generic sampling-consent pass recognizes the protocol surface directly. Python requires an exact
`from mcp import ClientSession`, a same-scope named async callback, and an exact `mcp.types`
`CreateMessageResult` or `ErrorData` return. TypeScript requires an exact
`@modelcontextprotocol/client` `Client`, a literal sampling-capability declaration, a proven instance
or typed parameter receiver, and a
structurally balanced `sampling/createMessage` arrow handler returning the required result fields.
Successful handlers are automatic unless Python proves an interactive decision with a fail-closed
rejection branch or TypeScript proves an awaited confirmation whose negative branch throws. The
decision must precede provider invocation. The TypeScript analysis separately records full request disclosure and a `Math.min` token cap propagated
to the provider request. Named external callbacks and complex or indirect handlers remain explicit
`unresolved-handler` settings rather than assumed safe or unsafe.

The PydanticAI adapter path recognizes an exact, immutable module-scope import of
`pydantic_ai.mcp.MCPToolset` and a constructor with a non-null `sampling_model`. PydanticAI converts
that model into an SDK-generated sampling callback, so the IR records automatic fulfilment to a
model provider even though no callback appears at the call site. A simultaneous non-null
`sampling_handler`, expanded keyword arguments, a rebound constructor, and unrelated imports
or imports inside conditional runtime branches withhold the path. The capability records
`sdk-session-dependent` protocol compatibility because
session support still depends on the MCP SDK surface used at runtime.

The elicitation-consent pass models a separate server authority: a client advertises form and/or URL
elicitation and returns `accept`, `decline`, or `cancel`. Python requires an exact `mcp.ClientSession`,
a same-scope named async callback, and an exact `mcp.types.ElicitResult` action. TypeScript requires
an exact `@modelcontextprotocol/client` `Client`, a literal elicitation capability, an immutable receiver,
and a balanced inline `elicitation/create` arrow handler. Literal acceptance is automatic unless
every accepting branch follows direct awaited user input or confirmation. One exact local imported
helper is also recognized when its unique body collects input and can decline or cancel before
acceptance. Decline-only and unresolved handlers remain distinct settings. The IR records advertised
modes, server input authority, response destination, request disclosure, and an exact
`mcp-elicitation-consent` control edge.

The FastMCP adapter path recognizes an exact `fastmcp.Client`, a same-scope named async
`elicitation_handler`, and an optional exact `ElicitResult`. FastMCP treats ordinary returned data,
including the supplied `response_type(...)`, as protocol `accept`; explicit `ElicitResult` actions
retain accept, decline, and cancel semantics. A direct input call is not enough to prove consent:
acceptance is human-confirmed only when an earlier decision preserves decline/cancel outcomes.
Rebound callbacks or response factories and unknown return calls remain unresolved. Request
disclosure is derived only from values passed to recognized display/prompt calls, so the pinned CLI
is correctly modeled as human-confirmed with message-only disclosure rather than full request-detail
disclosure.

URL disclosure is modeled independently from acceptance. For exact Python callbacks, the full
request object or its `.url` field must reach a direct display/prompt argument; schema-only and
message-only rendering do not qualify. TypeScript requires `request.params.url` in a recognized UI
call. `AV-MCP007` applies only to human-confirmed URL-capable handlers missing that proof, avoiding a
duplicate disclosure result on handlers already reported for automatic acceptance.

A repository prepass builds bounded Python network summaries for unique top-level free functions in
selected files. A summary records direct recognized HTTP calls and the formal parameters that can
control their origins after fixed-prefix discrimination. At a tool call site, only an exact named
absolute or relative import can apply the summary; positional and keyword arguments map back to the
controlled formals, and the capability retains the helper path and sink lines. Import state is
function-local and statement-ordered, so reassignment, deletion, or replacement imports invalidate
the edge. Module-object calls, reexports, nested/transitive helpers, client instances, helper-local
aliases, and rebound HTTP clients remain unresolved rather than being inferred by name.

After all direct frontends run, a bounded graph pass promotes proven dynamic network behavior across
registered Python classes. A summary requires a unique class tool, exactly one literal entrypoint,
and an existing dynamic network edge. Callers resolve only an exact named imported constructor used
directly or assigned once to `self.<field>` in `__init__`; all class-local assignments, deletion,
`setattr`, constructor shadowing, and ambiguous definitions invalidate the field proof. The caller's
first positional or matching keyword argument is evaluated with statement-ordered assignment and
loop-variable taint. When the callee reads one unique literal object key, only that caller field is
treated as the origin; a dynamic sibling field cannot taint a fixed URL. Fixed arguments remain
inventory-only. Newly resolved class tools can become
summaries for the next pass, capped at four iterations. Each capability retains the callee class,
method, definition line, and prior network-edge lines.

The same Python tool-parameter state distinguishes browser-page code execution from ordinary code
inventory. In a module importing Playwright, Selenium, or Puppeteer, an attribute call to
`evaluate(...)`, `evaluate_handle(...)`, `eval_on_selector(...)`, `eval_on_selector_all(...)`, or
Locator `evaluate_all(...)` becomes a `code-execution` capability with
`execution_context: browser-page`. The script expression is positional argument zero except for the selector APIs, where
it is positional argument one; every supported API also accepts the exact `expression=` keyword.
`dynamic_input` is true only when that script expression contains
a current tool parameter or its direct assignment alias; literals, module constants, and values
derived solely from normalized intermediates remain inventory-only. A dynamic browser evaluator is
emitted only when its receiver is an exact imported Playwright `Page`/`Locator`/handle annotation,
one immutable alias of such a parameter, an exactly typed `self` attribute in the enclosing class,
an immutable constructor-bound Playwright page field or its direct local alias, an exact built-in
property with a Playwright return annotation, a straight-line locally constructed Playwright page,
one uniquely annotated module-level Playwright receiver, a parameter of a private same-class helper
whose selected-module call sites unanimously pass a locally proven Playwright browser, or the first
result of Skyvern's exact imported `get_page` factory. An exact Skyvern wrapper scope derived from
that result is also accepted when an unshadowed built-in `getattr` selects `_locator_scope` with a
`None` default or falls back through `.page` to the same receiver, and the annotated assignment
dominates the evaluator. A field on an imported context class may flow through one immutable local
alias when the selected defining file has one top-level class definition and one exact Playwright
field annotation, the consumer uniquely resolves an unrebound import of that class, and an immutable
parameter uses the exact imported class annotation. Module annotations require one binding and no
top-level rebound or duplicate annotation; function parameters and local bindings shadow them. Playwright imports in a
top-level `try` are accepted only when every handler terminates, including an exact `sys.exit(...)`
path through one uniquely bound `sys` import. Class attributes may use one
direct annotation in the class body or `__init__`; exact Playwright imports under an immutable
top-level `TYPE_CHECKING` guard are accepted for deferred annotations. Conflicting annotations,
rebound or near-package type imports, and static/class methods are withheld. Constructor flow must
begin at one exact imported `sync_playwright` call, continue through direct
browser/context creation, and assign the page field once in straight-line `__init__` code.
Conditional, repeated, later-method, and shadowed-factory assignments are withheld. Parameter reassignment
invalidates its proof, and module browser imports alone cannot promote an ordinary object's
call to one of these evaluator names. Fixed-script observations remain inventory with
`unresolved-browser-import-context` when their receiver is not yet proven. The capability still
receives an exact tool edge when it occurs in a resolved tool body, including post-definition
FastMCP tools. The call gate is structural, so chained receiver calls are inventoried even when
their dotted name cannot be reconstructed. A locator/get-by/filter/nth/and/or call or first/last property rooted
in an existing exact receiver remains proven through direct chains and one immutable local alias;
ordinary same-named methods and unknown derivations are withheld. Local construction requires a
unique exact module or direct same-function Playwright runtime import, a top-level context manager
or direct `.start()`, and immutable straight-line browser/context/page bindings; conditional imports,
branches, rebinding, and shadowed factories are withheld. A unique local
`@contextlib.asynccontextmanager` may also summarize one exact runtime→browser→context→page chain
with one unconditional page yield. Its caller must use the helper directly in a top-level
`async with` and bind one immutable name; multiple or conditional yields, exception handlers, nested
control flow, unknown yielded objects, decorator/helper rebinding, and target reassignment are
withheld. A local runtime may select `.chromium`, `.firefox`, or `.webkit` through built-in
`getattr(...)` only when the `self` selector field has one immutable class-level annotation using an
exact `typing.Literal` import, every literal is one of those three names, and its default is valid.
The resulting browser may flow into one uniquely defined, private, undecorated instance helper only
when every selected-module call is a direct same-class call or an immutable bound-method alias and
the same parameter always receives a proven local browser. Mixed or unknown arguments, other-class
attribute calls, escaped or rebound aliases, external helper definitions, and parameter reassignment
withhold the proof. A lifecycle-bound field is accepted only when `__init__` assigns it exactly once
to `None`, one undecorated async instance method assigns it exactly once from a straight-line exact
Playwright runtime→browser/context→page chain, and the intermediate fields obey the same two-write
boundary. Conditional assignments, additional mutations, decorated lifecycle methods, and locally
shadowed runtime factories withhold the proof. Private top-level helper parameters may also inherit
an exact local context-manager page proof when
the helper has one immutable definition, every selected-module call passes a proven page directly,
and the helper is never loaded as a value. Missing or mixed arguments, star expansion, ordinary
objects, function escape, module-level calls, and calls inside lambdas withhold the summary.
Caller-local shadowing of the helper or context-manager factory name also withholds the summary.
An `Any`-annotated lifecycle field may be proven across branches only when one exact Playwright
runtime root reaches every non-`None` field assignment through runtime, browser, context, page, or
exact `"popup"` event-result transitions. Unknown, tuple, or dynamic `setattr` writes, other event
names, and shadowed runtime factories withhold the field-wide summary.
Wrong wrapper attributes or fallbacks, shadowed `getattr`, and cross-branch use are withheld.
Ordinary or duplicate imported fields, near-package Playwright types, ambiguous or rebound class
imports, and reassigned context parameters or local aliases are also withheld.
Property proof requires the built-in decorator, one getter definition, and an exact imported
Playwright return type. Inherited fields, other ambiguous wrapper-returned locators, sanitizer
proofs, imported/transitive script builders, helper-return or non-unanimous helper-parameter provenance, and unsupported
browser evaluator APIs remain unresolved.

For TypeScript filesystem writes, a relative import can prove a `path-boundary` control only through
an exact two-file chain: the guard must pass the tool-derived path into a uniquely resolved predicate,
reject a false result before the write, and the predicate must normalize both candidate and roots and
use separator-aware containment. The control edge retains both source paths and carries
`policy_effect: restricts-filesystem-path` only when the roots are a statically narrow literal set;
otherwise it carries `validates-filesystem-path` with unresolved boundary scope. `AV-FS001`
suppresses only the former. Names such as `validatePath`, prefix-only comparisons, broad/dynamic
roots, and checks after the action do not establish sufficient coverage.

For Python filesystem writes, the AST frontend first proves same-function `pathlib.Path` flows. A
tool parameter must feed a candidate constructed under an explicitly resolved root, the candidate
must itself be resolved, and `candidate.is_relative_to(root)` must dominate the exact write. Both a
fail-closed rejecting branch and the positive branch of the predicate can govern a write; the latter
does not escape its branch. A `.parent` directory write additionally requires proof that the
candidate is not equal to the root. Reassigning either binding invalidates the proof. Literal absolute,
non-filesystem roots carry `restricts-filesystem-path`; parameter/configured roots carry
`validates-filesystem-path` with unresolved scope and retain `AV-FS001`. String-prefix checks,
unresolved candidates and shadowed `Path` imports are not treated as equivalent controls.

Filesystem capabilities separately record whether the governed path is derived from a current tool
input. AV-FS001 requires that fact in addition to a writable dynamic path and unresolved narrow
boundary, so configured and literal write locations remain visible inventory rather than reviews.
AV-FS002 intentionally does not require this immediate taint fact: a proven weak string-prefix
boundary remains reportable. Built-in `open(...)` retains its ordinary path semantics, while an
attribute `.open(...)` is classified as filesystem access only for a proven `pathlib.Path` receiver;
the receiver is the path and the first argument is the mode.

An exact imported cryptographic-digest helper can instead prove that tool input controls only one
separator-free path segment. The helper must have one input, use an immutable stdlib `hashlib`
SHA-256/SHA-384/SHA-512/BLAKE2 constructor over `input.encode()`, and return its unchanged
`hexdigest()`. Its immutable named import must feed a non-root argument of an exact, immutable
`os.path.join` binding whose prefix and every other dynamic segment are not tool controlled. The IR
emits `path-segment-sanitizer` with `policy_effect: removes-path-separator-control`; AV-FS001 does not
report that sink because hexadecimal output cannot express separators, dot segments, drive prefixes,
or UNC prefixes. Helper names alone, non-hex encodings, a repository-local `hashlib` shadow module,
mutable imports or stdlib attributes,
digest-derived roots, extra unsanitized segments, and a proof escaping a conditional/loop/try remain
unresolved.

A fail-closed `candidate.relative_to(root)` exception check can establish the same Python boundary
fact. The try body must contain only that check, the first handler capable of catching `ValueError`
must always terminate, and the candidate/root bindings must already be resolved and unchanged.
Continuing handlers, mixed mutation/check blocks, and parent writes without strict-descendant proof
remain unresolved. IR preserves `Path.relative_to` separately from `Path.is_relative_to` as the
control helper.

A unique same-class helper can propagate that `relative_to` fact to its caller. The helper must be a
synchronous, undecorated method; map exactly one formal path parameter through restricted `Path`
construction and an explicit zero-argument `resolve()`; perform one exclusive check with a
terminating handler; and return the same unchanged name. The caller must invoke it through its
unchanged `self`/`cls` receiver and consume the exact assigned return. Duplicate or explicitly
rebound members, generators, opaque transforms, alternate returns, post-check reassignment, and
caller reassignment invalidate the summary. Construction before the check is straight-line, and a
try `else` or `finally` block disqualifies it. These edges carry `summary: same-class-return` and keep
configured member roots unresolved, so the summary records validation without inventing a narrow
policy or suppressing `AV-FS001`.

The same flow engine records an exact `str(resolved).startswith(str(root))` predicate separately as
`path-prefix-check`, never as `path-boundary`. It follows parameter taint through tuple unpacking and
self-derived string assignments, preserves unresolved `root / input` joins until an explicit
`resolve()`, and propagates a check out of a try only when continuing handlers cannot bypass it.
The weak edge carries `policy_effect: weak-string-prefix-validation`: string prefixes do not compare
path components and can admit sibling-prefix targets. `AV-FS002` takes precedence over the generic
`AV-FS001` review at those exact sinks. Checks after the action and separator-aware expressions do
not match this specialized contract.

Python filesystem mutation calls preserve API semantics in Agent IR. Canonical and top-level
import-aliased `os`/`shutil` functions resolve only while their bindings remain unshadowed. One-path
create/delete APIs use their target argument; copy, move, rename, and replace APIs use the
destination argument, so a fixed source cannot hide a dynamic write boundary. Components record the
canonical API, `copy`/`move`/`create`/`delete` operation, and `target` or `destination` path role.
Destination expressions can inherit the same `path-boundary` proof as `open()` and `Path` writes.
Within a function, direct and conditional local callable assignments are resolved in statement
order. Branches merge only when every path leaves an alias bound to filesystem APIs with identical
path semantics; the component retains every possible API. Calls before assignment, conditional
rebinding to an unknown wrapper, and copy/delete choices are withheld. Arbitrary `.replace()`
methods and rebound import names are not promoted from their spelling alone. `Path.rename()` and
`Path.replace()` require an explicit unshadowed `pathlib.Path` constructor, an exact Path parameter
annotation, or a single immutable local derived from either. Conditional and reassigned bindings are
withheld; the destination argument remains the governed path and can inherit a boundary proof.

## Result kinds and uncertainty

- `inventory`: observed architecture facts without a risk judgment.
- `review`: a risky configuration candidate that needs surrounding context.
- `finding`: a locally demonstrated dangerous primitive or resolved unsafe flow.

Control analysis reports `present` only for a resolved governing edge. It reports `unresolved` when
coverage cannot be proven and never silently converts missing lexical evidence into “control absent.”
The first policy resolver recognizes same-function MCP tool-name allowlists that reject unknown tools
before forwarding. It also resolves literal approval on OpenAI Agents TypeScript function and
built-in tools, preserving local versus hosted shell execution. For Python files importing the
OpenAI Agents SDK, literal
`needs_approval=True` on `ShellTool`, `ApplyPatchTool`, and `CustomTool` creates an instance-scoped
tool-to-control edge when no automatic approval handler is configured; literal false is recorded as
explicitly disabled. An omitted value records the SDK's documented disabled default. Callback,
handler-controlled, and other non-literal approval policies remain unresolved.
`AV-APPROVAL003` is the bounded exception: when a configured handler resolves through unique
same-file calls to an immediate environment-backed true return, and the tool is a reachable local
shell or apply-patch built-in, the engine reports the demonstrated bypass flow. The finding retains
the exact environment names and callback-resolution basis.
Import-proven `ComputerTool` instances instead emit a local computer-control capability. Their
optional `on_safety_check` callback is recorded as SDK safety-check state, not promoted to a generic
human-approval control because it applies only when the model response carries safety checks.
Import-proven `LocalShellTool` instances emit local shell execution and explicitly distinguish an
SDK with no approval hook from one whose approval option is merely disabled. A reachable instance
can therefore trigger AV-APPROVAL002 as a review while preserving the executor as an unresolved
possible compensating control.
Schema v117 adds one repository-level proof for Trae Agent's default toolchain. The composition
requires the exact `TraeAgentConfig` literal default list, `tools_registry` class bindings,
`TraeAgent → BaseAgent` inheritance, default-`None` Docker configuration with a direct local-executor
fallback, `ToolExecutor` dispatch without an approval/confirmation branch, and both complete tool
sinks. The Bash tool's required `command` argument reaches persistent `/bin/bash` stdin; the editor's
required absolute `path` reaches `Path.write_text` after validation that proves absoluteness but no
workspace-root containment. The IR records two exact Agent→tool→capability paths plus
disabled-default isolation and unavailable-confirmation settings. Any missing source, changed
default tool, near package, decision hook, or path-boundary API withholds the entire composition.
Schema v118 adds an eight-source TypeScript composition for Roo Code's native command path. An exact
`execute_command` model schema must enter `getNativeTools`, flow through the Task tool builder, and
dispatch to the singleton `ExecuteCommandTool`. Its canonical model string must cross
`askApproval("command", ...)` before reaching `terminal.runCommand`. Separately, the Task's exact
`checkAutoApproval` call must reach the command branch that requires both global auto-approval and
`alwaysAllowExecute`, then maps `getCommandDecision(...)=auto_approve` to an approval decision. The
decision helper must parse command chains, retain deny and dangerous-substitution branches, and use
the exact raw `trimmedCommand.startsWith(lowerPrefix)` allowlist match. The resulting graph records
the default-prompt setting, command-allowlist control, agent/tool/capability path, and the missing
token boundary without flattening the surrounding safeguards. A bounded matcher or any incomplete,
duplicate, or near-package source role withholds the composition.
Schema v119 adds a separate 15-source TypeScript composition for Letta Code's default client tools.
It requires `Bash` and `Write` in the Anthropic default list, exact definition-to-implementation
bindings, declared approval requirements, the default `unrestricted` permission mode, settings/CLI
deny and always-ask checks before the mode override, classification through the WebSocket suggestion wrapper,
auto-allowed mapping to approved decisions, and approved execution through the tool manager. Bash
must reach an explicit `zsh`/`bash -c` launcher and then `child_process.spawn(..., shell: false)`;
Write must carry required `file_path` input through expansion to `writeUtf8Text`. The graph models
the permission default and the opt-in `LETTA_FS_SANDBOX` shell boundary separately, retaining
workspace and cross-agent guards as available controls. This is not a claim that controls are
absent: it proves that ordinary default actions do not prompt, the shell isolation gate is off by
default, and no general default workspace-root boundary dominates Write. Any missing or duplicate
role, a standard default, or a lookalike client package withholds the composition.
Schema v120 adds a six-source Continue CLI policy composition. It requires the plan policy's exact
Edit/MultiEdit/Write exclusions plus Bash allow, `ToolPermissionService`'s initialization and mode-
switch absolute overrides, `permissionChecker`'s disabled-only dynamic precedence, the runtime's
allow/ask dispatch, the exact non-readonly Bash tool, and the `shell-quote` evaluator's ordered
critical/high-risk/safe/unknown branches. The command must flow through `-c` into `spawn`. The graph
therefore distinguishes a selected, non-default plan mode from normal mode and distinguishes the
preserved critical hard block from discarded high-risk/unknown approval escalation. A fixed
dynamic-precedence branch or a non-shell argv runner withholds the composition.
Schema v121 adds a separate six-source Continue MCP composition. It requires the plan wildcard
allow and normal wildcard ask, absolute mode installation, first-match permission resolution, the
allow-without-prompt runtime branch, conversion of discovered MCP schemas into model tools with
`readonly: undefined`, and the `listTools`→`runTool`→`client.callTool` path. The graph models the
configured server boundary, adapter, invocation capability, selected-mode setting, and missing local
effect classification with five exact relationships. An ask wildcard, retained read-only
classification, mediated dispatch, incomplete role, or duplicate role withholds the composition.
Schema v123 adds two exact Cline approval-propagation compositions. The VS Code root host installs
explicit tool policies and a request callback, but unlisted SDK tools execute by default;
`spawn_agent` is both default-enabled and absent from the root list. The CLI sandbox path passes a
request callback, tool policies, and sandbox-forced local backend routing before delegation. Both
paths reach the local session spawn wrapper, which constructs the Act preset's local shell/edit tools
and calls the shared spawn factory without the policy or callback fields that the factory supports
and forwards to delegated agents. The graph models distinct root and child agents, delegation edges,
child privileged-tool capabilities, and approval-state-dropped controls. A spawn policy entry,
default-ask semantics, disabled spawning, non-local CLI routing, or forwarding either approval input
withholds the composition.
Import-proven `CodeInterpreterTool` instances similarly expose that their SDK constructor has no
approval hook, but they carry `execution_environment: hosted-sandbox` and
`sandbox_policy: sdk-hosted`. Literal auto-container selection is preserved as configuration
evidence; it is not treated as proof about network, persistence, or data-retention isolation.
Import-proven provider-hosted web-search, file-search, and image-generation tools use the same
unavailable-approval distinction. They emit network, data-retrieval, and media-generation
capabilities respectively, while retaining provider-hosted scope and withholding local execution or
parameter-controlled-origin claims.

Control presence is not automatically policy satisfaction. An uncaught lookup in an internal MCP
tool registry creates a `tool-registry` edge because it proves the name is routable and rejects
unknown names before forwarding. That edge carries `policy_effect: routing-only`; it does not satisfy
an explicit allowlist requirement or suppress `AV-MCP002`, because a discovery registry can contain
every tool advertised by the server. Finding analysis exposes both the governing control and its
effect even when no Agent-to-Tool edge is resolved.

A constructor-only instance attribute used directly, through a pure property, or through a
zero-argument getter creates a `fixed-tool-binding` edge with
`policy_effect: binds-tool-source-per-instance`. The proof is class-local and invalidated by any
second assignment, augmented assignment, or deletion. It removes a direct call-parameter selector
but, like a discovery registry, does not prove authorization or argument policy and therefore does
not suppress `AV-MCP002`.

The same control can carry `binding_scope: closure` when an unchanged enclosing parameter feeds a
nested callback that escapes by being returned or passed to a recognized tool/action registration
decorator. A retry or local helper closure invoked within the same caller-selected operation is not
an escaping binding. Reassigning the captured parameter also invalidates the edge. This distinction
prevents lexical nesting alone from being reported as governance.

Same-class calls receive a bounded method summary when the callee maps its tool-name parameter into
`self.get_tool(...)` or a `self.*tool*.get(...)` registry, then directly raises or returns on a
missing value in the same statement block. A return with a fallback value does not qualify. Earlier
return paths disqualify the summary unless a simple boolean parameter guard is ruled out by a
literal call argument; those required arguments are retained on the edge. The edge cites the
rejecting branch and carries `summary: same-class-method`. A fallback assignment does not qualify.
Imported or unselected manager implementations remain unresolved until their bodies are available;
class and field names are not proof of enforcement.

When a selected package reexports a registry class, the Python frontend follows only exact local
`from ... import ...` paths. A caller may inherit that class's method summary when one `__init__`
assignment binds `self.<attribute>` to the imported constructor and no other direct assignment,
deletion, or augmentation of that attribute occurs in the class. Rebound imported constructor names,
mutable attributes, fallback-returning managers, wildcard imports, and module-qualified constructor
aliases remain unresolved. The relationship cites both the consumer call and the imported rejecting
branch and carries `summary: imported-class-method`; its effect remains `routing-only`.

MCP stdio launchers may carry a separate supply-chain fact set on the `mcp-server` component:
`package_manager`, `package`, `package_spec`, `version_scope`, `auto_install`, and `install_mode`.
The Python frontend requires an MCP-module-bound constructor or a literal nested `mcpServers`
configuration. Import-proven Python constructors with another literal stdio command remain MCP
components but do not receive package facts. The TypeScript frontend requires an exact
`@modelcontextprotocol/sdk` named import of
`StdioClientTransport` or a literal `mcpServers` object, and rejects rebound/shadowed imports; the
JSON frontend requires the standard top-level `mcpServers` object. `uvx` is an automatic installer,
while `npx` is treated as automatic only with `-y`/`--yes`. An exact npm
`package@version` or Python `package==version` is distinguished from an absent version or floating
tag/range. These are launcher facts, not proof about registry integrity, lockfile provenance,
artifact signatures, transitive dependencies, or the capabilities of the installed server. In
particular, a package such as `tsx` can be the launcher runtime for local MCP source rather than the
server implementation itself.

For audit modeling, a tool capability lexically inside an OpenTelemetry
`start_as_current_span(...)` block receives an exact capability-to-`action-trace` control edge. A
span elsewhere in the same tool does not cover the action. The edge records exporter durability as
unresolved: instrumentation is not proof that an attributable record reaches durable storage.
An exact Google ADK Python path separately resolves `Runner` plugin composition, `PluginManager`
tool callbacks, and the BigQuery Agent Analytics Storage Write API. It emits a
`durable-action-audit` control only for enabled literal/default configurations and records event,
agent, user, session, invocation, and tool attribution. Delivery remains best-effort with explicit
drop accounting; nonliteral filters/configuration and incomplete framework source paths are withheld.
Skyvern Task v3 is modeled separately as `durable-action-record`: the resolver follows a
billable/recordable tool dispatch into the round callback and then through `create_action` to an
SQLAlchemy commit on the `actions` table. It preserves organization/workflow/task/step/action
correlation and completed/failed status, but does not upgrade the record to a fully attributable
audit because `created_by` is nullable and unset and persistence exceptions are contained.
`AV-AUDIT001` consumes that explicit relationship state: it reports only when a production-scope
durable action-record edge carries unresolved actor attribution. It does not treat missing tracing,
missing audit edges, or repository-level logging vocabulary as proof of an audit failure.

## Safety boundary

AgentVerify reads source and configuration as data. It never imports project modules, evaluates their
code, installs their dependencies, or launches configured MCP servers. Repository traversal excludes
and prunes dependency, build, VCS, cache, and virtual-environment directories. The research collector
preserves its 220 root-file cap and may materialize up to 20 additional local source dependencies
reached from MCP forwarding/URL-security roots or listed as versioned audited evidence hints.
Selected-path scans reject absolute and parent-traversal paths; their
reports are explicitly marked partial.

Configuration discovery includes Compose, devcontainers, and Kubernetes/Helm paths. Exact dangerous
boolean settings are reported as review results; templates and values are not rendered or executed,
and AgentVerify does not infer that a chart value governs a workload unless that relationship is
explicitly resolved. Compose short-syntax bind mounts are parsed into host path, container path,
credential class, and read-only state only when the source is an explicit host path. Sensitive SSH,
cloud, cluster, registry, package-manager, netrc, and Git credential locations become
`host-credential-mount` boundaries. Named volumes, adjacent path names, and ordinary workspaces do
not inherit sensitivity from their container destination.

The native AI BOM serializes the same evidence graph with stable observation IDs. Relationship
endpoints expose symbol-ID, evidence-location, unique-display-name, ambiguous, or unresolved
identity instead of collapsing same-named assets. It is a lossless AgentVerify format, not a claim of
CycloneDX or SPDX conformance.

Source-symbol IDs are module-qualified. When a Python or TypeScript file constructs multiple
agents/tools through the same binding, each definition receives an `@line` occurrence suffix so its
own outgoing edges stay exact. Python target references are scope-aware even when a display name has
only one observed definition: a local shadow cannot fall back to that definition. Repeated identities
resolve only when one direct definition in the same lexical or module scope appears earlier; the edge
records `target_identity: lexical-single-definition` or `module-single-definition`. One exact
constructor assignment or callable definition that is the sole same-block mutation before use records
`block-dominating-definition`. Reassignments and unproven references do not inherit an arbitrary
occurrence; repeated ones carry
`target_identity: ambiguous-repeated-binding` and remain unresolved.

Policy evaluation is a post-baseline reporting stage, not a rule filter. Gates count matching
fingerprints by rule, result kind, and minimum severity; findings remain in every output. JSON, text,
AI BOM, and SARIF retain the policy file digest, per-gate decision evidence, and matched summaries by
rule, result kind, and severity. The ordinary JSON report has a bundled schema so integrations can
validate the report contract directly; each JSON report carries `report_format` and `schema_version`
markers for artifact routing. Local `extends` composition loads base policies depth first,
deduplicates shared files by resolved path, rejects cycles and duplicate gate identities, and attaches
the contributing file digest to every gate.
Rule IDs, result kinds, severities, and confidence come from one runtime catalog. Policy loading
rejects unknown IDs and any selected rule excluded by the gate's kind or severity filters before a
scan begins; the bundled schema carries the same enabled ID set.

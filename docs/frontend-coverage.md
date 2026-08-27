# Frontend coverage and known gaps

This document separates implemented syntax from empirical corpus observations. A missing signature
does not mean a repository lacks agents or controls: AgentVerify may not support its language,
framework, wrapper, or configuration path. Counts come from schema-v123
`benchmarks/engine-results.json`, generated from the 71 pinned partial checkouts.

## Empirical coverage by repository category

“With” columns count repositories containing at least one selected-file observation of that Agent IR
kind. Categories and signature kinds can overlap.

| Category | Repositories | Source-bearing | With framework | With provider | With MCP/protocol | With capability |
|---|---:|---:|---:|---:|---:|---:|
| autonomous-agent | 3 | 3 | 2 | 3 | 1 | 3 |
| browser-agent | 3 | 3 | 2 | 3 | 2 | 3 |
| coding-agent | 15 | 15 | 9 | 7 | 8 | 14 |
| computer-agent | 1 | 1 | 0 | 1 | 0 | 1 |
| examples | 2 | 2 | 2 | 2 | 1 | 2 |
| framework | 22 | 22 | 21 | 20 | 19 | 21 |
| mcp | 9 | 9 | 2 | 3 | 8 | 8 |
| observability | 2 | 2 | 2 | 2 | 1 | 2 |
| research-agent | 1 | 1 | 1 | 1 | 1 | 1 |
| sandbox | 2 | 1 | 0 | 0 | 0 | 1 |
| tool-platform | 2 | 2 | 2 | 2 | 2 | 2 |
| visual-platform | 4 | 4 | 2 | 1 | 1 | 4 |
| workflow-agent | 3 | 3 | 2 | 3 | 1 | 3 |
| workflow-platform | 2 | 2 | 1 | 1 | 2 | 2 |
| **Total with observation** | **71** | **70** | **48** | **49** | **47** | **67** |

Observed framework signatures are LangChain (18 repositories), OpenAI Agents SDK (10), LangGraph
(8), LlamaIndex (6), Vercel AI SDK (5), CrewAI (4), Agno (3), Google ADK (3), PydanticAI (3),
AutoGen (2), Microsoft Agent Framework (2), Semantic Kernel (2), smolagents (2), AgentScope (1),
CAMEL (1), Cline SDK (1), Continue CLI (1), Dify Agent (1), Lagent (1), Marvin (1), Mastra (1), MetaGPT (1),
Letta Code (1), OpenHands SDK (2), Qwen-Agent (1), Roo Code (1), and Trae Agent (1).
Provider observations are OpenAI (43), Anthropic (25), Google (20), Azure OpenAI (12), Groq (7),
AWS Bedrock (6), Ollama (5), Cohere, Mistral, and xAI (3 each), DeepSeek (2), and Alibaba
DashScope and Moonshot AI (1 each). These overlapping exact-import/call, literal-service, and
model-string observations are lower than research-wide lexical signals.

Schema v114 identifies 25 exact `dify_agent` imports in the pinned Dify repository and resolves two
default-disabled shell run layers. Each `dify.shell` tool reaches a shell-execution capability and a
deployment-selected `sandbox-runtime` control; containment stays `external-unresolved` because the
selected API composition does not define the runtime backend. A missing runtime layer, near-name
package, enabled default, reordered guard, or rebound constructor withholds the composition.

Schema v115 adds AutoGen's current official `autogen_agentchat`, `autogen_core`, and `autogen_ext`
namespaces. Microsoft AutoGen contributes 239 selected import observations and raises framework
coverage to 42 repositories. Exact OpenAI, Azure OpenAI, and Anthropic model-client imports add 17
wrapper calls across Microsoft AutoGen and AgentOps: seven production calls, ten test calls, and 13
literal models. OpenAI-compatible `base_url` calls, near packages, and rebound constructors are
withheld. Python provider-call attribution therefore reaches 583 calls across 12 repositories: 20
native SDK calls and 563 wrappers, with 242 production calls, 341 tests, and 458 literal models.

Schema v116 recognizes exact Python `openhands` imports in both pinned OpenHands repositories,
raising selected-path framework coverage to 44 repositories. The SDK checkout contributes 1,173
import observations across 186 selected files; the application checkout contributes two more. An
exact module-level composition resolves 11 `TerminalTool`/`FileEditorTool` registrations across six
SDK examples, their Agent reachability, and conversation-scoped analyzer/confirmation state. The
MCP example installs `LLMSecurityAnalyzer` but retains the SDK 1.42.1 `NeverConfirm` default, so
`AV-APPROVAL006` reports one review. The paired security example installs `ConfirmRisky`, preserving
its default `HIGH` threshold and `confirm_unknown=True` as a human-approval control. Six reachable
`FileEditorTool` instances remain `AV-FS001` reviews because the implementation uses the workspace
as a working directory hint but accepts agent-supplied absolute paths without a containment check.
Near packages, rebound factories, non-`.name` tool references, dynamic policies, and incomplete or
multiply assigned chains remain unresolved.

Schema v117 recognizes exact Python `trae_agent` imports and resolves Trae Agent's default tool
composition only when seven source roles agree: the four-name default tool list, registry mappings,
`TraeAgent`/`BaseAgent` inheritance and routing, the direct `ToolExecutor`, persistent `/bin/bash`
stdin sink, and absolute-path editor sink. The pinned repository contributes two production
Agent→tool edges, two capability edges, and four exact control-setting edges. Its default
`docker_config=None` selects the local executor, whose direct dispatch exposes no per-action
decision hook; the editor requires an absolute path but proves no workspace-root containment. The
composition therefore adds one finding each to AV-EXEC001, AV-APPROVAL002, and AV-FS001. A changed
default list, missing source role, added executor decision hook, editor boundary check, duplicate
composition, or near package withholds the entire graph.

Schema v118 recognizes exact TypeScript `@roo-code/*` imports and resolves Roo Code's native
`execute_command` path across eight source roles: model schema, native registry, model-tool builder,
Task runtime, assistant-message dispatcher, command executor, auto-approval router, and command
decision helper. The model-controlled command reaches local `terminal.runCommand` only after an
approval callback. Auto-approval is disabled when its state is absent or false and additionally
requires `alwaysAllowExecute`; when enabled, however, allowlist selection accepts a raw
case-insensitive `startsWith` match without proving an executable or argument token boundary. The
graph records chain parsing, denylist conflict handling, and dangerous-substitution checks while
AV-APPROVAL007 reports only the remaining weak-prefix seam. Near packages, incomplete source chains,
and a token-boundary matcher withhold the composition.

Schema v119 recognizes exact TypeScript `@letta-ai/letta-client` imports and requires a 15-source
Letta Code composition before resolving the default Bash and Write tools. The proof joins the
Anthropic default list, tool-definition implementations, declared approval requirements, scoped
permission mode, settings/CLI deny and always-ask precedence, approval classification and suggestion wrapper,
interactive-tool policy, WebSocket auto-allowed decision mapping, approved execution, explicit
shell launcher, child-process sink, optional shell sandbox, and filesystem write sink. The default
`unrestricted` mode turns ordinary Bash/Write approvals into allow decisions, but explicit deny,
always-ask, workspace-sandbox, and cross-agent-memory guards remain represented. The shell sandbox
is opt-in through `LETTA_FS_SANDBOX`; the Write implementation proves no general default
workspace-root containment. The graph adds two Agent→tool, two capability, and four control-setting
edges and one finding each for AV-EXEC001, AV-APPROVAL002, and AV-FS001. A standard default,
near-package import, missing role, or duplicate role withholds the entire graph.

Schema v120 adds a six-source Continue CLI composition joining plan-mode policy selection, absolute
mode override, dynamic permission precedence, runtime approval dispatch, the model-visible `Bash`
tool, and the `shell-quote` risk evaluator. Normal mode remains the default and asks for Bash;
selected plan mode excludes Edit/MultiEdit/Write but statically allows Bash. The evaluator's
`disabled` result still blocks critical commands, while `allowedWithPermission` for high-risk and
unknown commands is replaced by the static allow before the login-shell spawn. The graph records
that compensating hard block and emits one `AV-APPROVAL008` review plus the exact `AV-EXEC001` sink.
Missing roles, a retained dynamic ask, or a non-shell argv path withholds the composition.

Schema v121 adds a separate six-source Continue MCP composition. The proof joins the plan-mode
wildcard allow and absolute override with first-match permission resolution, the runtime's
allow-without-prompt branch, the dynamic MCP adapter, server discovery, and the final
`client.callTool` sink. Every discovered tool is model-visible while the adapter explicitly leaves
`readonly` undefined, so no locally enforced read-only or risk classification constrains the
wildcard. Normal mode still asks, plan mode remains non-default, and only configured MCP servers are
reachable. Missing roles, an ask wildcard, retained read-only classification, or a mediated sink
withholds the composition and `AV-APPROVAL009` review.

Schema v123 adds a second Cline composition for approval propagation across delegation. The VS Code
path proves explicit root approval policies and a live callback while the SDK defaults unlisted
tools to auto-approved and leaves `spawn_agent` out of the explicit list. The CLI sandbox path proves
startup `toolPolicies`, `requestToolApproval`, and sandbox-forced local backend routing before
delegation. Both paths reach a local session wrapper that builds child `run_commands` and `editor`
tools but does not pass `toolPolicies` or `requestToolApproval` into a factory that supports and
forwards both. Missing roles, a gated spawn tool, disabled spawning, non-local CLI routing,
default-ask semantics, or either forwarded approval input withholds the composition and
`AV-APPROVAL010` review.

Schema v73 identifies 29 exact Python provider calls across seven repositories: 20 native Mistral,
Groq, Cohere, or Ollama SDK calls and nine LangChain wrappers. Seven calls across five repositories
are production-scoped; 22 calls and all 12 literal call-model arguments occur in tests. These call
facts refine configured use without changing the 48-repository provider-presence total.

Schema v74 adds exact TypeScript call proof for the official Mistral, Groq, and Cohere AI SDK
providers. Named aliases, destructured dynamic imports, top-level CommonJS destructuring, provider
factories, and immutable configured instances are supported; rebindings and near-name packages are
withheld. The pinned corpus contains one production dynamic-import Groq model call in Mastra and no
test-scoped calls or literal call-model arguments.

Schema v75 expands the Python call inventory to 63 calls across eight repositories: 20 native SDK
calls and 43 wrappers, comprising nine LangChain, 32 PydanticAI, and two AgentScope calls. Nine calls
across six repositories are production-scoped; 54 are tests. Of 35 literal call-model arguments, the
two production values come from AgentScope's public Ollama model reexport and the other 33 are tests.
This exact wrapper evidence raises provider presence to 49 repositories and Ollama presence to five.

Schema v76 makes the AgentScope reexport map symbol-specific and adds eight production calls: four
OpenAI Chat/Responses, two Anthropic, and two Google Gemini. Python therefore has 71 exact provider
calls across eight repositories: 20 native SDK calls and 51 wrappers, split into nine LangChain, 32
PydanticAI, and ten AgentScope calls. Seventeen calls across six repositories are production-scoped;
54 are tests. All 43 literal call-model arguments retain the exact provider proof. Repository
presence remains 49, while OpenAI rises to 42 repositories and Anthropic and Google to 18 each.

Schema v100 extends the same exact-export map with AgentScope's Alibaba DashScope, DeepSeek,
Moonshot AI, and xAI chat models. Nine additional production calls all carry literal models: four
DashScope, one DeepSeek, two Moonshot, and two xAI. Python therefore has 80 exact provider calls
across eight repositories: 20 native SDK calls and 60 wrappers, split into nine LangChain, 32
PydanticAI, and 19 AgentScope calls. Twenty-six calls across six repositories are production-scoped;
54 are tests, and all 52 literal call-model arguments retain exact provider proof. Repository
presence remains 49 because all four providers occur in the already-covered AgentScope repository.

Schema v101 expands exact PydanticAI attribution to dedicated Anthropic, Google/Google Cloud, AWS
Bedrock, xAI, and DeepSeek provider, model, and embedding modules. PydanticAI's selected tests add
263 calls and 175 literal model values; Marvin adds three production calls, two Anthropic and one
DeepSeek. Python now has 346 exact calls across nine repositories: 20 native SDK calls and 326
wrappers, split into nine LangChain, 298 PydanticAI, and 19 AgentScope calls. Twenty-nine calls
across seven repositories are production-scoped, 317 are tests, and 227 carry literal models. The
generic PydanticAI `OpenAIModel` and `OpenAIProvider` remain excluded because selected production
code configures the same surfaces for Azure, DeepSeek, AIMLAPI, and arbitrary compatible endpoints.

Schema v102 adds Agno's dedicated public and direct model modules for OpenAI Chat/Responses, Google
Gemini, Anthropic Claude, Azure OpenAI, and Groq. The corpus contains 220 exact calls: 200 production
calls in Agno, six production calls in AgentOps, and 14 OpenLLMetry tests. Of these, 218 retain a
literal `id=` or positional model value. Python now has 566 exact calls across 11 repositories: 20
native SDK calls and 546 wrappers, split into nine LangChain, 298 PydanticAI, 19 AgentScope, and 220
Agno calls. Two hundred thirty-five calls across nine repositories are production-scoped; 331 are
tests, and 445 carry literal models. No selected Agno call overrides its provider or endpoint;
custom OpenAI/Groq `base_url` calls are explicitly withheld.

Schema v103 expands official TypeScript AI SDK call attribution to OpenAI, Anthropic, Google, Azure
OpenAI, and xAI. Together with the existing Groq path, the corpus now contains 33 production calls
across five repositories: 31 model calls and two provider factories. Four inline or immutable
configured-instance calls are identified, and 22 direct literal model IDs are retained. The provider
split is 14 OpenAI, 13 Anthropic, three Google, one Azure OpenAI, one xAI, and one Groq. Exact
static/dynamic imports, direct language and image calls, and observed embedding factory chains are
supported. Factories with a literal `baseURL`, arbitrary object spread, or nonliteral config are
withheld; endpoint-neutral `spreadIfDefined('apiVersion', ...)` is accepted for Azure-style default
configuration. Generic `@ai-sdk/openai-compatible` calls remain withheld, and pinned negatives cover
Inception, Azure-hosted Anthropic, and a mock OpenAI endpoint.

Schema v104 adds native TypeScript SDK constructor proof for exact ESM imports from `openai`,
`@anthropic-ai/sdk`, and `@google/genai`. The corpus contributes 17 production constructors across
five repositories: ten OpenAI, four Anthropic, and three Google. Combined with schema v103's 32
official AI SDK calls, TypeScript has 49 exact production calls across eight repositories. Native
constructors require no arguments or a literal, spread-free configuration without `baseURL` or
`baseUrl`; unknown configs, nested custom endpoints, rebindings, and broad CommonJS imports are withheld.
Official AI SDK CommonJS destructuring is treated separately and only for top-level exact package
requires of supported provider symbols.
Anthropic presence rises from 21 to 24 repositories; OpenAI remains 43 and Google remains 20.

Schema v105 adds the exact CommonJS default-export form used by two GPT Pilot templates. Four
additional production constructors—two OpenAI and two Anthropic—raise TypeScript attribution to 53
calls across nine repositories: 21 native SDK constructors and 32 official AI SDK calls. The proof
requires one immutable module-level `const Client = require('openai' | '@anthropic-ai/sdk')` binding; reassignment,
shadowing, unknown/custom configs, non-default require shapes, and scoped requires remain
unresolved. Local regressions now additionally accept exact direct or aliased named destructures
such as `const { GoogleGenAI } = require('@google/genai')` and
`const { GoogleGenAI: GeminiAliasClient } = require('@google/genai')`; broader Google CommonJS forms
remain withheld.
Provider-presence counts do not change because GPT Pilot already had exact import evidence for both
providers.

Schema v106 follows immutable native SDK constructor bindings into exact downstream model methods.
The selected corpus adds three production OpenAI calls and literal models: `gpt-4o` and
`gpt-4o-mini` in Composio plus `gpt-3.5-turbo` in AgentGPT. TypeScript therefore has 56 exact calls
across nine repositories: 21 constructors, three native model calls, and 32 official AI SDK calls.
Only the exact OpenAI, Anthropic, and Google method chains with a direct first-argument object and
literal `model` property are supported. Rebound clients, nonliteral request objects, unrelated
methods, and typed-parameter client propagation remain unresolved.

Schema v107 resolves one typed-parameter model path through a same-file fixed point. OpenAI Agents
JS passes an inline default-endpoint client through four unique non-exported helpers before calling
`client.responses.create({model: 'gpt-5.4'})`. Type annotations and qualified SDK types no longer
count as constructor shadowing, which also recovers an Anthropic constructor in MCP TypeScript SDK.
TypeScript reaches 59 exact calls across nine repositories: 23 constructors, four native model
calls, and 32 AI SDK calls. The typed proof requires unanimous direct call sites; exported helpers,
mixed or unproven arguments, cycles without a constructor root, and actual parameter shadowing are
withheld, as are functions passed or stored as values.
Current local regressions also cover non-exported `const` arrow helpers with balanced block bodies
under the same call-site consensus rule. Exported, mixed-call-site, escaped, and expression-bodied
arrow helpers remain unresolved.

Schema v108 separates exact provider-request identity from literal model identity. A proven native
client now contributes an exact provider call for its provider-owned request method even when the
request object or `model` value is runtime data; a model component is still created only for a
direct literal `model` property. Four dynamic-model requests in GPT Pilot are recovered from
immutable direct bindings. Five more requests flow through readonly fields assigned exactly once in
the same class: OpenAI, Anthropic, and Google in Bytebot plus Anthropic and Google in MCP TypeScript
SDK. TypeScript reaches 68 exact production calls across nine repositories: 23 constructors, 13
native request calls, and 32 AI SDK calls. Five native requests use the class-field proof, while 26
literal models remain unchanged. Mutable or multiply assigned fields, custom endpoints, nonliteral
constructor configs, and unrelated methods remain withheld.

Schema v109 follows one additional same-class receiver shape: a private getter whose entire body
uses `??=` to cache an exact default-endpoint native client in a private backing field. The backing
field must have exactly one declaration, no other writes, and the getter must have no setter; public,
uncached, resettable, and custom-endpoint forms remain withheld. The MCP TypeScript SDK quickstart
adds two Anthropic `messages.create` requests through this proof. TypeScript reaches 70 exact
production calls across nine repositories: 23 constructors, 15 native request calls, and 32 AI SDK
calls. Two native requests use the accessor proof; literal models remain at 26 because the quickstart
passes a module constant rather than a direct literal property.

Schema v110 resolves that model constant without broad identifier propagation. Once provider and
request-method provenance are already exact, a direct `model: NAME` property may inherit an earlier
module-level `const NAME[: string] = 'literal'`. The binding must have one declaration and assignment
and no parameter, import, catch, or destructuring shadow. The two MCP TypeScript quickstart requests
therefore gain `claude-sonnet-4-6` model components with an explicit immutable-literal resolution
basis. TypeScript call counts remain 70, while literal models rise from 26 to 28. Mutable, forward,
shadowed, rebound, runtime-parameter, unknown template, and helper-object model expressions remain
withheld. A local regression now accepts the narrow composed case where a module-level template
string interpolates only earlier immutable literal bindings, preserving the same
`immutable-module-literal-binding` basis.

Schema v111 reuses that proof for official AI SDK model arguments. Activepieces' configured OpenAI
embedding provider now resolves the earlier `OPENAI_3_SMALL_MODEL_ID` constant to
`text-embedding-3-small`, while its provider call remains the same exact AI SDK call. TypeScript
call counts stay at 70 and literal models rise from 28 to 29; three model components now record the
immutable-module-literal basis. Runtime parameters in Activepieces and Mastra, plus mutable,
forward, composed, shadowed, and rebound fixture arguments, remain withheld.
Official TypeScript AI SDK calls now also support exact local named and star reexports: a local
import may carry provider/model attribution when its target module's reexport chain resolves to one
supported `@ai-sdk/*` instance or factory symbol. Local regressions pin direct OpenAI reexport,
Google factory reexport, transitive OpenAI reexport, Azure factory reexport, and single-symbol
star-barrel positives plus ambiguous-reexport, duplicate-star-barrel,
function-parameter-shadowing, and Azure baseURL-spread negatives. Module-object access and
ambiguous local provider barrels remain withheld.
Activepieces' workspace `createLanguageModel({ provider, modelId })` wrapper remains withheld in the
pinned corpus because the `@activepieces/ai-providers` implementation is absent from the source
snapshot and the same helper has a Cloudflare `@ai-sdk/openai-compatible` custom endpoint branch.
Three real-source negative labels pin that provider/model boundary.
The same immutable-module-literal basis now also covers exact module-level literal object maps such
as `MODEL_IDS.chat`, `MODEL_IDS["chat"]`, or `MODEL_IDS["chat-model"]` for native request objects
and official AI SDK first model arguments. The object must be a single top-level `const` with direct
literal string properties and no object/member reassignment; mutable object properties, nonliteral
object values, dynamic bracket keys, dynamic bracket member writes, and unknown template values
remain withheld. Local regressions now pin nine positive object-map model labels and eight guarded
negatives. Exact `@ai-sdk/azure` factory/configured embedding calls are now covered with a matching
custom-endpoint spread negative and a real Activepieces Azure embedding provider label. Together with
the expanded local-reexport, real Activepieces boundary, and TypeScript sandbox-helper labels, the
public IR truth set now covers 1,803 labels.

Schema v77 separates Python MCP process inventory from package-launcher provenance and adds exact
Agent→MCP-server identities. Import-proven literal stdio constructor calls are inventoried for any
literal command; their assigned results receive stable IDs. Package/version/install facts are
attached only when `npx` or `uvx` proves a package selection. A direct edge requires an earlier,
unreassigned same-block binding named in a
literal `mcp_servers=[...]` list. Forward references, rebound servers, indirect list variables, and
cross-scope module globals are deliberately unresolved.
The pinned corpus contains 27 such literal constructor calls across seven repositories: 23 assigned
servers receive stable IDs, 20 calls launch non-package processes, and seven select packages. Ten
calls are production-scoped. The only two exact Agent edges are both production-scoped and resolve
the Deno and `uvx` bindings in Marvin.

Schema v78 adds exact `fastmcp` and `mcp.server` FastMCP constructor inventory with
`transport: in-process`. It also links a sole immutable module assignment into a later literal
Agent list inside a function or module control block. Definition order and every enclosing lexical
scope are checked; module rebinding, parameter/local shadowing, conditional definitions, forward
lexical order, and near-name FastMCP modules are withheld.
The corpus contains 240 exact in-process constructor calls across 13 repositories; 227 assigned
results receive stable IDs and 22 calls are outside tests. Python Agent→MCP coverage reaches four
fully resolved edges in Marvin: two same-block and two immutable-module bindings, with three outside
tests.

Schema v79 resolves top-level `try` imports only when every handler terminates, then connects an
immutable exact FastMCP registrar to its decorated or post-registered tools. Capability context
traverses the resulting Agent→server→tool chain. Optional imports that continue, rebound servers,
ambiguous registrations, and name-only matches remain disconnected.
The fail-closed import raises assigned in-process identities to 228 and Agent→server edges to five.
Across eight repositories, 121 exact FastMCP server→tool edges resolve both symbol endpoints; 89 are
outside tests. Marvin contributes four production Agent→server edges, three
Agent-reachable registered tools, and one production filesystem capability with the full path.

Schema v80 adds exact context-manager identity. The stdio inventory now contains 41 constructor
calls across eight repositories: 34 assignment-bound and three context-managed calls have stable
IDs, for 37 bound assets total; 11 calls are outside tests and seven remain package-backed. The
three context-managed assets occur in OpenAI Agents Python and Agno. A direct, unreassigned in-body
reference produces the sixth exact Python Agent→MCP edge and expands repository coverage from one to
two. The OpenAI edge shares its server ID with the SDK's disabled-default approval evidence.
Exact `agents.sandbox` imports also identify 156 OpenAI `SandboxAgent` assets, 15 outside tests; one
has the context-managed MCP edge. Duplicate, rebound, escaped, nested, and near-import forms remain
withheld.

Schema v81 resolves a project-local adapter only when its immutable top-level class directly
subclasses an exact `agents.mcp.MCPServer`, `agents.mcp.server.MCPServer`, or
`pydantic_ai.mcp.MCPServer` import and directly defines both `list_tools` and `call_tool`. A unique,
unreassigned local import and earlier same-scope instance can then use the standard literal Agent
binding. Skyvern contributes the one corpus instance and edge; it is production-scoped. Near bases,
incomplete adapters, rebound bindings, and forward references remain withheld.

Schema v82 resolves eight test-scoped OpenAI SandboxAgent handoff edges through two exact local
function definitions. Each helper is undecorated, uniquely defined before its direct same-block
calls, and has one direct top-level return of an import-proven Agent constructor. Six fixture forms
with conditional or indirect returns, helper rebinding, forward use, constructor shadowing, or
result rebinding stay unresolved. No production edge is added.
TypeScript OpenAI Agents sandbox examples now contribute exact `@openai/agents/sandbox`
`SandboxAgent` inventory and sandbox `shell()`, `filesystem()`, `memory()`, and `skills()` capability
edges when the agent is directly assigned or directly returned from a same-file helper using exact
imported constructors and lists literal `capabilities`. Real OpenAI Agents JS examples pin
SDK-sandbox shell, filesystem, memory, and skill-loading reachability without promoting them to
host-local shell/filesystem risk; near-package, rebound-constructor/capability, aggregate capability,
and conditional helper fixtures remain unresolved.
Exact `@openai/agents/sandbox/local` `UnixLocalSandboxClient` and `DockerSandboxClient` imports also
record `sandbox-runtime` controls when they are passed directly as `run(..., { sandbox: { client } })`
or through one exact `client.create(...)` session binding, including inline
`await new Client(...).create(...)` session assignments and object-shorthand
`{ sandbox: { session } }`; typed session variable declarations are accepted when the initializer is
still a proven client `.create(...)` call. Variables initialized by direct calls to already-proven
same-file `return new SandboxAgent(...)` helpers can also carry those session edges, which covers
shared session multi-agent examples without treating generic factories as evidence. Exact imported
`Runner` instances can additionally carry per-call `runner.run(agent, ..., { sandbox: { session } })`
session options, distinct from Runner-constructor sandbox config. Delegated sandbox agents can also
inherit `SandboxAgent.asTool({ runConfig: { sandbox: { session } } })` runtime edges, so
agent-as-tool execution keeps its own sandbox context rather than only the orchestrator delegation.
Literal numeric `exposedPorts` arrays on exact `DockerSandboxClient`/`UnixLocalSandboxClient`
constructor configs are recorded as `sandbox-network-exposure` controls linked back to the
corresponding `sandbox-runtime`, preserving reviewer visibility into deliberate sandbox port
exposure without treating it as host-local network execution.
Literal `extraPathGrants` Manifest entries are also recorded as `sandbox-path-grant` controls when
their `path` is a direct string or earlier immutable module-level string binding and `readOnly` is a
literal boolean; dynamic path construction and unknown Manifest constructors remain unresolved.
Literal `environment` Manifest entries are recorded as `sandbox-environment-variable` controls for
direct string values or earlier immutable module-level string bindings; values for secret-like
variable names are redacted in IR attributes.
Rebounded local-client imports, unknown session factories, half-known ternary client selection, and
aggregate helper contents remain unresolved.

Schema v83 recognizes OpenAI Agents Python `LocalShellTool` only through one immutable top-level
import from `agents` or `agents.tool`. It records the SDK's lack of an approval parameter as
`approval_policy: unavailable`, keeps the executor as an unresolved possible compensating control,
and emits a local shell-execution capability. The pinned SDK contains five test-scoped instances,
five capability edges, and four exact Agent bindings. A near-package import and a rebound exact
import remain unclassified; two resumed-state test bindings remain conservatively ambiguous.

Schema v84 applies the same exact-import boundary to OpenAI Agents Python
`CodeInterpreterTool`. Five pinned instances across two repositories now emit hosted-sandbox
code-execution assets and capability edges; two production examples use literal auto-managed
containers and resolve directly from their Agents. All five record that the SDK constructor exposes
no approval parameter. Symbolic or casted container configs remain unresolved, and near-package or
rebound constructors remain unclassified. These sandboxed inventory facts do not raise AV-EXEC002.

Schema v85 extends the exact-import inventory to provider-hosted `WebSearchTool`,
`FileSearchTool`, and `ImageGenerationTool`. Thirteen instances across three repositories include
seven production assets, 13 capability edges, and eight exact Agent bindings. Six web-search assets
retain the SDK-default external-access state, four file-search assets distinguish two literal
vector-store scopes from unresolved configuration, and three image-generation assets record their
provider-hosted media boundary. All 13 expose no constructor approval parameter. Exact `agents` or
`agents.tool` imports are required, so same-named smolagents, PydanticAI, CrewAI, near-package, and
rebound constructors stay unclassified. Provider-hosted web search is inventory, not AV-NET001,
because it does not expose a source-proven parameter-controlled origin.

Across the selected snapshot, 10,069 observations have module-qualified symbol IDs. Of
4,756 relationship endpoint observations, all 3,946 identified endpoints resolve to an observed
component (3,587 Python and 359 TypeScript). Two former false IDs on CrewAI test edges are now
withheld because a function parameter and assignment shadow the same-named package import.
Repeated Python and TypeScript constructor bindings are occurrence-qualified. Their direct source
edges resolve exactly. The current schema records 379 Python lexical-single-definition, 20 same-block
dominating-definition, 25 contextual-absolute-import resolutions, three same-class helper-return
resolutions, 14 contextual imported-class Agent-factory resolutions, 444 inline constructor
resolutions, four context-manager resolutions, four contextual imported-callable exports, six
absolute-import binding edges, and one typed-tool-parameter
resolution. The latter uses an import-proven `ApplyPatchTool` annotation and ten unanimous
same-module constructor call sites to create an occurrence-qualified parameter component that
retains every concrete target ID. Same-block function-factory resolutions include exact
module-qualified framework constructors while withholding conditional, forward, and rebound helper
flows; schema v83 records two new explicit ambiguities for resumed-state LocalShellTool references
that lack a unique lexical occurrence. Inconsistent, uncalled, rebound, shadowed, reassigned, and
non-exact typed fixture forms stay unresolved.
All seven exact Python Agent→MCP-server edges resolve both endpoints. Marvin contributes five—two
same-block and three immutable-module bindings—and OpenAI Agents Python contributes the
context-managed edge. Skyvern contributes one same-block imported-adapter edge. Six edges are outside
tests. Package facts remain isolated to the relevant launcher.
Literal Python Agent tool lists recover 755 exact role-proven tools: 181 callables, 100
constructor-bound instances, 444 inline constructors, four direct context-manager bindings, 21 exact
Agent-as-tool adapters, and five absolute-import boundary tools. Of these, 526 are outside tests;
they contribute 30 capability edges and 812 exact Agent edges. Each Agent-as-tool adapter has one
exact delegation edge to its same-block Agent receiver. Thirty use immutable module-level definitions. Four imported callables
resolve to exact selected local definitions; unavailable absolute-import sources retain a boundary
identity without inferred capabilities. Imported `from_settings` tool factories, exact
`HostedMCPTool` and `LangchainTool` constructors, and exact same-block `Agent.as_tool()` adapters
resolve the final six former production misses. Across all 1,222 Python Agent→tool edges, all 623
outside tests resolve; the 70 unresolved edges are confined to tests and conservative fixtures.
Import-proven OpenAI `function_tool(function)`
assignments recover 12 wrappers and 12 Agent edges; all are tests, three enable approval, and their
selected bodies add no recognized capability edges. Import-proven Python `ComputerTool`
constructors contribute 15 computer-control assets and ten exact agent links; their optional
`on_safety_check` callback is inventoried separately from generic approval policy. All 15 are local,
two configure the callback, and one occurs outside test paths in the pinned SDK example.
Exact-import `LocalShellTool` adds five local shell assets and five capability edges, all under tests;
four Agent edges resolve, and all five assets record that the SDK exposes no approval parameter.
The exact provider-hosted built-ins add 13 assets and capability edges, including seven production
assets and eight resolved Agent edges.
Capability/control taxonomy endpoints intentionally lack
source-symbol IDs, so the endpoint fraction is inventory coverage rather than an accuracy or recall
metric.

The native AI BOM 1.2 resolver independently classifies all 4,756 endpoints: 3,938 by symbol ID, 701
by exact relationship evidence, 21 by a unique display name, 38 as ambiguous, and 58 as unresolved.
Evidence-local resolution removes capability/control ambiguities; occurrence-qualified bindings
resolve repeated source agent/tool observations, and conservative lexical resolution removes further
target ambiguities. The remaining 38 ambiguous endpoints are agent, protocol, control, or tool targets without a unique
local symbol or target location.

The TypeScript graph contains 107 structure-backed agent edges: 14 agent-as-tool delegations, 87
agent-to-tool edges, and six other agent-composition edges. All 87 tool endpoints resolve to an
observed component. This replaces a prior
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
Schema v113 adds one separate Python `path-segment-sanitizer` edge in Qwen-Agent: exact imported
SHA-256 hexadecimal output controls only a non-root joined cache segment. This removes one AV-FS001
review and one repository from that rule without treating discovery roots or generic sanitizer names
as containment policy.

The Python frontend also resolves all 115 Skyvern tools registered after definition through exact
`mcp.tool(...)(function)` applications. Every target is reached through one immutable relative
import and one unique module-level function definition. Ninety-three registrations are direct; 22
pass through proven metadata-preserving forwarders, totaling 23 wrapper layers because one tool has
a two-wrapper chain. The wrappers must use `functools.wraps` and directly forward `*args, **kwargs`
to the wrapped callable. All 115 tools create only 22 exact capability edges—14 browser actions, seven
browser-page evaluations, and one filesystem mutation—so inventory expansion is kept separate from
finding volume. Of Skyvern's 36 inventoried Playwright evaluations, only `skyvern_evaluate` receives
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
two exact callee summaries. A local module-qualified fixture now also resolves `parsers.UrlParser()`
style calls when the module alias comes from one exact local import and remains unrebound. Fixed
arguments retain inventory edges. Multiple assignments, `setattr`, constructor
shadowing/rebinding, duplicate classes, and locally shadowed module aliases remain unresolved. A
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
`origin_authority: tool-execution-arguments` and `destination_policy: absent-on-proven-path`.
Schema v112 then resolves five Google ADK Python helper arguments back to two immutable imported
`https://api.github.com` constants, reducing the corpus to 18 AV-NET001 reviews across 11
repositories. Each fixed-origin capability retains the source module and line. A guarded transport,
fixed argument map, broken schema gate, or wrong import withholds a dynamic path.

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
edge and a path derived from a tool input. Expanded registry, literal tool-role, and OpenHands
built-in reachability produces 41 filesystem reviews across ten repositories. Four CrewAI Examples
sinks are specialized as AV-FS002, leaving 37 AV-FS001 sites across nine repositories. Four newly
reachable Marvin sinks cover dynamic writes and deletion configured through module-level callable
tools. Fixed paths remain inventory-only, and attribute `.open()`
is treated as filesystem access only for a proven `pathlib.Path` receiver. The Skyvern review is
`resolved.parent.mkdir(...)` in its registered state-save tool: the validator admits equality with an
allowed root, so the parent mutation is not proven to remain inside that root. No pinned mutation
destination has a statically narrow guard, so the corpus records zero guarded calls in this API
subset. Qwen-Agent's former directory-creation review is now a negative: the exact imported
`hash_sha256` helper returns `hashlib.sha256(input.encode()).hexdigest()`, and that value occupies
only a non-root `os.path.join` segment beneath `self.data_root`. The control is withheld for generic
sanitizer names, mutable stdlib/import bindings, non-hex output, a digest-derived root, another
tool-controlled segment, and control-flow escape.

## Implemented syntax

| Frontend | Implemented observations and resolution |
|---|---|
| Python AST | Imports; known agent/model constructors; ordinary tool decorators; import-proven MetaGPT/Qwen registry decorators with literal class entrypoint resolution; literal tool/handoff lists with exact local and immutable module callables, exact selected local or absolute-SDK import bindings, literal-`__all__` star imports from selected local callable modules, exact framework-constructor star imports from a narrow module map, import-proven constructor bindings, occurrence-qualified inline constructors, direct context-manager bindings, and OpenAI `function_tool(function)` wrapper recovery; exact same-class direct/tuple Agent-return propagation into caller composition; import-proven OpenAI built-in typed parameters with unanimous same-module constructor call sites; exact default-disabled Dify Agent shell/runtime run-layer composition; exact OpenHands built-in terminal/file-editor reachability with conversation analyzer and confirmation-policy state; module-, class-, parameter-, and repeated-occurrence-qualified agent/tool IDs; shell, Python eval/exec, Playwright/Selenium/Puppeteer-context `.evaluate(...)`, filesystem, Requests/httpx/aiohttp plus import-proven `urllib.request.urlopen` and `Request(url)`, browser, MCP, and Docker SDK calls; import-bound MCP launcher constructors plus literal nested `mcpServers` dictionaries, including literal argument prefixes and exact npm/Python package pin state; exact Semantic Kernel MCP sampling callback/default/model-authority composition and exact MCP `ClientSession` sampling result/consent callbacks; browser-page execution context with direct tool-parameter/alias flow, literal discrimination, exact Playwright parameter/class-attribute receiver annotations (including immutable `TYPE_CHECKING` imports), exact constructor-bound page fields/local aliases, known Locator derivations, structural chained-evaluator inventory, and a provenance-locked Skyvern page factory; canonical, top-level import-aliased, and statement-ordered local callable-aliased `os`/`shutil` create/copy/move/delete mutations with compatible branch merging, destination roles, and rebinding invalidation; `Path.open`/`rename`/`replace` through proven receivers; tool-input filesystem-path state plus exact imported hexadecimal cryptographic-digest path-segment sanitizers; tool-parameter HTTP origins with direct alias propagation plus fixed-origin constants, instance fields, concatenation, and `.format(...)`; exact fail-closed `urlparse`/`urlsplit` scheme+hostname controls with redirect/DNS scope; source-proven imported secure transports with initial/redirect URL, proxy, DNS, peer, default, and escape-hatch state; unique top-level imported network-function summaries plus iterative single-entrypoint registered-class summaries through direct constructors or immutable fields; repository-unique, filesystem-relative, and importer-ancestor-single-path absolute imports with exact decorated class-tool export validation; literal approval decorators; OpenAI Agents `ShellTool`/`ApplyPatchTool`/`CustomTool` approval constructors plus `ComputerTool` computer-control and safety-check-callback inventory; env-backed auto-approval flags with direct true-return branches and same-class approval short circuits; statement-ordered MCP rejection guards, internal tool-registry routing lookups, same-class rejecting registry-method summaries with literal boolean path selection, immutable constructor-bound imported registry summaries through exact package reexports, constructor-only fixed tool bindings through direct attributes or pure accessors, unchanged captured parameters in returned/registered callbacks, same-function resolved `pathlib.Path.is_relative_to()` or fail-closed `relative_to()` exception boundaries, exact same-class checked-Path return summaries, and non-suppressing string-prefix path checks with dominance and reassignment invalidation; lexically scoped OpenTelemetry spans; exact Google ADK `Runner`/`PluginManager` tool callbacks composed with the BigQuery Agent Analytics Storage Write sink; exact Skyvern Task v3 recordable dispatch/callback composition into its committed SQLAlchemy `actions` table. |
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
  MetaGPT, Marvin, AgentScope, OpenHands SDK, AutoGen's legacy and current official Python namespaces, and Vercel AI
  SDK alongside the original signatures. The `ai` package
  is TypeScript-only evidence. Package reexports, Pydantic wrappers beyond direct imports, and custom
  agent bases may still leave a generic `Agent` without framework attribution.
- Google provider taxonomy requires an exact GenAI/Vertex/AI SDK import or a Gemini model prefix.
  AWS Bedrock requires its exact TypeScript runtime SDK, a recognized `langchain_aws` constructor
  import, or a literal `bedrock-runtime` service selection. Mistral, Groq, Cohere, and Ollama support
  exact Python SDK imports plus import/alias-proven native and LangChain wrapper calls. Rebinding
  withholds call attribution. Exact AutoGen model-client imports identify OpenAI, Azure OpenAI, and
  Anthropic unless the OpenAI-compatible client overrides `base_url`; constructor names alone do
  not qualify. The official OpenAI, Anthropic, Google, xAI, Mistral, Groq, and Cohere
  TypeScript AI SDK providers also support selected exact named/dynamic imports, top-level CommonJS
  destructuring, factories, and immutable or inline configured instances; custom factory endpoints,
  unknown/spread configs, rebound destructured aliases, generic compatible packages, and community
  Ollama providers are not conflated. Native OpenAI,
  Anthropic, and Google GenAI TypeScript SDK constructors are supported through exact
  ESM default/named imports when their endpoint configuration is statically default; unknown/spread
  configs and custom endpoints remain unresolved. General CommonJS remains unresolved; the supported
  forms are an immutable direct module-level `const` require of the OpenAI or Anthropic package
  default constructor, plus exact top-level direct or aliased `GoogleGenAI` destructuring. Immutable native
  instances expose exact OpenAI chat/response, Anthropic message, and Google content-generation
  model calls only when the direct request object contains a literal `model`, a proven immutable
  module literal/template binding, or an exact immutable module-level literal object-map property
  such as `MODEL_IDS.chat`. Exact imported
  type annotations can carry provider identity through unique non-exported same-file helpers when
  every direct call site agrees; other require shapes, exported/ambiguous helper graphs, and
  instance/method flows remain unresolved.
  AgentScope's exact public model reexports and direct PydanticAI provider/model/embedding modules
  are supported. Selected local package reexport chains of these exact provider-wrapper symbols are
  also supported when every hop imports a known symbol/proven alias and does not rebind the exported
  alias. Star imports from proven local reexport modules are supported when the provider name is
  visible through literal `__all__` or the normal non-underscore wildcard rule. Simple imported local
  wrapper factories are supported when they have one return path to a proven provider-wrapper
  constructor and map a literal or parameter model source; the same factory summaries survive direct
  local reexport chains and star imports when visible through literal `__all__` or the normal
  non-underscore wildcard rule. Rebound aliases, ambiguous factories, shadowed constructors, and
  generic same-named classes remain unresolved.
  Literal call-model arguments inherit the proven provider, and selected Mistral-owned prefixes are
  recognized; third-party model names hosted by Groq or Ollama and indirect factories remain
  unresolved.
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
- Python imported literal-origin proof requires an exact named import from one selected module and a
  single immutable top-level HTTP(S) string literal. Import aliases and f-string/local-prefix
  propagation are supported. Environment or composed values, source duplication or `global`
  mutation, consumer rebinding, function-local shadowing, wildcard/reexport forms, ambiguous imports,
  and module-qualified access remain unresolved.
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
  exact named imports or one exact local module-qualified constructor, direct constructor calls or
  immutable constructor-only `self` fields, and four iterations. Reexports, inheritance, local
  constructor variables, ambiguous module aliases, multiple entrypoints, mutable/dynamic fields, and
  arbitrary class methods remain unresolved.
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
  Statement-ordered local alias chains are supported while every hop copies an already proven
  compatible filesystem callable in the same function. Aliases assigned before their source is
  proven, rebound alias targets, incompatible operation families, and imported wrapper helpers
  remain unresolved. `Path.rename`/`replace`
  require explicit or immutable receiver proof; conditional, reassigned, union-typed, and helper-
  returned receivers remain unresolved rather than matching string/container methods by name.
  Arbitrary attribute `.open()` calls are deliberately excluded unless the receiver is proven to be
  a `pathlib.Path`; configured or fixed write paths remain inventory but do not raise AV-FS001.
- Browser-page evaluation inventories 93 import-context calls and proves 71 receivers: two exact
  Playwright-annotated SWE-agent parameters, five Skyvern calls reached from an exact imported page
  factory, 15 exact class-attribute annotations across CAMEL, LaVague, and MetaGPT, and 13 Devika
  calls through an exact constructor-bound page field or immutable local alias. One further Skyvern
  call is a known Playwright Locator derivation rooted in the imported page factory. Schema v89 adds
  one exact Playwright-returning property in OpenAI Agents Python and three straight-line local page
  uses in Aider and Skyvern. Schema v90 additionally proves Browser-Use's uniquely annotated module
  page and same-branch derived Locator under a fail-closed Playwright import guard. These original
  `.evaluate(...)` observations remain 41 proven of 86. Schema v91 adds structural support for
  `evaluate_handle(...)`, `eval_on_selector(...)`, `eval_on_selector_all(...)`, and Locator
  `evaluate_all(...)`; the expression is selected from each API's positional script slot or exact
  `expression=` keyword, so a dynamic selector paired with a fixed script is not dynamic JavaScript.
  Seven newly inventoried Skyvern test calls add three locally constructed-page proofs and four
  unresolved receivers, for an API split of 86 `evaluate`, five `eval_on_selector`, and two
  `eval_on_selector_all` calls. The selected production file containing another alternate evaluator
  lacks local Playwright provenance and is deliberately excluded. Schema v92 proves four more
  Skyvern test calls through two unique local `@contextlib.asynccontextmanager` helpers. Each helper
  must contain one exact Playwright runtime→browser→context→page chain and exactly one unconditional
  page yield; the caller must bind that helper directly in a top-level `async with` and leave the
  target immutable. Schema v93 proves two MetaGPT production calls by resolving an exact
  `Literal["chromium", "firefox", "webkit"]` selector through
  `getattr(playwright_runtime, self.browser_type)`, then requiring unanimous private same-class
  helper call sites. Direct calls and one immutable bound-method alias are accepted; mixed calls,
  escaped or rebound aliases, and wider literal sets are withheld. Schema v94 additionally proves
  three Devika production calls through a one-shot lifecycle field: `None` in `__init__`, followed
  by one straight-line async Playwright runtime→browser→page assignment method. Conditional flow,
  reassignment, decorated initializers, and shadowed factories are withheld. Schema v95 additionally
  resolves three Skyvern test helper-body evaluations when a private
  top-level function's selected-module call sites unanimously pass an exact local context-manager
  page. Mixed calls, escaped helpers, lambda-hidden calls, and caller-local helper or factory
  shadowing withhold the proof.
  Schema v96 proves 12 CAMEL production evaluations through a field-wide branching lifecycle: one
  exact locally imported Playwright runtime must reach every page assignment through browser or
  context construction, existing context pages, or an exact popup event result. Unknown, tuple, or
  dynamic `setattr` writes, other event names, and shadowed factories withhold the proof.
  Schema v97 proves one Skyvern production evaluation through its exact imported-page wrapper scope.
  The page must come from the pinned `get_page` factory, built-in `getattr` must be unshadowed, and
  the expression must select `_locator_scope` with a `None` default or fall back through `.page` to
  the same page. The annotated assignment must dominate the derived Locator evaluator. Wrong
  attributes or defaults, a shadowed `getattr`, and cross-branch use withhold the proof.
  Schema v98 proves one further Skyvern production evaluation through an imported context field.
  The defining selected file must contain one top-level class with one exact Playwright field
  annotation; the consumer must uniquely resolve an unrebound import of that class, use it as the
  exact annotation of an immutable parameter, and copy the field into one immutable local. Ordinary
  or duplicate field annotations, near or rebound imports, and parameter or alias reassignment
  withhold the proof.
  Schema v99 proves one further Skyvern production evaluation through an imported protocol method
  returning `Page | None`. The defining selected file must expose one unique, undecorated method
  with an exact Playwright receiver return annotation; the consumer must uniquely import the class,
  annotate an immutable context, call the method in the matching sync/async mode, and bind one
  dominating immutable alias. A nested closure may capture that context only when it is neither
  shadowed nor declared `nonlocal`. Ordinary, duplicate, decorated, rebound, mode-mismatched,
  branch-only, shadowed, and nonlocal-mutated forms withhold the proof.
  Class or `__init__` annotations may use an exact immutable Playwright import under `TYPE_CHECKING`.
  Constructor flow requires a straight-line exact Playwright runtime→browser/context→page chain and
  one field mutation. Conflicting/wrong annotations, near or rebound imports, static methods, and
  conditional, repeated, late, or shadowed-factory fields are withheld. Six chained calls formerly
  missed by the dotted-name gate are now inventoried; five remain unresolved. Across all supported
  APIs, 22 fixed-script observations retain unresolved receiver state. Dynamic promotion also
  supports one immutable alias of a typed parameter and known locator/get-by/filter/nth/and/or/
  first/last derivations;
  untyped/inherited fields, other ambiguous wrapper locators, sanitizers,
  structured JavaScript builders, helper-return and non-unanimous helper-parameter flow, mutable lifecycle fields,
  and unsupported evaluator APIs remain unresolved.
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
  import closure, all charged against the same cap. This refresh added 202 files across 25 repositories. Unselected definitions
  and controls are not evidence of repository-wide coverage or absence.

## Quality interpretation

The 719-label rule truth set and 1,803-label IR component/relationship set are curated regression
suites. They guard known positives and negatives; they are not an unbiased accuracy estimate. A
future holdout must be sampled separately across the categories above, externally reviewed, and kept
sealed while rules change. Until then, precision/recall values apply only to the published seed
labels.

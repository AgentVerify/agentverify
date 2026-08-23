# Recurring agent-system patterns

## Model → orchestrator → tool router → privileged executor

The dominant architecture separates reasoning from action. A model proposes a call, an agent loop or
graph routes it, and a tool crosses a trust boundary into the filesystem, shell, browser, network,
database, or third-party API. Verification must link all four layers; a model import alone is not an
agent architecture.

## Multi-agent delegation

Frameworks express delegation as graph edges, handoffs, group chat, role-based crews, or agents
wrapped as tools. Delegation can expand effective permissions: a low-privilege coordinator may invoke
a specialist with shell or browser access. The IR should compute transitive capabilities.

In TypeScript, the wrapper itself may be inline (`worker.asTool(...)`) or assigned before it appears
in an Agent's tools array. Both forms need to resolve back to the agent identity; treating the adapter
as an unrelated tool hides transitive authority.

## MCP client/server indirection

MCP moves tool definitions and execution outside the application process. Clients can discover tools
dynamically and forward model-generated argument maps. Servers may expose narrow domain actions or
broad primitives such as command execution and writable roots. Verification needs client config,
server capability manifests, transport, authentication, and approval context. Framework adapters
also commonly bind one discovered tool source per wrapper instance; this removes a direct
call-parameter selector but does not prove the source object immutable. It is weaker than an
authorization allowlist and must remain a distinct control effect.

Captured names require escape analysis. A callback returned from a wrapper factory or installed in a
tool/action registry binds a source across later invocations; a retry closure created and consumed
inside one public call does not narrow the caller's authority. Lexical nesting is not a control by
itself.

Internal dispatch also crosses methods. A caller can inherit routing evidence from a same-class
callee only when parameter mapping, registry lookup, and a rejecting missing-value branch in the
same statement block are all resolved. A return that computes a fallback does not qualify. Earlier
returns require a simple boolean branch and a call-site literal that selects the path beyond it; the
required literal remains visible on the relationship. Delegation to an unavailable manager body
remains unknown; `ToolManager` naming alone is not a control.

Cross-file routing proof requires more than a manager-shaped attribute. The selected dependency must
export a class whose method has the same rejecting registry pattern, and the consumer must bind that
imported constructor once in `__init__` without rebinding either the attribute or constructor name.
This resolves the MCP Python SDK path while keeping mutable and fallback managers unknown.

MCP stdio configuration is also a package-install boundary. `uvx` and `npx -y` can resolve and run a
server package at startup, so a missing version or floating tag makes future executions depend on
mutable registry state. Exact package pins narrow that state but do not prove artifact integrity,
transitive dependency stability, publisher identity, or server capability safety. Analysis should
keep package resolution separate from tool authorization and runtime containment. The same boundary
appears in Python constructors, JSON configuration, and TypeScript SDK transports or literal
`mcpServers` objects. A launcher dependency such as `tsx` may execute local server source, so the
fact should identify the mutable package selected by the launcher without claiming it implements the
server.

## Local versus isolated execution

Code and shell tools run directly, in local containers, or in remote sandboxes. “Sandbox present” is
not binary evidence of safety: mounts, network access, credentials, host sockets, and workspace scope
determine containment quality.

## Tool-controlled network destinations

Agent tools often accept search terms, resource identifiers, or complete URLs. A fixed origin with a
dynamic query is materially different from allowing the tool parameter to choose the scheme and
host. Destination analysis must preserve that distinction and eventually combine hostname policy,
DNS resolution, redirects, proxies, and runtime egress controls.

Axios instances add two separate questions: whether a relative request is locked to a fixed
`baseURL`, and whether absolute URLs may override that origin. Transport-bound filtering agents can
validate direct IPs and connection-time DNS results, but environment proxy routing may move that
validation boundary to the proxy connection. The IR must preserve `allowAbsoluteUrls`, agent
override ordering, configured IP/CIDR exceptions, and proxy dependence instead of flattening the
client to “safe” or “unsafe.”

Conditional package exports can change the security contract by runtime. A Node implementation may
validate DNS and pin an Undici dispatcher while an edge implementation either fails closed or falls
back to raw fetch. Analysis must resolve the exact imported export and runtime branch; the existence
of a strong Node helper cannot govern an intentionally unguarded edge fallback.

Schema-driven file hydration is also a network boundary. A tool executor may recursively inspect an
argument object, identify `file_uploadable` values, and fetch URL strings before invoking the remote
tool. That preprocessing is part of the tool's effective network authority even when the tool's own
API call uses a fixed origin.

Generated API tools require field-sensitive origin reasoning. An OpenAPI tool can legitimately let
the model choose path, query, header, and body values while retaining a deployment-controlled server
origin. That conclusion depends on segment encoding, dot-segment rejection, server-variable source,
and credential URL behavior; the presence of a variable named `url` at the final fetch is not enough
to call the origin model-controlled.

## A2A card → negotiated RPC endpoint

Remote-agent configuration often names an AgentCard location, not the final RPC origin. The card can
advertise one or more transport endpoints, and an SDK client factory negotiates among them. A secure
composition therefore binds every network-supplied endpoint to the card source origin and an allowed
scheme before client construction. A deployment-controlled card URL is not model-controlled SSRF,
but an unconstrained remotely supplied card is still a distinct downstream-origin authority.

## Approval gates and bypasses

Approval may apply per tool, per argument pattern, per session, or only to destructive operations.
Auto-approve lists and skip-confirmation modes can silently widen authority. Analysis must represent
gate scope and the configuration that bypasses it.

Approval callbacks are another policy layer. A literal `needs_approval` setting can coexist with a
handler that automatically returns approval under an environment flag. A demonstrated bypass
requires the callback binding, same-file call chain, enabled-value comparison, privileged tool, and
Agent reachability; merely finding an auto-approval helper elsewhere in the file is insufficient.

SDK defaults are part of that policy surface. In an MCP bridge, an omitted server-level approval
argument may be normalized once and copied into every dynamically discovered tool wrapper. The
agent→server binding, default normalization, per-name fallback, and final wrapper assignment must all
be proven before reporting the effective default; absence alone is not a destructive-path finding.
When a local MCP package has a known write surface, the effective default becomes actionable only
after proving Agent reachability and excluding a literal read-only tool allowlist. Dynamic filters
remain unresolved rather than being credited as mutation controls.
Frameworks can express the same decision as a positive confirmation list instead of an approval
boolean. A sound analysis compares a literal list against the known mutating server surface:
omission and incomplete static coverage are actionable, complete coverage is a proven control, and
dynamic policy expressions remain unresolved. Read-only tool inclusion is an independent
counterproof and must not be inferred from a suggestive variable name.

MCP approval is bidirectional. Tool approval governs client requests sent to a server, while sampling
approval governs a server request that spends the client's model authority and returns the result.
For sampling, the relevant evidence is callback registration, default denial, callback precedence,
the server-controlled prompt and sampling fields, the actual model call, and the response channel.
A shared word such as `auto_approve` is not enough to explain that trust boundary, and generic and
protocol-specific findings should not be emitted for the same setting.
At the raw protocol layer, registering a sampling callback is itself a capability grant. Returning a
well-formed sampling result without an intervening decision is automatic fulfilment whether the
example currently uses a canned response or a provider—the same handler seam is where production
hosts attach the model. A consent control must expose the request and fail closed on rejection;
logging a preview is not approval. Token capping is an independent spend control and does not replace
the decision.
Elicitation is a third, distinct server-to-client authority. An `accept` result is not a generic
success value: it asserts that a user approved a form response or URL interaction. Canned content,
completion notifications, schema validation, and a safe-looking URL do not establish that decision.
A governing client path must present the request, collect or confirm the user's response, preserve
decline/cancel outcomes, and—in URL mode—apply destination controls before navigation. Analyses must
therefore attach consent to each accepting branch rather than infer it from comments or handler names.
Framework adapters can hide that authority transition. PydanticAI turns a configured sampling model
into an SDK-generated callback, while FastMCP turns ordinary elicitation-handler data into protocol
`accept`. Analysis must model those adapter contracts explicitly, preserve SDK/session compatibility
and disclosure gaps, and reject rebound constructors, callbacks, or response factories rather than
equating a friendly framework API with consent.
Consent and disclosure are separate controls for URL elicitation. A yes/no prompt can prove the
decision while still hiding a server-controlled phishing destination. Full-URL display must be
proven at the user interface before acceptance; URL validation and secure browser opening are further
independent controls.

Risk analysis is also separate from action gating. A framework may classify a tool call as low,
medium, high, or unknown without stopping execution. OpenHands makes the dependency explicit:
confirmation mode requires both an analyzer and a non-default confirmation policy. Static analysis
should therefore model analyzer and gate as separate controls and credit human approval only when
the same reachable conversation composes both.

Optional containment is also separate from effective containment. Trae Agent includes a Docker tool
executor, but its public constructors default `docker_config` to `None` and select the local executor
on that path. A scanner should record Docker isolation as available while attaching the disabled
default to the exact Bash/editor capabilities; the mere presence of a sandbox implementation must
not govern an execution path that does not select it.

## Provider presence versus configured provider calls

An SDK import proves a repository dependency, while an import-proven constructor or inference call
proves configured use at a specific source location. Aliases preserve that identity until rebinding;
generic `Client` names do not. Literal model arguments can inherit the proven call's provider, but
hosted third-party identifiers must not be treated as provider-owned model families. This distinction
is especially important for Groq and Ollama, which commonly serve models developed elsewhere.
In TypeScript, exact dynamic `import()` destructuring can preserve the same proof as a static named
import, while a provider instance created by an official factory remains attributable only while its
local binding is immutable and unshadowed.
Framework public APIs can provide equivalent proof when the module and exported constructor are
both exact. Positional arguments need signature-level treatment: a model wrapper's first string may
be a model ID, while a provider constructor's first string may instead be a credential or endpoint.
A public module can reexport constructors for several providers, so provider identity belongs to the
exact `(module, exported symbol)` pair rather than the module alone. This also keeps module aliases
precise without trusting unrelated exports from the same package.

## Observability as a cross-cutting control

Tracing and audit hooks appear at framework, model-client, runtime, and tool layers. A useful rule asks
whether consequential actions receive durable, attributable records—not merely whether a logging
package is imported.

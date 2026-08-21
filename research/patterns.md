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

## Observability as a cross-cutting control

Tracing and audit hooks appear at framework, model-client, runtime, and tool layers. A useful rule asks
whether consequential actions receive durable, attributable records—not merely whether a logging
package is imported.

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

## Local versus isolated execution

Code and shell tools run directly, in local containers, or in remote sandboxes. “Sandbox present” is
not binary evidence of safety: mounts, network access, credentials, host sockets, and workspace scope
determine containment quality.

## Tool-controlled network destinations

Agent tools often accept search terms, resource identifiers, or complete URLs. A fixed origin with a
dynamic query is materially different from allowing the tool parameter to choose the scheme and
host. Destination analysis must preserve that distinction and eventually combine hostname policy,
DNS resolution, redirects, proxies, and runtime egress controls.

## Approval gates and bypasses

Approval may apply per tool, per argument pattern, per session, or only to destructive operations.
Auto-approve lists and skip-confirmation modes can silently widen authority. Analysis must represent
gate scope and the configuration that bypasses it.

## Observability as a cross-cutting control

Tracing and audit hooks appear at framework, model-client, runtime, and tool layers. A useful rule asks
whether consequential actions receive durable, attributable records—not merely whether a logging
package is imported.

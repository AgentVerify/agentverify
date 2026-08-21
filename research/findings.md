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

## 2. MCP creates a cross-process trust boundary

MCP signals occur in 50 repositories. Seventeen contain generic tool-call forwarding shapes, and 17
MCP-positive repositories had no allowlist term in the bounded sample. The latter number is a triage
queue, not proof that allowlist enforcement is missing.

Representative forwarding shapes occur in
[Goose](https://github.com/block/goose), [CrewAI](https://github.com/crewAIInc/crewAI),
[Semantic Kernel](https://github.com/microsoft/semantic-kernel), and
[AutoGPT](https://github.com/Significant-Gravitas/AutoGPT). AgentVerify should resolve the configured
server, discovered tool set, transport, authentication, argument flow, and enclosing approval policy.

The structure-aware engine retains every selected dynamic forwarding capability and reports 43 for
review. One MCP Python SDK path is now proven to be governed by an internal tool registry: two
uncaught mapping lookups occur before forwarding, so unknown names terminate before the call. This
routing fact is represented as an Agent IR edge but does not suppress the review, because the registry
contains server-advertised tools rather than an explicit authorization policy. Caller-owned mappings
and post-call lookups remain unresolved.

Five additional calls across CrewAI, Lagent, AgentScope, and Trae bind the forwarded name once in a
wrapper constructor. The engine records exact `fixed-tool-binding` edges—including pure property and
getter accessors—but retains all five reviews because per-instance routing is not an authorization
allowlist and does not constrain the argument map. A mutable local regression prevents class-wide
name matching from inventing this control.

Five more calls bind a tool source through an escaping callback: three browser-use actions are
registered and two ArcadeAI wrappers are returned. Equivalent retry closures in the MCP Python SDK
and FastMCP do not qualify because the public caller still selects the name for each operation.
Schema v13 therefore reports five instance and five closure fixed-binding edges, without suppressing
any review.

FastMCP adds an interprocedural routing fact: its middleware recursion reaches a same-class callee
that resolves `get_tool(name)`, rejects a missing tool, and only then executes. The literal
`run_middleware=False` call argument proves that the earlier recursive return is bypassed and is
retained as a required edge argument. This becomes the second `tool-registry` edge. A default-tool
fallback and the selected MCP Python SDK file whose manager body is absent remain unresolved,
demonstrating why semantic names are not enforcement evidence.

## 3. Approval exists, but bypass behavior recurs

Human-approval vocabulary appears in 52 repositories, while auto-approval or skip-confirmation
vocabulary appears in 18. Some matches are deliberately safe tests or demonstrations; others are
production configuration. A useful analyzer must model approval scope and bypass paths rather than
only checking whether an approval API exists.

The structure-aware engine reports 15 default-scope approval-bypass reviews. Eight are explicit
environment-enabled approval short circuits in pinned OpenAI Agents Python/JavaScript examples; the
remaining seven are enabled configuration candidates found previously. Examples are not treated as
vulnerabilities, but they prove that deployment-time approval overrides recur in real agent code and
need auditable policy. Status flags and branches with an additional safety condition are regression
negatives.

## 4. Provider identity is a governance dependency

OpenAI signals appear in 51 repositories, Anthropic in 37, Google in 28, Azure OpenAI in 18, and AWS
Bedrock in 14. Forty-four repositories contain two or more provider signals. An AI bill of
materials should report providers and model configuration even when no security issue is present.

## 5. Controls are layered

Sandboxing vocabulary appears in 64 repositories, audit/tracing in 57, human approval in 52, and
allowlisting in 39. These controls live in infrastructure, framework middleware, configuration, or
individual tool wrappers. The Agent IR must preserve which control governs which action instead of
producing repository-wide flags. One pinned MCP Servers write now demonstrates why exact control
edges matter: its imported validator normalizes candidate and root paths, rejects separator-aware
boundary failures before `mkdir`, and is represented as a `path-boundary` control rather than a
repository-wide “filesystem safe” flag. Its configured root scope remains unresolved, so the review
is retained rather than treating the presence of validation as sufficient policy.

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
corpus. Exact relationship locations safely resolve 295 capability/control endpoints. Reused Python
and TypeScript bindings were a second identity failure: one file-level ID could describe many
constructor occurrences. Occurrence-qualified IDs resolve all 688 source agent/tool ambiguities, and
141 unsafe target IDs become unresolved instead of pointing at multiple assets. Intermediate
benchmark schema v5 recorded all 289 target references whose duplicated raw binding ID was withheld.
Schema v6 resolves only single direct definitions that appear earlier in the same Python lexical or
module scope: 325 same-scope and 14 module-scope edges. The final export has 30 ambiguous endpoints,
all tool targets, and 500 unresolved endpoints. A governance export that collapses those references
by name would silently attach controls or risks to the wrong asset.

## 8. Dynamic network origin is rarer but high impact

Five default-scope tool paths in the bounded corpus pass a tool parameter directly or through a
same-file helper to an HTTP origin: [Goose's Wikipedia MCP tool](https://github.com/block/goose/blob/48d480f91163bbcdc0f69f01befa3841a93a1d3e/examples/mcp-wiki/src/mcp_wiki/server.py#L29)
and [AgentOps' smolagents webpage tool](https://github.com/AgentOps-AI/agentops/blob/f8e907b92dabe47232978023fdcb01e2a7d4b752/examples/smolagents/multi_smolagents_system.py#L73),
the MCP TypeScript SDK's [registered `fetch-data` tool](https://github.com/modelcontextprotocol/typescript-sdk/blob/3924de99df834302d89f5997a1b64ca268282284/packages/server/src/server/mcp.examples.ts#L130-L138),
Mastra's [helper-backed `httpRequest` tool](https://github.com/mastra-ai/mastra/blob/1da5fb00e141b78c2148b21ee085ec24112cf2a5/packages/agent-builder/src/defaults.ts#L1045),
and MCP Servers' [helper-backed gzip resource fetch](https://github.com/modelcontextprotocol/servers/blob/599dafc1054550a6eeb87a6545c1e1b03b3ca827/src/everything/tools/gzip-file-as-resource.ts#L85).
The first four accept arbitrary HTTP destinations; Goose checks the scheme but does not constrain the
host. MCP Servers has an optional environment-configured hostname allowlist, but its empty default
permits arbitrary HTTP/HTTPS origins; size and timeout limits constrain impact rather than
destination. A
[fixed Devpost origin with a dynamic search query](https://github.com/microsoft/ai-agents-for-beginners/blob/01777b05e8afeba6bf5a6dbe74cc2293372d3693/11-agentic-protocols/code_samples/github-mcp/app.py#L118)
and the SDK's [fixed weather host with a dynamic query](https://github.com/modelcontextprotocol/typescript-sdk/blob/3924de99df834302d89f5997a1b64ca268282284/examples/guides/get-started/firstServer.examples.ts#L20-L40)
are real negatives. This small but high-impact set supports a narrow review rule, not a claim that
every variable URL is SSRF.

## Limitations

- The collector is presence-based and scans a bounded subset of files.
- Generic words such as approval, trace, and sandbox can produce contextual false positives.
- Framework repositories contain tests and examples that are not enabled by default.
- Data flow and configuration resolution are required before absence or reachability claims.
- Every promoted detection needs a hand-reviewed real case and regression fixture.

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

Filesystem mutation is broader than `open()` and `write_text()`. Schema v31 resolves 448 Python
filesystem mutations in selected files: 179 creates, 190 deletes, 46 copies, and 33 moves. The move
inventory includes 20 `Path.rename`/`Path.replace` calls proven through explicit constructors or
immutable Path-derived bindings, including ChatDev's
[`source_path.rename(target_path)`](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/server/services/workflow_storage.py#L137).
Exact tool reachability narrows this inventory to 30 filesystem reviews across ten repositories:
26 generic AV-FS001 sites across nine repositories and four specialized AV-FS002 sites in CrewAI
Examples. Newly exposed cases include ArcadeAI's
[`os.replace`/`shutil.move` destination branches](https://github.com/ArcadeAI/arcade-ai/blob/597debaa1593b54172061ce36a414cc29aa8fc6a/examples/mcp_servers/local_filesystem/src/local_filesystem/tools.py#L287-L301)
and its [conditional `copy`/`copy2` callable](https://github.com/ArcadeAI/arcade-ai/blob/597debaa1593b54172061ce36a414cc29aa8fc6a/examples/mcp_servers/local_filesystem/src/local_filesystem/tools.py#L329-L331),
and CrewAI Examples'
[`copytree` destination](https://github.com/crewAIInc/crewAI-examples/blob/da94a91e691e1cf5b3151416bb15b5b62729bea8/crews/landing_page_generator/src/landing_page_generator/tools/template_tools.py#L86-L90).
That copy and three sibling sinks rely on `str(resolved).startswith(str(root))`; schema v31 preserves
the checks as weak, non-suppressing control edges because string prefixes do not enforce path-component
boundaries. AV-FS002 takes precedence at those sinks and recommends `Path.is_relative_to`,
`Path.relative_to`, or `os.path.commonpath`.
The additional review comes from Skyvern's post-definition FastMCP registration. Exact relative
import resolution links `skyvern_state_save` to its body and exposes
[`resolved.parent.mkdir(...)`](https://github.com/Skyvern-AI/skyvern/blob/486c8975e9864a53037d4701b781f8619e698c40/skyvern/cli/mcp_tools/state.py#L89).
Its validator admits a candidate equal to an allowed root, so the parent operation lacks a proven
descendant boundary. Across Skyvern, 115 recovered registrations—including 22 through structurally
proven transparent wrappers—yield only 21 capability edges and
this one additional filesystem review.
The IR records the destination—not the source—as the governed path for two-path APIs. Import aliases
are resolved only when unshadowed; string `.replace()` calls and caller-shadowed `shutil` names are
regression negatives.

Browser-page evaluation is a separate execution boundary. Schema v31 inventories 80
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
Schema v31 therefore reports five instance and five closure fixed-binding edges, without suppressing
any review.

FastMCP adds an interprocedural routing fact: its middleware recursion reaches a same-class callee
that resolves `get_tool(name)`, rejects a missing tool, and only then executes. The literal
`run_middleware=False` call argument proves that the earlier recursive return is bypassed and is
retained as a required edge argument. This becomes the second `tool-registry` edge. A default-tool
fallback remains unresolved, demonstrating why semantic names are not enforcement evidence.

The collector's bounded dependency closure adds 135 local Python imports across 11 repositories. It
exposes the MCP Python SDK's `ToolManager` reexport and implementation: `MCPServer` binds one imported
manager in its constructor, and that manager resolves `get_tool(name)` and rejects a miss before
execution. This is the third routing-only `tool-registry` edge. Mutable manager fields, fallback
managers, and rebound constructor imports are regression negatives. The same dependency refresh
exposes six OpenAI Agents SDK forwarding reviews and CAMEL's parameter-fed `exec` helper; both new
rule observations are pinned in the 299-label truth set.

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
ChatDev contributes the Python exception form: its local-tool creation route resolves a candidate,
calls [`target_path.relative_to(tools_dir)`](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/server/routes/tools.py#L58),
and terminates the `ValueError` handler before writing. Schema v31 records this as a distinct
`Path.relative_to` control edge with unresolved root scope; handlers that continue are not controls.
OpenAI Agents Python demonstrates the interprocedural variant: its `_resolve()` helper returns the
same checked Path to create, update, and delete callers. Three sink edges retain the helper's exact
check location and `same-class-return` provenance. The configured root remains unresolved, and
duplicate/rebound helpers or changed returns do not qualify.

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
corpus. The current schema resolves 410 endpoints by exact relationship evidence. Reused Python
and TypeScript bindings were a second identity failure: one file-level ID could describe many
constructor occurrences. Occurrence-qualified IDs resolve all 688 source agent/tool ambiguities, and
141 unsafe target IDs become unresolved instead of pointing at multiple assets. Intermediate
benchmark schema v5 recorded all 289 target references whose duplicated raw binding ID was withheld.
Schema v31 resolves only single direct definitions that appear earlier in the same Python lexical or
module scope: 325 same-scope and 14 module-scope edges. The final export resolves 1,927 endpoints by
symbol ID and 17 by unique display name; 30 remain ambiguous, all tool targets, and 500 unresolved.
A governance export that collapses those references
by name would silently attach controls or risks to the wrong asset.

## 8. Dynamic network origin is rarer but high impact

Thirteen default-scope tool paths in the bounded corpus pass a tool parameter directly or through a
resolved function/class helper to an HTTP origin: [Goose's Wikipedia MCP tool](https://github.com/block/goose/blob/48d480f91163bbcdc0f69f01befa3841a93a1d3e/examples/mcp-wiki/src/mcp_wiki/server.py#L29)
and [AgentOps' smolagents webpage tool](https://github.com/AgentOps-AI/agentops/blob/f8e907b92dabe47232978023fdcb01e2a7d4b752/examples/smolagents/multi_smolagents_system.py#L73),
the MCP TypeScript SDK's [registered `fetch-data` tool](https://github.com/modelcontextprotocol/typescript-sdk/blob/3924de99df834302d89f5997a1b64ca268282284/packages/server/src/server/mcp.examples.ts#L130-L138),
Mastra's [helper-backed `httpRequest` tool](https://github.com/mastra-ai/mastra/blob/1da5fb00e141b78c2148b21ee085ec24112cf2a5/packages/agent-builder/src/defaults.ts#L1045),
MCP Servers' [helper-backed gzip resource fetch](https://github.com/modelcontextprotocol/servers/blob/599dafc1054550a6eeb87a6545c1e1b03b3ca827/src/everything/tools/gzip-file-as-resource.ts#L85),
two Qwen-Agent registry tools that fetch caller-selected remote image URLs, Qwen's registered
document parser calling an exact imported downloader, and smolagents' visualizer calling a
function-local self-imported image encoder. The last two imported helper summaries retain the helper
definition and HTTP sink lines on their call-site capability evidence.
Four additional Qwen paths propagate that proof through registered classes: three call
`SimpleDocParser` directly or through an immutable constructor field, while `Retrieval` reaches the
newly summarized `DocParser` on the second graph iteration. The class pass requires a unique
single-entrypoint tool and an exact imported constructor; fixed arguments remain inventory, and
mutation, `setattr`, shadowing, module-qualified calls, and rebound constructors are pinned negatives.
Schema v31 also inventories 22 exact `urllib.request.urlopen` calls. Two are reachable from Qwen's
registered weather tools. Both wrap a fixed `https://ali-weather.showapi.com` URL with dynamic query
data in `Request` objects, so preserving the constructor's original URL produces exact inventory
edges without adding reviews. Module or named aliases are import-proven; local shadowing and rebound
openers are withheld.
Schema v31 separately models fail-closed Python scheme and hostname checks as
`network-origin-allowlist` controls on the exact request. The proof requires an import-proven
`urlparse`/`urlsplit`, immutable URL and parse-result bindings, static nonempty allowlists, and checks
that terminate before the sink. It records explicit redirect disabling while leaving DNS scope and
all other redirect behavior unresolved. None of the 13 corpus review paths carries this exact
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

## Limitations

- The collector is presence-based and scans a bounded subset of files.
- Generic words such as approval, trace, and sandbox can produce contextual false positives.
- Framework repositories contain tests and examples that are not enabled by default.
- Data flow and configuration resolution are required before absence or reachability claims.
- Every promoted detection needs a hand-reviewed real case and regression fixture.

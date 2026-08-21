# Detection validation log

Validation date: 2026-08-21. Repositories are partial checkouts pinned by
`research/repository-data.json`; paths and results can be reproduced from the corpus scripts.

## AV-EXEC001 — dynamic command through system shell

| Repository | Commit | Selected files scanned | Findings | Representative path |
|---|---|---:|---:|---|
| Aider-AI/aider | `5dc9490b` | 152 | 4 | `aider/editor.py:134` |
| bytedance/trae-agent | `e839e559` | 75 | 2 | `trae_agent/agent/docker_manager.py:175` |
| FoundationAgents/MetaGPT | `11cdf466` | 214 | 1 | `metagpt/repo_parser.py:731` |
| SWE-agent/SWE-agent | `3ea751c0` | 102 | 1 | `tools/windowed/lib/flake8_utils.py:143` |
| cline/cline | `80b3b034` | 187 | 1 | `apps/examples/cli-agent/src/index.ts:19` |

These are pattern detections, not claims that each application is exploitable. Caller provenance,
input constraints, containment, and approval policy determine exploitability. The rule reports the
dangerous execution primitive with high pattern confidence and leaves reachability for graph analysis.

## Regression cases

- `cases/python_dangerous/agent.py`: positive dynamic string plus `shell=True`.
- `examples/safe_agent/agent.py`: negative fixed argv plus default `shell=False`.
- `cases/typescript_mcp`: MCP inventory and approval-bypass candidate.
- `cases/typescript_approved`: literal TypeScript tool approval resolves a governing control, while
  callback and disabled forms remain unresolved.
- `cases/builtin_tool_approval`: OpenAI Agents Python built-in tool instances preserve enabled,
  disabled, callback, and auto-handler approval policies without leaking controls between same-named
  tools.
- `cases/typescript_structured_tools`: balanced tool-array parsing, namespace spreads, inline and
  assigned SDK tools, agent-as-tool delegation, approval policies, and unrelated-name negatives.
- `cases/typescript_bun_shell`: Cline inline tools distinguish dynamic Bun `sh -c`, a fixed command,
  direct argv execution, and string-only near misses.
- `cases/typescript_tool_registrations`: import-aware Mastra factory properties and MCP registrations
  retain exact callback-to-capability tool identities, with string and ordinary-registry negatives.
- `cases/typescript_helper_summary`: unique same-file network helpers propagate exact tool edges while
  fixed-host flows and `fetch(...)` text inside JavaScript regex literals remain negatives.
- `cases/mcp_forwarder`: statement-ordered allowlists, internal registries, constructor-only and
  returned closure bindings, plus mutable/rebound negatives remain distinct.
- `cases/mcp_imported_manager`: package reexports and immutable constructor bindings resolve an
  imported registry guard; mutable fields, fallback managers, and rebound imports remain negative.

## Full-corpus engine benchmark

The 2026-08-21 default scan covered 70 source-bearing repositories plus one docs-only upstream
snapshot. It parsed 10,729 selected Python/TypeScript/JavaScript files plus 155 configuration files,
resolved 1,379 relationships, and completed in 74.03 seconds on the development machine. Three parse
warnings were isolated and reported without aborting the run. Tests and fixtures are inventoried but excluded from findings by
default; `--include-tests` enables them. The pinned corpus contains no AgentVerify inline directives,
so the benchmark records zero suppressed findings.

The locked collector preserves the original 220-file root selection and adds at most 20 local Python
imports reached from MCP forwarding files. This refresh materialized 135 dependency files across 11
repositories; the engine scans all of them, while the collector's lexical-signal inventory retains
its independent 2 MB per-repository byte cap. Collector schema v2 records the dependency count per
repository; engine schema v15 carries both the 135-file total and the 11-repository coverage.

Engine benchmark schema v15 retains stable component-name taxonomies, category presence counts,
matched-versus-identified endpoint counts, TypeScript graph precision measures, and exact MCP
forwarding-control counts. It intentionally
excludes arbitrary agent/tool display names from the summary. The resulting
framework/provider/protocol/capability coverage and unsupported syntax are published in
`docs/frontend-coverage.md`; presence counts are discovery observations, not recall measurements.

The benchmark now also measures identity coverage: 8,566 agent/tool component observations carry
module-qualified IDs. Of 2,758 relationship endpoints, 1,875 carry symbol IDs and 1,873 resolve to an
observed component (1,622 Python and 251 TypeScript). Schema v15 records 325 same-scope and 14
module-scope targets resolved from a single direct definition that appears before the Agent
constructor. It also records 23 repeated-binding targets still withheld because the scope contains
multiple definitions. The two unmatched IDs are explicit Python re-export targets; capability,
control, and taxonomy endpoints intentionally remain evidence observations.

Schema-v15 benchmark output measures native AI BOM endpoint resolution separately. AI BOM 1.1
resolves 1,873 endpoints by symbol ID, 338 by exact evidence location, and 17 by a unique display
name; 30 remain ambiguous and 500 unresolved. Before evidence-local and occurrence-qualified
resolution, raw name matching left many endpoints ambiguous. Exact locations resolve additional
capability/control endpoints. Unique occurrence IDs resolve repeated source agent/tool observations
and mark unsafe targets explicitly unresolved. Conservative lexical resolution removes further target
ambiguities. All 30 remaining ambiguities are tool targets without a unique local definition, so the
resolver does not use a nearby source location to invent an identity.

The Python frontend resolves unambiguous absolute imports rooted at the repository, `src/`, or
`python/`, plus relative modules that map to exactly one sibling package file. It found five imported
agent-to-tool edges across two pinned repositories, including
CrewAI Examples' [markdown validator tool](https://github.com/crewAIInc/crewAI-examples/blob/da94a91e691e1cf5b3151416bb15b5b62729bea8/crews/markdown_validator/src/markdown_validator/crew.py#L3).
Two are newly resolved relative imports: the
[email flow draft tool](https://github.com/crewAIInc/crewAI-examples/blob/da94a91e691e1cf5b3151416bb15b5b62729bea8/flows/email_auto_responder_flow/src/email_auto_responder_flow/crews/email_filter_crew/email_filter_crew.py#L46)
and [CrewAI-LangGraph draft tool](https://github.com/crewAIInc/crewAI-examples/blob/da94a91e691e1cf5b3151416bb15b5b62729bea8/integrations/CrewAI-LangGraph/src/crew/agents.py#L44).
Missing files, path escapes, and duplicate absolute module names remain unresolved rather than
falling back to name-only inference.

Resolved agent/tool components and relationships now carry frontend-and-module-qualified symbol IDs.
The import truth labels verify both target paths and target IDs, including CrewAI-LangGraph's
`py:integrations/CrewAI-LangGraph/src/crew/tools.py#tool:CreateDraftTool.create_draft` class method.
The same-name collision fixture proves that the approved and dangerous `run_command` definitions do
not share reachability or control coverage.

The TypeScript frontend now reads only balanced top-level entries from literal Agent tool arrays. It
resolves OpenAI `tool`, `toolNamespace`, built-in tool factories, inline/assigned `asTool` adapters,
and Cline `createTool`. Import-aware discovery now also resolves generic/Mastra object-property
tools plus MCP `registerTool` names and callback spans. Schema v15 records 27 Mastra factory tools,
264 MCP registrations, 70 object-property tools (the factory/property categories overlap), and ten
exact registration-to-capability edges. Four of those edges come from bounded same-file network
helper summaries: three Mastra static methods and one MCP Servers free function. Schema v15 also
records one imported TypeScript path-boundary control edge. The full sample
contains 95 structure-backed agent edges: 14 delegations and 81 tool edges, all with targets that
resolve to observed components. The prior token heuristic could
turn words inside callbacks, string literals, and nested options into spurious tool edges. Relative
named imports still apply the conservative `.js`-specifier-to-source rule; this snapshot has no
qualifying cross-file Agent tool edge, so that part remains regression-validated only.

The approval-policy resolver attaches exact controls to inline OpenAI Agents JS tools, including the
pinned [local shell example](https://github.com/openai/openai-agents-js/blob/0b944370c6fe019ac5b08364ca013826cd7d0668/examples/tools/local-shell.ts#L104).
Literal true creates a control; false and the SDK default remain disabled, while callback results are
unresolved. Hosted container shell factories are identified separately and do not trigger the local
approval review.

For Python, files importing the OpenAI Agents SDK now inventory `ShellTool`, `ApplyPatchTool`, and
`CustomTool` instances with line-scoped identities. A literal `needs_approval=True` with no automatic
handler creates an exact tool-to-control edge; literal false and the SDK default are recorded as
disabled, while callbacks and a configured `on_approval` handler remain unresolved. The pinned SDK's
[shell HITL example](https://github.com/openai/openai-agents-python/blob/17ba331bb0ad1622a4ff4ecdc914c77118075dad/examples/tools/shell_human_in_the_loop.py#L117)
is the real positive: `ShellTool@117` is governed by the literal policy at line 119. Requiring an
`agents` import prevents unrelated application classes with the same constructor names from being
promoted into Agent IR.

## AV-APPROVAL001 — enabled approval-bypass path

The rule reports explicit enabled auto-approval/skip-confirmation settings and environment-backed
approval branches. Environment handling is deliberately flow-sensitive within a narrow boundary: an
approval-specific variable such as `SHELL_AUTO_APPROVE` must be compared with an explicit enabled
value, and the governed branch must return true directly without an intervening conditional. Python
tracks module flags into functions and keeps local flags lexically scoped. TypeScript supports inline
`process.env` comparisons and module-level flag assignments; comments and strings remain masked.

The full benchmark now reports 15 default-scope reviews. Eight newly resolved paths are official SDK
examples: OpenAI Agents Python's
[shell prompt bypass](https://github.com/openai/openai-agents-python/blob/17ba331bb0ad1622a4ff4ecdc914c77118075dad/examples/tools/shell.py#L80),
its [apply-patch approval short circuit](https://github.com/openai/openai-agents-python/blob/17ba331bb0ad1622a4ff4ecdc914c77118075dad/examples/tools/apply_patch.py#L83),
and OpenAI Agents JS examples for
[hosted MCP approval](https://github.com/openai/openai-agents-js/blob/0b944370c6fe019ac5b08364ca013826cd7d0668/examples/mcp/hosted-mcp-on-approval.ts#L6),
[computer use](https://github.com/openai/openai-agents-js/blob/0b944370c6fe019ac5b08364ca013826cd7d0668/examples/tools/computer-use-hitl.ts#L62),
[local shell](https://github.com/openai/openai-agents-js/blob/0b944370c6fe019ac5b08364ca013826cd7d0668/examples/tools/local-shell.ts#L73),
and [apply patch](https://github.com/openai/openai-agents-js/blob/0b944370c6fe019ac5b08364ca013826cd7d0668/examples/tools/apply-patch.ts#L77),
plus two sibling HITL examples using the same flag. These are intentional examples, not vulnerability
claims; `review` communicates that deployments should decide whether the bypass is acceptable.

Regression negatives reject status variables such as `AUTO_APPROVED_WARNING`, disabled values,
non-approval methods, and branches that add a second safety condition before returning. Same-class
Python attributes are resolved only when an approval-specific method has an unconditional early
return; inheritance, helper-object propagation, and callback results remain unresolved. The rule has
14 positive and 14 negative exact labels.

## AV-APPROVAL002 — reachable local shell with SDK approval disabled

The enabled rule is intentionally narrower than a general “missing approval” claim. It requires a
local OpenAI Agents Python `ShellTool` or TypeScript `shellTool`, a direct resolved Agent-to-tool edge,
and an explicit false or the SDK's documented false default. It reports a high-confidence `review`,
not a finding, because a custom executor may still implement an equivalent internal approval control.
Hosted shell environments, callback policies, automatic handlers, unresolved environments, and test
paths are excluded.

The full benchmark reports two sites, both in the pinned SDK's
[local shell skill example](https://github.com/openai/openai-agents-python/blob/17ba331bb0ad1622a4ff4ecdc914c77118075dad/examples/tools/local_shell_skill.py#L29).
The paired real negative is the
[HITL shell example](https://github.com/openai/openai-agents-python/blob/17ba331bb0ad1622a4ff4ecdc914c77118075dad/examples/tools/shell_human_in_the_loop.py#L117),
which creates a resolved human-approval edge. OpenAI Agents JS contributes real approved-local and
hosted-shell negatives. The rule has three positive and four negative exact labels.

During validation, import-aware shell resolution rejected Cline's `RegExp.exec()` calls as unrelated
to `child_process.exec()`. Structure-aware Cline `createTool` parsing then exposed the distinct real
path where agent input reaches
[`Bun.spawn(["sh", "-c", input.command])`](https://github.com/cline/cline/blob/80b3b0348e694bafc48e3dcd70154de3cf4289d9/apps/examples/cli-agent/src/index.ts#L19).
Truthy approval-bypass matching plus test-scope filtering reduced Cline approval candidates from 41
to five; those remain review results rather than confirmed vulnerabilities.

Expanding the truth set exposed two additional false-positive families. Literal TypeScript commands
were incorrectly classified as dynamic; resolving complete string literals removed five corpus
findings while preserving interpolated templates. Broad approval-name matching confused warning-state
and version-check flags with human approval; requiring approval-specific names removed six review
candidates. Corpus totals are now 21 `AV-EXEC001` findings and 15 `AV-APPROVAL001` reviews.
The dependency closure also exposes CAMEL's production `func_string_to_callable(code)` helper, whose
parameter reaches `exec`; it raises the `AV-EXEC002` total to 50 and is now pinned in the rule truth
set.

## AV-MCP002 — dynamic MCP forwarding

The rule requires an MCP import plus a non-literal tool name. A fixed tool name is the negative
regression. The full benchmark reports 49 default-scope forwarding sites across 23 repositories.
Hand-reviewed pinned examples include:

- [CrewAI client](https://github.com/crewAIInc/crewAI/blob/456c67d7c27923ed3c3dca202c6f56651d8e6063/lib/crewai/src/crewai/mcp/client.py#L599)
- [browser-use client](https://github.com/browser-use/browser-use/blob/85ddbfedf609166b2d2c76c3d80506649fee82a9/browser_use/mcp/client.py#L324)
- [Semantic Kernel connector](https://github.com/microsoft/semantic-kernel/blob/b39d95a34435f4c1d55dd00c86120ce118d847e1/python/semantic_kernel/connectors/mcp.py#L618)
- [ChatDev tool manager](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/runtime/node/agent/tool/tool_manager.py#L291)

These are legitimate protocol boundaries in framework code and are therefore `review` results. A
later policy-resolution pass will suppress sites governed by a resolved allowlist rather than
claiming that the forwarding operation itself is unsafe.
Six newly selected OpenAI Agents Python SDK calls account for the corpus increase; the retry wrapper
at `src/agents/mcp/server.py:1538` is pinned as a real dynamic-forwarding positive.

That policy pass now handles a same-function `not in` guard followed by `raise`/`return`. Guards are
applied in statement order: a rejection after the forwarding call does not govern the earlier action.
It resolves
and suppresses CAMEL's [registered-tool guard](https://github.com/camel-ai/camel/blob/473388d36390b22e0df31e25b7b2d50db55310d2/camel/utils/mcp_client.py#L1054)
before the dynamic call, while retaining the forwarding capability and a `tool-allowlist` control edge.

The resolver also recognizes an uncaught, statement-ordered lookup through an internal `self.*tool*`
registry. The MCP Python SDK's
[`SessionGroup.call_tool`](https://github.com/modelcontextprotocol/python-sdk/blob/57394b0548d1e2dc2dce8d67d84985769df3b8bb/src/mcp/client/session_group.py#L239-L241)
indexes both the tool-to-session map and the registered tool map before forwarding. An unknown name
therefore raises before the call. AgentVerify attaches a `tool-registry` edge with the lookup
location and explicitly marks its policy effect as `routing-only`. The review remains because this
registry aggregates every server-advertised tool and is not an authorization allowlist. A
caller-owned mapping, a lookup after the call, or a lookup hidden inside a caught fallback does not
qualify even as routing coverage.

The 49-site audit also found five forwarding calls in four repositories where the name comes from a
single constructor assignment with no class-local reassignment. CrewAI exposes the
stored name through a property, Trae through a zero-argument getter, Lagent directly through stored
metadata, and AgentScope has two calls over one stored tool. AgentVerify attaches a
`fixed-tool-binding` edge with `policy_effect: binds-tool-source-per-instance`. A second assignment,
deletion, or augmented assignment invalidates the proof. These five reviews remain: anchoring the
name to one stored source removes a direct call-parameter selector, but it does not prove that the
source object is immutable, the discovered tool set is an authorization allowlist, or arguments are
constrained.

Five more calls use captured parameters in callbacks that escape their factory: browser-use registers
three wrappers through its action registry, while ArcadeAI returns two LangChain tool callbacks. They
carry `binding_scope: closure` and `policy_effect: binds-tool-source-per-closure`. Merely nesting a
function does not qualify: the MCP Python SDK and FastMCP retry helpers are invoked within the same
caller-selected operation, so their names remain uncontrolled. A rebound parameter is likewise
unresolved. Schema v15 publishes the resulting fixed-binding split as five instance edges and five
closure edges; all ten remain AV-MCP002 reviews.

FastMCP contributes a second `tool-registry` edge through a same-class method summary. Its middleware
branch recursively calls `self.call_tool(..., run_middleware=False)`; the summarized callee resolves
the name through `get_tool`, rejects `None`, and only then invokes the tool. The edge records
`required_arguments: {run_middleware: false}` rather than assuming that the earlier recursive return
was bypassed. A local fallback fixture proves that substituting a default tool is not a rejecting
guard.

The bounded dependency closure now selects the MCP Python SDK's `tools` package reexport and
`ToolManager` body. `MCPServer.__init__` binds `self._tool_manager` once to that imported class;
`ToolManager.call_tool` resolves `get_tool(name)` and raises before execution when absent. This adds
the third `tool-registry` edge with `summary: imported-class-method`. Local negatives cover a mutable
manager attribute, a fallback manager, and a rebound imported constructor. Schema v15 distinguishes
one same-function lookup, one same-class method summary, and one imported-class summary; all three
retain their AV-MCP002 reviews as routing-only discovery controls rather than authorization
allowlists.

## AV-FS001 — dynamic writable tool path

The rule requires a writable dynamic path inside a resolved tool; ordinary application writes and
fixed tool paths do not trigger it. The full benchmark reports 18 default-scope sites across eight
repositories. A hand-reviewed case is ArcadeAI's
[local-filesystem MCP `write_file`](https://github.com/ArcadeAI/arcade-ai/blob/597debaa1593b54172061ce36a414cc29aa8fc6a/examples/mcp_servers/local_filesystem/src/local_filesystem/tools.py#L154),
which resolves a caller-provided path before writing. No workspace-root constraint is visible in the
tool function, but the result remains `review` because enclosing server policy is unresolved.
New TypeScript registration edges expose Mastra's
[`writeFile` tool adapter](https://github.com/mastra-ai/mastra/blob/1da5fb00e141b78c2148b21ee085ec24112cf2a5/packages/agent-builder/src/defaults.ts#L457-L475)
and the MCP filesystem server's
[`create_directory` callback](https://github.com/modelcontextprotocol/servers/blob/599dafc1054550a6eeb87a6545c1e1b03b3ca827/src/filesystem/index.ts#L412-L429).
For the latter, an unambiguous import chain resolves `validatePath` to a normalized,
separator-aware roots predicate; the callback rejects paths outside configured roots before `mkdir`.
AgentVerify emits a `path-boundary` control edge, but retains the review because the CLI/MCP-provided
roots are not statically known and could be broad. A literal narrow-root fixture demonstrates the
suppressible case. A helper name alone, prefix-only checks, missing imports, or a check after the
write remain unresolved.

The Python frontend adds a second pinned `path-boundary` edge at FastMCP's
[`download_skill` directory creation](https://github.com/jlowin/fastmcp/blob/609f79b8a118cd6c4bb58a5341bafd76e42e5a2b/fastmcp_slim/fastmcp/utilities/skills.py#L166-L184).
It proves the resolved candidate is checked with `is_relative_to()` before `mkdir`, but retains
unresolved scope because `target_dir` is caller configured. Local fixtures prove both fail-closed
and positive-branch dominance for literal absolute roots. Writes after the positive branch,
string-prefix checks, candidate/root reassignment, and candidates without `resolve()` remain
reviews. Parent-directory writes also require a strict-descendant check so an equal-to-root
candidate cannot escape through `.parent`. Schema v15 therefore records one Python and one TypeScript boundary edge, both unresolved
in the pinned corpus, while all 18 existing AV-FS001 reviews remain intact.

## AV-NET001 — parameter-controlled HTTP origin

The rule requires a recognized Python HTTP client or TypeScript global `fetch`/Axios call inside a
tool, or a uniquely named same-file TypeScript helper containing such a call, where an execution
parameter (or its shallow assignment/destructuring alias) determines the URL origin. A
literal URL and a template/concatenation whose resolved literal prefix already contains a complete
HTTP scheme and host remain inventory-only. The full benchmark reports five reviews across five
repositories:

- [Goose's Wikipedia MCP tool](https://github.com/block/goose/blob/48d480f91163bbcdc0f69f01befa3841a93a1d3e/examples/mcp-wiki/src/mcp_wiki/server.py#L29)
  checks only that the URL begins with HTTP before requesting it.
- [AgentOps' webpage tool](https://github.com/AgentOps-AI/agentops/blob/f8e907b92dabe47232978023fdcb01e2a7d4b752/examples/smolagents/multi_smolagents_system.py#L73)
  sends the tool's URL parameter directly to `requests.get`.
- The MCP TypeScript SDK's
  [`fetch-data` example](https://github.com/modelcontextprotocol/typescript-sdk/blob/3924de99df834302d89f5997a1b64ca268282284/packages/server/src/server/mcp.examples.ts#L130-L138)
  passes its registered tool input directly to global `fetch`.
- Mastra's
  [`httpRequest` tool](https://github.com/mastra-ai/mastra/blob/1da5fb00e141b78c2148b21ee085ec24112cf2a5/packages/agent-builder/src/defaults.ts#L1045)
  passes caller-provided `url` and optional `baseUrl` fields through a static helper to `fetch`.
- MCP Servers' registered
  [`gzip-file-as-resource` tool](https://github.com/modelcontextprotocol/servers/blob/599dafc1054550a6eeb87a6545c1e1b03b3ca827/src/everything/tools/gzip-file-as-resource.ts#L85)
  passes its validated URL through `fetchSafely`; its hostname allowlist is optional and empty by
  default, while byte and timeout limits constrain response size and duration rather than origin.

Pinned negatives include a [fixed Devpost origin](https://github.com/microsoft/ai-agents-for-beginners/blob/01777b05e8afeba6bf5a6dbe74cc2293372d3693/11-agentic-protocols/code_samples/github-mcp/app.py#L118),
the MCP SDK's [fixed weather API](https://github.com/modelcontextprotocol/typescript-sdk/blob/3924de99df834302d89f5997a1b64ca268282284/examples/guides/get-started/firstServer.examples.ts#L20-L40),
and Vercel's [literal PDF URL](https://github.com/vercel/ai/blob/f607a129c0298870038b398dbcba57ff041114f6/examples/ai-e2e-next/tool/fetch-pdf-tool.ts#L5-L12).
Results remain `review`: URL validation, redirects, DNS rebinding, proxies, and runtime egress policy
are not yet resolved.

## AV-SANDBOX001 — container/host boundary

The rule found 19 default-scope boundary crossings across nine repositories. It reports development
and production configuration alike but retains their source path so policy can distinguish them.
Hand-reviewed examples include:

- [AutoGen devcontainer Docker socket](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/.devcontainer/docker-compose.yml#L11)
- [Langflow deployment Docker socket](https://github.com/langflow-ai/langflow/blob/09ef6b2b7119e35a6787fc249f916f8b47b28615/deploy/docker-compose.yml#L10)
- [Bytebot privileged container](https://github.com/bytebot-ai/bytebot/blob/3d37894ce07ef8d8b40adc7fd309ad96c2a71313/docker/docker-compose.yml#L15)
- [Bytebot Helm privileged default](https://github.com/bytebot-ai/bytebot/blob/3d37894ce07ef8d8b40adc7fd309ad96c2a71313/helm/charts/bytebot-desktop/values.yaml#L40)
- [OpenHands service-account token default](https://github.com/OpenHands/OpenHands/blob/4a8cabc5fdc81bb6d899785f33ea7449387beb4c/helm/agent-canvas/values.yaml#L45)
- [AutoGPT read-only Docker socket mount](https://github.com/Significant-Gravitas/AutoGPT/blob/601093ddfe23a3d58a9c8f4a208bd49b203ee612/autogpt_platform/db/docker/docker-compose.yml#L471)
- [trae-agent privileged Docker SDK call](https://github.com/bytedance/trae-agent/blob/e839e559ac61bdd0e057c375dd1dee391fee797d/evaluation/patch_selection/trae_selector/sandbox.py#L33)
- [Skyvern host-mounted credentials directory](https://github.com/Skyvern-AI/skyvern/blob/486c8975e9864a53037d4701b781f8619e698c40/kubernetes-deployment/backend/backend-deployment.yaml#L63)

A read-only Docker socket mount is still reported because the Docker API can create privileged
workloads even when the socket file itself is mounted read-only. A mounted service-account token does
not by itself prove useful Kubernetes privileges; the result remains `review` until RBAC bindings and
the rendered workload are resolved. Likewise, a `hostPath` finding proves a node-filesystem boundary,
not that its contents are sensitive; path-specific policy and pod scheduling remain unresolved. The
Docker SDK frontend currently requires an imported `docker` module, a `.containers.run(...)` call,
and a literal `privileged=True` keyword.

## Seed truth-set metrics

`benchmarks/truthset.json` contains 185 exact labels across all eight enabled rules: 108 positives and 77
negatives. Labels mix local fixtures, immutable real positives, and unmatched real corpus observations,
including a CAMEL allowlist, fixed-name MCP, ordinary non-tool filesystem writes, fixed argv and
literal TypeScript shell calls, constant/test-only eval, non-approval skip flags, disabled
auto-approval, conditional environment guards, late MCP guards, and safe
Compose/Kubernetes/Docker SDK settings. All 185 currently pass; each rule's seed precision and recall
are 1.0. Negative labels must retain either an observed Agent IR component anchor or verified source
text at the exact pinned line, preventing a missing or drifting location from passing silently.

This is a curated regression set, not an unbiased estimate of ecosystem precision or recall. The next
benchmark milestone is a separately sampled, externally reviewed holdout set with framework-stratified
coverage; its labels must not drive rule implementation before evaluation.

## Agent IR control-edge checks

IR relationship inference is scored separately from finding rules in `benchmarks/ir-truthset.json`.
Four audit labels pair a traced and untraced local external action with ArcadeAI's pinned
[Gmail send span](https://github.com/ArcadeAI/arcade-ai/blob/597debaa1593b54172061ce36a414cc29aa8fc6a/examples/mcp_servers/telemetry_passback/src/telemetry_passback/server.py#L234)
and its sibling authentication span. Only the `httpx` send at line 241 is governed by the send span;
the authentication span at line 223 does not claim action coverage. All four labels pass. Exporter
configuration and durable storage remain unresolved, so this inventory edge does not suppress a
finding or enable `AV-AUDIT001`. The full corpus scan observed seven action-trace controls and five
lexically governed HTTP capability edges, all in that ArcadeAI telemetry example.

Three MCP registry labels cover the local control edge, a caller-owned-map negative, and the pinned
SDK SessionGroup edge. Four fixed-instance labels cover a local constructor-only binding, a mutable
negative, AgentScope's pinned wrapper, and Trae's pure-getter path. Three import labels cover a
resolved relative fixture, a missing-module
negative, and the pinned CrewAI-LangGraph draft-tool edge. Seven approval labels cover enabled,
disabled, callback, and automatic-handler policies plus pinned Python and TypeScript OpenAI shell
edges. Four TypeScript graph
labels cover inline and assigned agent adapters, the Cline tool path, and a nested-token negative.
Nine registration labels cover four local Mastra/MCP edges, an ordinary-registry negative, and four
pinned Mastra/MCP capability edges. Six helper-summary labels cover two local edges, two pinned
Mastra edges, the MCP Servers edge, and a regex-literal negative. Four TypeScript path-boundary labels
cover a local proven guard, imported name-only and reassignment negatives, and MCP Servers' real
control edge. Six Python path-boundary labels cover two local proven branches, two local bypasses, a
configured-root edge, and FastMCP's real control edge. Four closure-binding labels cover a returned local callback, a rebound negative, browser-use's
registered wrapper, and the Python SDK retry negative. Three method-registry labels cover a local
resolved callee, a fallback negative, and FastMCP's real summary. Five imported-registry labels cover
a local resolved manager, mutable/fallback/rebound negatives, and the pinned MCP Python SDK manager.
All 62 IR labels pass: three approval positives/four negatives,
two audit positives/two negatives, two import positives/one negative, three TypeScript graph
positives/one negative, eight registration positives/one negative, five helper-summary positives/one
negative, six path-boundary positives/four negatives, two MCP-registry positives/one negative, three
fixed-instance positives/one negative, two closure positives/two negatives, two method-registry
positives/one negative, and two imported-registry positives/three negatives.

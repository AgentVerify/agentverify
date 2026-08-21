# Detection validation log

Validation date: 2026-08-22. Repositories are partial checkouts pinned by
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
- `cases/python_openai_mcp_approval_default`: a directly bound stdio MCP server inherits the OpenAI
  Agents Python disabled approval default; explicit approval and broken SDK propagation stay negative.
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
- `cases/python_post_registration`: exact FastMCP decorator applications resolve same-module and
  relative-imported functions; wrappers, nested calls, rebound bindings, duplicate registrars, and
  unrelated factories remain negative.
- `cases/python_browser_evaluate`: Playwright page evaluation preserves both inventory and browser
  execution context; exact `Page` annotations and an immutable alias prove dynamic receivers, while
  literal JavaScript, an ordinary non-browser `.evaluate(...)` in the same import context, and a
  reassigned typed page remain negatives.
- `cases/python_registry_tools`: import-proven MetaGPT function/class and Qwen class decorators retain
  exact entrypoints and capability edges; unlisted methods, nonliteral entrypoints, rebound or
  unrelated registrars, arbitrary `.open()` methods, fixed filesystem paths, and fixed HTTP origins
  remain negative for their corresponding rules.
- `cases/python_imported_network_helper`: exact named imports propagate unique top-level helper
  network behavior and caller arguments; fixed origins and arguments remain inventory-only, while
  nested helpers, module calls, rebound imports/clients, and local reassignment remain unresolved.
  Single-entrypoint class cases cover direct construction, immutable fields, two-hop propagation,
  fixed inputs, mutation, `setattr`, shadowing, module-qualified calls, and rebound constructors.
- `cases/network_dynamic_origin`: import-proven urllib module/named aliases cover direct URLs and
  `Request(url)` objects; fixed hosts remain inventory while local shadowing and module rebinding
  withhold the opener identity.
- `cases/python_proxy_conditional_network_helper`: direct fetches and manually followed redirects
  retain distinct policy states; proxy-dependent pinning stays conditional, while a missing peer
  assertion and an ordinary request remain negative.
- `cases/python_configurable_network_helper`: default-on connector gates compose with allowlist and
  loopback exemptions, enforcement-conditional pinning/proxy rejection, and distinct redirect modes;
  disabling the default, breaking the pinned backend, or calling ordinary `httpx` remains negative.
- `cases/typescript_configurable_ssrf_composition`: a default-off real-versus-passthrough service
  choice propagates into a LangChain tool and Axios helper; a default-on mutation changes policy
  state, while branch, lookup, and redirect-hook mutations plus a raw-Axios near miss remain negative.
- `cases/typescript_flowise_secure_request`: variable Flowise node URLs reach either a fixed Axios
  request object or `secureFetch`; the latter overrides caller options with a pinned agent after the
  spread. Default, redirect, lookup, deny-predicate, caller-transport, mapped-IP, broken class-flow,
  and unrelated same-named-helper negatives withhold the corresponding policy edge.
- `cases/typescript_google_adk_secure_fetch`: an imported `FunctionTool` maps its model URL into a
  same-file global-fetch helper with fail-closed address preflight and disabled redirects; missing
  imports, fixed inputs, automatic redirects, incomplete DNS/address checks, and mapped-IP bypasses
  withhold the edge.
- `cases/typescript_axios_instance`: immutable same-file Axios instances cover direct verbs and
  `.request(...)`, fixed bases, absolute-URL override disabling, no-base behavior, and a shadowed
  local-client negative.
- `cases/typescript_activepieces_safe_http`: exact Activepieces imports compose a manifest-pinned
  filtering Axios client with the MCP transport; private-address, agent-ordering, caller-proxy,
  manifest, and import mutations withhold the policy.
- `cases/typescript_composio_ssrf_safe_fetch`: conditional package imports preserve Node Undici
  pinning, configured-route residuals, edge fail-closed behavior, and the distinct intentionally
  unguarded `WhereSupported` fallback; runtime-map and transport mutations withhold the policy.
- `cases/typescript_composio_cli_upload`: schema-marked tool arguments recursively reach raw fetch
  for URL file inputs; guarded transport, fixed arguments, broken gates, and wrong imports withhold
  the path.
- `cases/typescript_google_adk_openapi_rest_tool`: generated OpenAPI tools preserve a
  spec-configured origin while encoding model path segments; dynamic server variables, unencoded
  paths, credential URL rewrites, and broken factory imports withhold the control.
- `cases/typescript_a2a_card_endpoint`: two remote-card flows reach `ClientFactory`: ADK JS through
  an import-proven resolver and Gemini through an Undici agent/proxy dispatcher. Fixed cards, fixed
  resolver inputs, wrong imports, and unproven dispatchers withhold the corresponding edge.
- `cases/python_a2a_card_endpoint`: cached and per-invocation client creation are both dominated by
  all-interface HTTPS/loopback and same-origin validation. Primary-interface-only, reversed-origin,
  and permissive-scheme mutations withhold the policy edge.

## Full-corpus engine benchmark

The 2026-08-22 default scan covered 70 source-bearing repositories plus one docs-only upstream
snapshot. It parsed 10,763 selected Python/TypeScript/JavaScript files plus 155 configuration files,
resolved 1,527 relationships, and completed in 179.38 seconds on the development machine. Three parse
warnings were isolated and reported without aborting the run. Tests and fixtures are inventoried but excluded from findings by
default; `--include-tests` enables them. The pinned corpus contains no AgentVerify inline directives,
so the benchmark records zero suppressed findings.

The locked collector prioritizes manifests, production SSRF/URL-safety sources, and then general
security/agent/tool/MCP sources within the 220-file cap. It adds at most 20 local source files:
versioned audited evidence hints plus Python imports reached from MCP forwarding or source-proven
URL-security call sites, all charged against the same cap. This refresh materialized 168 dependency files across 18
repositories; the engine scans all of them, while the collector's lexical-signal inventory retains
its independent 2 MB per-repository byte cap. Collector schema v4 records the hint manifest and
dependency count per repository; engine schema v52 carries both the 168-file total and the
18-repository coverage.

Engine benchmark schema v52 retains stable component-name taxonomies, category presence counts,
matched-versus-identified endpoint counts, TypeScript graph precision measures, and exact MCP
forwarding-control counts. It also publishes Python and TypeScript initial-origin control coverage
plus source-proven Python and TypeScript secure transports, with redirect, DNS, proxy, configured
scope, and open/default-disabled states kept separate. It intentionally
excludes arbitrary agent/tool display names from the summary. The resulting
framework/provider/protocol/capability coverage and unsupported syntax are published in
`docs/frontend-coverage.md`; presence counts are discovery observations, not recall measurements.

Schema v52 retains A2A endpoint provenance as a separate authority class: four exact client-construction
paths comprise two unconstrained remote-card-selected TypeScript origins and two same-origin-
constrained ADK Python paths. The guarded paths validate every advertised interface; the Gemini path
also records its Undici agent/proxy transport. These metrics do not count configured card URLs as
model-controlled AV-NET001 origins.

Schema v52 also publishes immutable same-file Axios-instance metrics and the sixth TypeScript
secure-network composition. The corpus-level generic instance counters are zero; those syntax paths
are fixture-validated. The selected Activepieces path contributes one imported-client capability and
one address-filtering control with configured allowlist and environment-proxy residual metrics. Four
Composio edges separately count configured-route pinning residuals, one edge-runtime fail-closed path,
and three edge-runtime unguarded fallbacks.

The benchmark now also measures identity coverage: 8,927 agent/tool component observations carry
module-qualified IDs. Of 3,054 relationship endpoints, all 2,171 identified symbol endpoints resolve
to an observed component (1,912 Python and 259 TypeScript). Schema v52 records 311
`lexical-single-definition` targets plus 20 exact same-block dominating definitions. Fifteen
import-proven OpenAI Agents Python `ComputerTool` instances add ten exact agent links, including
three formerly ambiguous repeated bindings. Literal Agent tool lists add 150 direct callable tools,
83 outside tests, with seven capability edges and 162 exact Agent edges. Import-proven OpenAI
`function_tool(function)` assignments add 12 wrapper tools and 12 exact Agent edges; three explicitly
enable approval, all occur under tests, and none of their selected bodies contains a recognized
capability. Four corpus targets in parameter, helper-return, or tuple-unpack forms remain withheld;
cross-branch, forward, parameter, shadowed-factory, lambda, and reassigned fixture cases also stay
unresolved. Two former CrewAI misses were false
package-import identities attached after a same-named function parameter or assignment shadowed the
import; their IDs remain withheld.
Capability, control, and taxonomy endpoints intentionally remain evidence observations.

Schema-v52 benchmark output measures native AI BOM endpoint resolution separately. AI BOM 1.2
resolves 2,171 endpoints by symbol ID, 521 by exact evidence location, and 15 by a unique display
name; 29 remain ambiguous and 318 unresolved. Before evidence-local and occurrence-qualified
resolution, raw name matching left many endpoints ambiguous. Exact locations resolve additional
capability/control endpoints. Unique occurrence IDs resolve repeated source agent/tool observations
and mark unsafe targets explicitly unresolved. Conservative lexical resolution removes further target
ambiguities. The 29 remaining ambiguities are control or tool targets without a unique local definition, so the
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

Python post-definition registration recovery resolves all 115 pinned Skyvern tools through direct
module-level `mcp.tool(...)(function)` applications. Each target has one immutable relative import
and one unique module-level definition. Ninety-three registrations are direct; 22 pass through
metadata-preserving forwarding wrappers, totaling 23 wrapper layers. A wrapper must carry an exact
`functools.wraps(function)` decorator and directly call `function(*args, **kwargs)` from its returned
callback; direct wrappers, decorator factories, and chains of at most four layers are supported.
These tools yield 21 exact capability edges—14 browser actions, six browser-page evaluations, and
one filesystem mutation—rather than 115 findings. Only one of 30 Skyvern evaluations receives raw
tool-controlled script text; the remaining evaluator inventory is not promoted to a finding.
The filesystem edge exposes
[`resolved.parent.mkdir(...)`](https://github.com/Skyvern-AI/skyvern/blob/486c8975e9864a53037d4701b781f8619e698c40/skyvern/cli/mcp_tools/state.py#L89)
inside `skyvern_state_save`; equality with an allowed root does not prove that its parent remains
inside the root. Opaque and branch-only wrappers, nested registrations, rebound imports or
registrars, wildcard imports, and unrelated `.tool` methods remain unresolved.

Import-proven registry decorators recover another 56 Python tools: five functions and 51 classes,
with 35 observations from MetaGPT and 21 from Qwen-Agent. Thirty-four have resolved callable
entrypoints and yield 26 exact capability edges after imported-helper and urllib propagation. MetaGPT functions use their decorated body;
MetaGPT classes expose only direct methods named by a literal `include_functions=[...]`; Qwen classes
require a literal registered name and one direct `call` method. The class remains the tool identity,
so method capabilities do not create duplicate tool components. Exact module provenance and
statement-ordered alias rebinding prevent ordinary or rebound `register_tool` functions from being
promoted. Dynamic entrypoint lists and names remain unresolved rather than making every class method
reachable.

These edges expose four MetaGPT AV-FS001 reviews and two Qwen AV-NET001 reviews while preserving
near misses. A literal `Path(...).write_text(...)` is filesystem inventory but not a dynamic-path
review, and arbitrary object `.open(...)` methods are not filesystem capabilities. Qwen fixed-host
URLs remain inventory-only when a dynamic path or query is concatenated to a proven module constant
or formatted through an immutable `self` URL field.

Python imported network summaries add exactly two corpus capabilities, both dynamic, each from a
different unique top-level helper and each with an exact tool edge. Qwen's `simple_doc_parser`
passes its tool-controlled URL to the imported `save_url_to_local_work_dir`, whose corresponding
formal reaches `requests.get`. Smolagents' `visualizer` performs a function-local self-import of
`encode_image`; its image-path parameter reaches another `requests.get`. The edge is attached at the
tool call site and retains the helper path, definition line, and network sink lines. Exact named
imports, unique top-level definitions, direct formal flow, and recognized clients are required;
module-object calls, nested helpers, reexports, transitive calls, local aliases, and any relevant
binding or client rebinding remain unresolved.

An iterative class pass adds four more capabilities and exact tool edges, all dynamic and all in
Qwen-Agent. It first summarizes `SimpleDocParser.call` from its proven imported-function network
edge, then resolves direct construction in `WebExtractor` and immutable fields in `DocParser` and
`ExtractDocVocabulary`. `DocParser` becomes a summary on the next iteration, exposing `Retrieval` as
a two-hop path. The two callee summaries retain definition and prior network-edge lines. Only unique
registered classes with one literal entrypoint qualify; exact named imports, direct construction or
one constructor-only field, and caller argument flow are required. A unique literal key read by the
callee maps only that caller object field, so a fixed URL plus a dynamic sibling remains inventory.
Fixed inputs retain an inventory edge. Multiple assignments, deletion, `setattr`, shadowed/rebound constructors, duplicate classes,
module-qualified calls, inheritance, and more than four iterations remain unresolved.

The TypeScript frontend now reads only balanced top-level entries from literal Agent tool arrays. It
resolves OpenAI `tool`, `toolNamespace`, built-in tool factories, inline/assigned `asTool` adapters,
and Cline `createTool`. Import-aware discovery now also resolves generic/Mastra object-property
tools plus MCP `registerTool` names and callback spans. Schema v38 records 27 Mastra factory tools,
264 MCP registrations, 70 object-property tools (the factory/property categories overlap), and ten
exact registration-to-capability edges. Four of those edges come from bounded same-file network
helper summaries: three Mastra static methods and one MCP Servers free function. Schema v38 also
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

For Python, files importing the OpenAI Agents SDK now inventory `ShellTool`, `ApplyPatchTool`,
`ComputerTool`, and `CustomTool` instances with line-scoped identities. `ComputerTool` produces a
local computer-control capability and records its optional `on_safety_check` callback separately
from generic approval policy. All 15 observed instances are local, two configure the callback, and
only the pinned SDK example instance is outside test paths. A literal `needs_approval=True` with no
automatic handler creates an exact tool-to-control edge; literal false and the SDK default are recorded as
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

Schema v52 separately inventories OpenAI Agents Python's MCP approval default without widening the
rule. In the pinned sandbox-agent example, omitted `MCPServerStdio.require_approval` flows through the
SDK's `None → False` normalization and missing-name false fallback into each generated
`FunctionTool`, and the exact server binding reaches `SandboxAgent.mcp_servers`. The IR emits one
agent→server edge and one disabled-default policy setting. No AV-APPROVAL002 review is emitted because
the downstream reference-policy tools are not a proven destructive capability. Two negative rule
labels, two positive/one negative IR labels, and six mutations preserve that boundary.
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
parameter reaches `exec`. Browser-aware evaluation adds one more exact path: Skyvern's registered
[`skyvern_evaluate`](https://github.com/Skyvern-AI/skyvern/blob/486c8975e9864a53037d4701b781f8619e698c40/skyvern/cli/mcp_tools/browser.py#L2458)
passes its tool parameter to Playwright `page.evaluate`. Across 80 inventoried browser-page
evaluations, this is the only one with direct tool-parameter flow, raising `AV-EXEC002` to 51 across
15 repositories. Schema v38 proves seven receivers: two exact Playwright `Page` annotations in
SWE-agent and five results of Skyvern's exact imported `get_page` factory. The other 73 fixed-script
observations remain inventory with unresolved receiver state. Dynamic calls with only browser-import
context are withheld: local regressions cover an ordinary calculator's `.evaluate(...)`, a
reassigned typed page, and one immutable typed-page alias. Skyvern's normalized numeric scroll
JavaScript at line 1664 remains a real negative. Registry and receiver fixtures bring the rule to 21
positive and 15 negative exact labels.

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
unresolved. Schema v38 publishes the resulting fixed-binding split as five instance edges and five
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
manager attribute, a fallback manager, and a rebound imported constructor. Schema v38 distinguishes
one same-function lookup, one same-class method summary, and one imported-class summary; all three
retain their AV-MCP002 reviews as routing-only discovery controls rather than authorization
allowlists.

## AV-FS001 — dynamic writable tool path

The rule requires a writable tool-input-derived path inside a resolved tool; ordinary application
writes and fixed/configured tool paths do not trigger it. The full benchmark reports 28 default-scope sites across nine
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
suppressible case. A helper name alone, missing imports, or a check after the write remain
unresolved. Exact string-prefix checks are classified separately by AV-FS002 and never satisfy this
boundary.

Post-definition registration recovery adds Skyvern's
[`skyvern_state_save`](https://github.com/Skyvern-AI/skyvern/blob/486c8975e9864a53037d4701b781f8619e698c40/skyvern/cli/mcp_tools/state.py#L71)
to exact tool reachability. Its line-89 parent-directory creation remains a review because
`_validate_state_path` permits the resolved candidate to equal an allowed root; that does not prove
the candidate's parent remains within the boundary.

Registry-decorator recovery adds four MetaGPT sites: the Editor's parent creation and file write plus
GPT-v Generator's output-directory creation and write. Its exact Qwen class entrypoints add one
`simple_doc_parser` directory creation; the path includes a hash of the tool input, so this remains a
conservative review rather than a demonstrated traversal. A fixed literal `Path.write_text` fixture
retains its capability edge without a finding. Attribute `.open(...)` calls now require a proven
`pathlib.Path` receiver, preventing MetaGPT's in-memory filesystem API from being misclassified as a
host filesystem sink.

The Python frontend adds a second pinned `path-boundary` edge at FastMCP's
[`download_skill` directory creation](https://github.com/jlowin/fastmcp/blob/609f79b8a118cd6c4bb58a5341bafd76e42e5a2b/fastmcp_slim/fastmcp/utilities/skills.py#L166-L184).
It proves the resolved candidate is checked with `is_relative_to()` before `mkdir`, but retains
unresolved scope because `target_dir` is caller configured. Local fixtures prove both fail-closed
and positive-branch dominance for literal absolute roots. Writes after the positive branch,
string-prefix checks, candidate/root reassignment, and candidates without `resolve()` remain
reviews. Parent-directory writes also require a strict-descendant check so an equal-to-root
candidate cannot escape through `.parent`. ChatDev adds a second Python form at its
[`target_path.relative_to(tools_dir)`](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/server/routes/tools.py#L58)
check: the try body contains only the check and the ValueError handler terminates before the write.
OpenAI Agents Python adds the interprocedural form: `WorkspaceEditor._resolve()` returns the exact
resolved value after an exclusive, terminating `relative_to(self._root)` check, and its create,
update, and delete methods consume that return at two writes and one unlink. AgentVerify propagates
the proof only through a unique undecorated same-class helper, exact argument mapping, restricted
`Path` construction, and an unchanged return binding. It records `summary: same-class-return` and
keeps the scope unresolved, so these inventory controls do not suppress a tool review. Duplicate or
rebound methods, async/generator helpers, opaque path transforms, continuing handlers, different or
reassigned returns, try `else`/`finally` mutation, conditional construction preludes, caller
reassignment, and parent writes remain unresolved.

Schema v38 therefore records five Python and one TypeScript boundary edges, all with unresolved root
scope in the pinned corpus. Four Python edges use `Path.relative_to`; three are same-class return
summaries. The helper distinction and summary provenance are explicit.

Canonical, top-level import-aliased, and statement-ordered local callable-aliased `os`/`shutil`
mutations extend the Python sink model beyond `open()` and ordinary `Path` methods. They contribute
429 calls; with proven Path moves, the full inventory contains 449 calls: 179 creates, 191 deletes,
46 copies, and 33 moves. Two-path APIs use the destination
argument, including keyword `dst`, and calls record their canonical API, possible API family,
operation, path role, and callable-alias provenance. The added real case is ArcadeAI's
[`copy_fn` selection between `shutil.copy` and `shutil.copy2`](https://github.com/ArcadeAI/arcade-ai/blob/597debaa1593b54172061ce36a414cc29aa8fc6a/examples/mcp_servers/local_filesystem/src/local_filesystem/tools.py#L329-L331),
raising the rule total by one without adding a repository. Compatible branch-local choices merge;
calls before assignment, conditional rebinding to an unknown wrapper, and copy/delete choices remain
negative. A fixed destination and two boundary-guarded copies are local negatives; shadowed imports
and string `.replace()` remain explicit near misses.

Schema v38 additionally resolves 20 `Path.rename`/`Path.replace` moves: two renames and 18 replaces.
Receivers require an explicit unshadowed constructor, an exact Path annotation, or a single immutable
local derived from one. DeepAgents contributes 18 real atomic replacement calls; these are inventory,
not AV-FS001 reviews, because they are not reached from resolved tools. Conditional, reassigned,
union-typed, helper-returned, and shadowed receivers remain unresolved. The destination argument is
still the governed path. ChatDev's
[`source_path.rename(target_path)`](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/server/services/workflow_storage.py#L137)
is a pinned immutable-derived receiver, and a local guarded-rename fixture proves boundary-control
integration.

## AV-FS002 — string-prefix filesystem boundary

The specialized rule reports four default-scope sinks in one pinned repository, CrewAI Examples.
Its file writer checks
[`not str(resolved_path).startswith(str(workdir))`](https://github.com/crewAIInc/crewAI-examples/blob/da94a91e691e1cf5b3151416bb15b5b62729bea8/crews/landing_page_generator/src/landing_page_generator/tools/file_tools.py#L58)
before a parent `mkdir` and `open`; its template copier applies the same shape to
[`destination_resolved`](https://github.com/crewAIInc/crewAI-examples/blob/da94a91e691e1cf5b3151416bb15b5b62729bea8/crews/landing_page_generator/src/landing_page_generator/tools/template_tools.py#L71)
before another parent `mkdir` and `copytree`. A raw string prefix is not a path-component boundary:
a sibling such as `/workspace-escape` starts with `/workspace`.

AgentVerify follows parameter taint through tuple unpacking and self-derived string assignments,
tracks unresolved root joins until `resolve()`, and propagates facts through a try only when
continuing handlers do not bypass the check. Each sink receives a non-suppressing
`path-prefix-check` edge with `weak-string-prefix-validation`; AV-FS002 replaces the generic AV-FS001
result at that location. A check after the sink and a separator-aware expression are pinned
negatives. The rule has high pattern confidence but remains a `review`: an independent allowlist,
sandbox, or other enclosing policy may still prevent exploitation.

## AV-NET001 — parameter-controlled HTTP origin

The rule requires a recognized Python HTTP client or TypeScript global `fetch`/Axios call inside a
tool, or a uniquely named same-file TypeScript helper containing such a call, where an execution
parameter (or its shallow assignment/destructuring alias) determines the URL origin. Immutable
same-file Axios instances preserve direct verb and `.request(...)` flow, including fixed-base and
`allowAbsoluteUrls: false` discrimination. Five exact TypeScript composition families additionally
propagate URLs through imported Axios, `node-fetch`, or global-fetch helpers. A
literal URL and a template/concatenation whose resolved literal prefix already contains a complete
HTTP scheme and host remain inventory-only. The full benchmark reports 17 reviews across ten
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
- Qwen-Agent's multimodal crop example and `image_zoom_in_tool` pass caller-selected remote image
  URLs to `requests.get`. Exact class-registry entrypoints make both network calls reachable.
- Qwen-Agent's registered `simple_doc_parser` passes its URL to an exact imported downloader, and
  smolagents' `visualizer` passes an image path to a function-local self-imported encoder. Each
  helper's matching formal parameter directly reaches `requests.get`; the call-site capability
  retains the helper and sink locations.
- Qwen's `doc_parser`, `extract_doc_vocabulary`, and `web_extractor` reach that same downloader
  through `SimpleDocParser.call`; `retrieval` reaches it through the newly summarized
  `DocParser.call`. Exact class and tool identities make the second hop explicit.
- n8n's AI Builder `web_fetch` passes its parsed tool URL into an imported Axios helper. Its address
  policy is default-off and separately modeled below, so the dynamic-origin review remains visible.
- Flowise contributes two paths: its Agentflow HTTP node copies a variable URL into a fixed Axios
  request object, while its Web Scraper tool propagates `_call(initialInput)` through the recursive
  scraper into `secureFetch`; their distinct transport residuals are modeled separately below.
- Google ADK JS's `LOAD_WEB_PAGE` maps its model-controlled URL into `loadWebPage`; its preflight-only
  address policy and unpinned global fetch are modeled separately below.

Schema v38 separately inventories 22 import-proven `urllib.request.urlopen` calls. Two occur in
Qwen's registered `area_to_weather` and `weather_hour24` tools and therefore receive exact tool
edges. Both construct `Request` objects from a fixed `https://ali-weather.showapi.com` origin plus
tool-controlled query data, so unwrapping the Request's URL keeps them inventory-only. The other 20
calls are outside resolved tool bodies and do not create tool reachability. Exact module-level
imports or aliases are required; rebinding and same-function shadowing invalidate the symbol proof.

Python `urlparse`/`urlsplit` guards now create a `network-origin-allowlist` edge only when an immutable
tool-origin value is checked against static nonempty scheme and hostname sets and the rejecting branch
terminates before the direct request. The control explicitly covers the initial origin only. An
explicit `allow_redirects=False` or `follow_redirects=False` is recorded as redirect-disabled; all
other redirect behavior and DNS scope remain unresolved. The full corpus contains zero such exact
Python controls on its Python review paths. This is a bounded governance gap, not proof that imported validators,
proxy policy, or runtime egress controls are absent.

MCP Servers' same-file `validateDataURI` now contributes one TypeScript
`network-origin-policy` edge to the gzip resource fetch. The validator always restricts schemes to
`data`, `http`, or `https` and uses exact/subdomain matching when `GZIP_ALLOWED_DOMAINS` is nonempty.
Because the normalized environment list explicitly defaults to empty, the edge records
`configured-optional` and `hostname_default: open`; DNS and redirect scope remain unresolved. It
therefore explains partial governance without satisfying destination policy or suppressing the review.

Schema v38 also resolves CrewAI's locally defined `safe_get` as a `network-ssrf-policy` at two
production call sites: `DocsSiteLoader.load` and `DOCXLoader._download_from_url`. The helper validates
the initial URL and each redirect, disables automatic redirects and environment proxies, rejects
private/reserved DNS results, and verifies the connected peer through its mounted adapter. Both edges
record `enforcement_default: enabled`, `redirect_scope: each-hop-validated`,
`dns_scope: connection-pinned`, and `proxy_scope: disabled`. The
`CREWAI_TOOLS_ALLOW_UNSAFE_PATHS` escape hatch and `CREWAI_TOOLS_FORCE_SAFE_PATHS` override remain
explicit instead of being collapsed into unconditional protection. Ten test-scope `safe_get` calls
are inventoried but excluded from the production-control total.

Schema v38 adds two production Composio edges from the session-file router to `safe_get` and
`safe_request`. Both validate HTTP(S) targets against public resolution results before requesting and
pin direct connections through a protected adapter with a connected-peer assertion. `safe_get`
records `redirect_scope: disabled`; `safe_request` follows a bounded loop and records
`redirect_scope: each-hop-validated`. The helper deliberately allows environment or caller proxies,
where the proxy resolves the target and the SDK cannot pin that peer. Both edges therefore record
`dns_scope: connection-pinned-unless-proxied` and
`proxy_scope: environment-or-caller-dependent`, rather than inheriting CrewAI's stronger
`connection-pinned`/`disabled` profile. Four positive and one negative exact IR labels validate this
new family.

Schema v38 adds ten Langflow production edges whose policy is strong when enabled but explicitly
configurable. The collector's schema-v4 selection-hint manifest lists 11 callers from Langflow's own
SSRF-wiring registry plus the security settings source; all 12 files are charged against the existing
20-file dependency cap. The analyzer then resolves exact imports across Langflow's nested source root
and requires the default-on global and connector settings, both gate implementations, configured
allowlist and default literal-loopback behavior, the core public-address validator, async and sync
backends that connect to validated IPs, proxy-rejecting transports, protected client construction,
and ordinary-client fallbacks. Five synchronous GET edges disable redirects by default and validate
each bounded hop when enabled; the other five GET/POST edges reject automatic redirects. All ten
record `dns_scope: connection-pinned-when-enforced`, `proxy_scope: disabled-when-enforced`, and both
opt-out environment names. The initial-origin scope explicitly preserves configured allowlists and
the default literal-loopback exemption, so no edge claims unconditional SSRF prevention. Four
positive and one negative IR labels cover local sync/async applications, DeepSeek and Glean pinned
calls, and an ordinary request; mutations of the enabled default or pinned backend withhold the
summary.

Schema v38 resolves n8n's AI Builder `web_fetch` as a dynamic-origin tool path and preserves its
default-off composition. Four audited hint files add the CLI composition root, discovery subgraph,
tool factory, and Axios helper within n8n's existing dependency budget. The composition root injects
`SsrfProtectionService` only when `N8N_SSRF_PROTECTION_ENABLED` is true; the false/default branch
injects `createPassthroughSsrfGuard`, whose URL checks are successful no-ops and whose lookup is the
ordinary DNS function. The enabled service applies configured hostname/IP allowlists and blocklists,
preflight resolution, and a custom lookup that validates addresses returned at connection time. The
Axios helper caps redirects at five, uses the custom lookup, validates direct-IP redirect targets,
halts cross-host auto-follow, and revalidates the cross-host URL before a second fetch. The edge still
records `proxy_scope: unresolved`: selected source does not prove whether Axios proxy routing keeps
the custom lookup on the destination. Independent domain HITL is retained as governance context but
does not satisfy address policy. Two positive and one negative IR labels cover the local and pinned
edges plus raw Axios. Mutations of the composition branch, lookup, or redirect hook withhold the
edge; a literal default-on mutation instead retains it and changes its enforcement/escape state.

Schema v38 also resolves two Flowise paths. Its `httpAgentflow` node reaches
`secureAxiosRequest` through a fixed request object, while `web_scraper_tool` propagates
`_call(initialInput)` through `scrapeRecursive` and `scrapeSingleUrl` into `secureFetch`. Two audited
caller hints and the `src/index.ts` re-export barrel are charged against Flowise's dependency budget.
The HTTP node exposes
`nodeData.inputs.url` as a variable input, derives `finalUrl`, and assigns it to the
fixed config's `url` property before the imported call. The helper enables its default address deny
list unless `HTTP_SECURITY_CHECK=false`, normalizes IPv4-mapped IPv6, validates every DNS answer,
disables automatic redirects, validates each manual hop, and installs an agent lookup pinned to the
chosen address. The exact caller supplies no adapter, agent, proxy, socket path, transport, or spread
property. Environment proxy routing remains a real residual, so the edge records
`dns_scope: connection-pinned-unless-proxied`, `proxy_scope: environment-dependent`, and
`escape_hatch: configured-opt-out`. The fetch helper overwrites the caller's requested redirect mode
with `manual`, validates and resolves every bounded hop, then supplies `agent: () => agent` after the
caller-option spread. Its edge therefore records `dns_scope: connection-pinned`,
`proxy_scope: pinned-agent`, and `transport_scope: caller-agent-overridden`; it does not inherit the
Axios path's environment-proxy residual. Three exact IR labels per family cover both local and pinned
edges plus unrelated same-named helpers. Default-off, automatic-redirect, unpinned-agent,
caller-transport, mapped-address, deny-predicate, and broken same-class-flow mutations withhold the
corresponding edge.

Schema v38 resolves Google ADK JS's `LOAD_WEB_PAGE` through its imported `FunctionTool` definition
and exact `execute: ({url}) => loadWebPage(url)` callback. The helper restricts schemes, blocks
localhost names, checks every preflight DNS answer against explicit IPv4/IPv6 non-global ranges,
normalizes IPv4-mapped IPv6, and disables redirects. It then calls unpinned global `fetch`, whose own
connection-time DNS lookup is not tied to the preflight result. The edge therefore records
`dns_scope: preflight-only-rebinding-residual`, `transport_scope: global-fetch-unpinned`, and
`proxy_scope: unresolved`, while preserving `enforcement_default: enabled` and `escape_hatch: none`.
Two positive and one negative IR labels cover the local and pinned paths plus an ordinary same-named
helper; missing imports, fixed inputs, automatic redirects, incomplete address checks, or mapped-IP
bypasses withhold the edge.

Schema v40 adds Activepieces' configured MCP transport as an imported filtering-Axios composition.
The entrypoint passes `tool.serverUrl` into `createMcpClient`; the transport's exact `safeHttp` named
import reaches `safeHttp.axios.request`. The helper forces `RequestFilteringHttpAgent` and
`RequestFilteringHttpsAgent` after caller config, while the nearest package manifest pins
`request-filtering-agent` 3.2.0. Direct IPs and every direct connection-time DNS result are filtered,
with `AP_SSRF_ALLOW_LIST` retaining configured IP/CIDR exceptions. Environment proxy routing can
shift that boundary to the proxy, so the edge records
`dns_scope: connection-time-filtered-unless-proxied`, `proxy_scope: environment-dependent`, and
`transport_scope: imported-axios-client-instance`. Two positive and one negative IR labels cover the
local and pinned paths plus raw Axios; wrong imports, missing manifest proof, unsafe agent ordering,
and caller proxy/agent overrides withhold the edge. The generic same-file Axios-instance syntax is
fixture-validated; the selected corpus contains no matching real same-file instance call.

Schema v41 adds four Composio TypeScript paths through the package-conditional `#ssrf_guard`
import. The Node/default helper validates every DNS answer and bounded manual redirect, then supplies
the validated addresses through an Undici dispatcher's lookup. Caller dispatchers, non-stock global
dispatchers, and `NODE_USE_ENV_PROXY` routing stand down from pinning and retain preflight-only
validation. The edge implementation of `ssrfSafeFetch` fails closed for the caller-selected session
upload URL; the separate `ssrfSafeFetchWhereSupported` export uses raw edge fetch for three
API-response transfer paths. Four positive and one negative IR labels cover local and pinned paths
plus raw fetch. Mutations of the package map, manual redirect, dispatcher pin, import, or edge
fail-closed branch withhold all four edges.

Schema v42 adds Composio CLI's tool-file preprocessing path. The exact
`ToolsExecutor.execute(slug, params)` implementation passes `params.arguments` and the resolved input
schema to `uploadToolInputFiles`. Recursive `file_uploadable` hydration sends HTTP(S) strings through
`readFileFromUrl`, which uses raw global `fetch(url)` rather than the core safe-fetch export. The
engine emits one symbolized tool-to-network edge and one AV-NET001 review at line 146. Two positive
and one negative IR labels cover local, pinned, and raw paths; guarded-fetch, fixed-argument,
schema-gate, and wrong-import mutations withhold the edge.

Schema v43 adds Google ADK JS's generated OpenAPI tool as a fixed-origin counterexample. The exact
toolset/parser/factory chain creates `RestApiTool.runAsync`; model arguments can affect encoded path
segments, query, headers, and body, while `endpoint.baseUrl` comes from the first spec server.
Server variables use declared defaults or enums, dot segments are rejected, and credential handling
only appends query data or headers. The engine emits one symbolized tool-to-network edge and one
`network-origin-policy` edge at line 134, but no AV-NET001 review. Two positive and one negative IR
labels plus six incomplete-composition mutations pin the distinction.

Pinned negatives include a [fixed Devpost origin](https://github.com/microsoft/ai-agents-for-beginners/blob/01777b05e8afeba6bf5a6dbe74cc2293372d3693/11-agentic-protocols/code_samples/github-mcp/app.py#L118),
the MCP SDK's [fixed weather API](https://github.com/modelcontextprotocol/typescript-sdk/blob/3924de99df834302d89f5997a1b64ca268282284/examples/guides/get-started/firstServer.examples.ts#L20-L40),
Vercel's [literal PDF URL](https://github.com/vercel/ai/blob/f607a129c0298870038b398dbcba57ff041114f6/examples/ai-e2e-next/tool/fetch-pdf-tool.ts#L5-L12),
and Qwen's two fixed urllib weather endpoints plus fixed AMap endpoint formatted with a dynamic
query. Python fixed-origin facts propagate
through unique module constants and immutable `self` fields, concatenation, and `.format(...)`.
Results remain `review`: neither the local Python controls, configured-open TypeScript policy,
default-off n8n control, proxy-conditional Flowise control, nor ADK's preflight-only address check
suppresses the rule. Redirect, DNS rebinding, proxy, imported-validator, and runtime-egress state is
kept path-specific rather than treated as universally resolved.

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

## AV-AUDIT001 — durable action record lacks actor attribution

Schema v52 reports one medium-severity, high-confidence production review in Skyvern Task v3. The
exact path executes a billable/recordable [tool handler](https://github.com/Skyvern-AI/skyvern/blob/486c8975e9864a53037d4701b781f8619e698c40/skyvern/forge/taskv3/loop.py#L559),
passes its completed or failed result to the configured callback, and commits an action row. However,
the Task v3 constructor does not populate `created_by`, and the
[`ActionModel` field](https://github.com/Skyvern-AI/skyvern/blob/486c8975e9864a53037d4701b781f8619e698c40/skyvern/forge/sdk/db/models.py#L1157)
is nullable. The row remains correlated to organization, workflow, task, step, action type, status,
and ordering, so this is an actor-attribution gap in a proven durable record—not a claim that logging
is absent.

The rule fires only when an external-action capability has a source-proven durable-action-record edge
whose actor-attribution state is explicitly unresolved. Generic untraced or unrecorded actions and
Google ADK's attributable BigQuery record are regression negatives. Remediation is to populate and
require a non-null authenticated actor identifier before commit while retaining execution correlation
and surfacing failed writes through metrics or alerts.

## Seed truth-set metrics

`benchmarks/truthset.json` contains 342 exact labels across all eleven enabled rules: 186 positives and 156
negatives. Labels mix local fixtures, immutable real positives, and unmatched real corpus observations,
including a CAMEL allowlist, fixed-name MCP, ordinary non-tool filesystem writes, fixed argv and
literal TypeScript shell calls, constant/test-only eval, literal browser evaluation, an ordinary
non-browser `.evaluate(...)` method, non-approval skip flags, disabled
auto-approval, conditional environment guards, late MCP guards, and safe
Compose/Kubernetes/Docker SDK settings. All 342 currently pass; each rule's seed precision and recall
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
finding or trigger `AV-AUDIT001`. The full corpus scan observed seven action-trace controls and five
lexically governed HTTP capability edges, all in that ArcadeAI telemetry example.

Four additional audit labels exercise Google ADK Python's BigQuery Agent Analytics plugin: a local
enabled external action and explicit-disabled counterexample, the pinned Storage Write API edge, and
a pinned `InMemoryRunner` plugin composition. The resolver requires the exact enabled/default plugin,
`Runner` propagation, `PluginManager` callback dispatch, before/after/error tool flow, and
`append_rows` sink. Schema v52 records one available durable control, one audit-storage capability,
two test deployments, two agent-control edges, one storage edge, and zero production deployments or
production external-action control edges. Records are attributable by event, agent, user, session,
invocation, and tool, but delivery is best-effort with drop accounting. This attributable control is
a negative for `AV-AUDIT001`; production deployment, retention, and loss guarantees remain unresolved.

Five Skyvern Task v3 labels add a local governed action, an unrelated untracked negative, and pinned
production action, storage, and agent-control edges. The exact path begins after model-selected
`spec.handler(args)` dispatch, retains billable/recordable completed or failed actions, invokes the
configured round callback, constructs an action with organization/workflow/task/step/order identity,
and commits an `ActionModel` to the SQLAlchemy `actions` table. Schema v52 records one production
deployment, one governed external-action edge, and one storage edge. It remains a
`durable-action-record`, not a fully attributable audit: `created_by` is nullable and unset in this
path, persistence happens after the action, and callback/database failures are contained.
Schema v52 raises one medium-severity, high-confidence `AV-AUDIT001` review at this exact production
action edge. The rule requires a durable-action-record relationship whose actor-attribution state is
explicitly unresolved; it does not infer findings from generic untraced or unrecorded actions. Two
positive and two negative rule labels pin the Skyvern, ADK, and unrelated-action boundaries.

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
control edge. Sixteen Python path-boundary labels cover six local proven sinks, seven local bypasses,
a configured-root edge, and FastMCP's and ChatDev's real control edges. Nineteen Python filesystem-mutation labels
cover nine local positives, seven local rebinding/compatibility negatives, and three pinned
ArcadeAI/CrewAI edges. Four closure-binding labels cover a returned local callback, a rebound negative, browser-use's
registered wrapper, and the Python SDK retry negative. Three method-registry labels cover a local
resolved callee, a fallback negative, and FastMCP's real summary. Five imported-registry labels cover
a local resolved manager, mutable/fallback/rebound negatives, and the pinned MCP Python SDK manager.
Eleven same-class path-helper labels cover the local exact-return edge, seven adversarial negatives,
and OpenAI's three real sinks. Eight path-prefix labels cover two local and four real positive sinks,
plus post-write and separator-aware negatives. Seven Python post-registration labels cover two local
tool edges, one cross-file approval edge, three adversarial negatives, and Skyvern's real filesystem
edge. Six transparent-wrapper labels cover direct, decorator-factory, and two-layer positives plus
metadata-only, branch-only, and deferred-call negatives. Three browser-evaluation labels cover two
exact tool-to-browser-page execution edges and an ordinary-method negative. Thirteen Python
registry-tool labels cover eight exact MetaGPT/Qwen capability edges and five provenance,
entrypoint, or receiver negatives. Eleven imported Python function-network labels cover six exact
tool edges and five nested, module-qualified, or rebound negatives. Fifteen imported class-network
labels cover ten direct/bound/multihop or fixed-field edges and five mutable or ambiguous negatives.
Seven urllib labels cover two local dynamic origins, one local fixed origin, two local binding
negatives, and two pinned Qwen fixed-origin tool edges. Nine Python network-origin-control labels cover
two fail-closed local guards and seven late, partial, continuing, rebound, shadowed, mutable-policy,
or rejection-branch-sink negatives. Seven TypeScript network-origin-policy labels cover the local and
MCP Servers edges plus late, rebound, nested-call, scheme-only, and branch-only negatives. Eight browser-receiver labels cover an
annotated parameter, immutable alias, ordinary-method, reassignment, late/branch alias negatives,
a container annotation negative, and Skyvern's proven factory result. Six secure-network-helper
labels cover two local and two CrewAI edges plus incomplete-redirect and rebound-import negatives.
Five proxy-conditional secure-network labels cover two local and two Composio edges plus an ordinary
request negative. Five configurable pinned-network labels cover two local and two Langflow edges plus
an ordinary request negative. Three TypeScript configurable-composition labels cover local and n8n
edges plus raw Axios. Three Flowise request-object labels and three Flowise `secureFetch` labels each
cover local and pinned governed paths plus an unrelated same-named helper. Three Google ADK labels
cover local and pinned preflight-only paths plus an ordinary same-named helper. Nine A2A endpoint
labels cover two local and two pinned unconstrained TypeScript paths, four guarded ADK Python paths,
and a trusted local-card negative. Five Axios-instance labels cover four direct/request/base-policy
edges and one shadowed-client negative. Three Activepieces filtering-client labels cover the local
and pinned governed paths plus raw Axios. Five Composio conditional-runtime labels cover two local
and two pinned governed paths plus raw fetch. Three Composio CLI upload labels cover the exact local
and pinned schema-driven tool-argument flows plus an unrelated raw fetch. Three Google ADK OpenAPI
labels cover the local and pinned origin locks plus an unrelated raw global fetch. Three OpenAI
Agents Python MCP-approval labels cover the local and pinned disabled defaults plus an unrelated
server helper. Four Google ADK BigQuery audit labels add three positive durable-control/storage edges
and one explicit-disabled negative. Five Skyvern action-history labels add four positive production/
local record edges and one unrelated-action negative. Ten direct-callable labels add the pinned
PydanticAI definition and local same-block positives plus reassigned, cross-branch, parameter, and
forward-reference negatives. Thirteen wrapper labels cover exact local body/approval/Agent edges,
wrong and shadowed factories, reassignment, cross-branch and lambda negatives, and both pinned
OpenAI Agent edges. All 311 IR labels pass:
three approval positives/four negatives,
nine audit/action-record positives/four negatives, two import positives/one negative,
four import-shadow positives/one negative, nine block-dominance positives/two negatives, seven
Python ComputerTool positives/one negative, eight direct-callable positives/two negatives, 12
function-tool-wrapper positives/one negative, three
TypeScript graph
positives/one negative, eight registration positives/one negative, five helper-summary positives/one
negative, 11 path-boundary positives/nine negatives, four path-helper positives/seven negatives,
six path-prefix positives/two negatives,
12 filesystem-mutation positives/seven
negatives, two MCP-registry positives/one negative, three
fixed-instance positives/one negative, two closure positives/two negatives, two method-registry
positives/one negative, four post-registration positives/three negatives, three transparent-wrapper
positives/three negatives, two browser-evaluation positives/one negative, three browser-receiver
positives/five negatives, eight Python registry-tool
positives/five negatives, six Python imported-network positives/five negatives, ten Python
imported-class-network positives/five negatives, five urllib-network positives/two negatives, two
Python network-origin-control positives/seven negatives, two TypeScript network-origin-policy
positives/five negatives, four Python secure-network-helper positives/two negatives, and two
imported-registry positives/three negatives, plus four proxy-conditional secure-network positives/one
negative, plus four configurable pinned-network positives/one negative, plus eight A2A endpoint
provenance positives/one negative, plus two TypeScript
configurable-composition positives/one negative, plus two Flowise request-object positives/one
negative, two Flowise `secureFetch` positives/one negative, two Google ADK fetch positives/one
negative, four Axios-instance positives/one negative, and two Activepieces filtering-client
positives/one negative, plus four Composio conditional-runtime positives/one negative, two Composio
CLI upload positives/one negative, two Google ADK OpenAPI origin-lock positives/one negative, and two
OpenAI Agents Python MCP-approval-default positives/one negative.

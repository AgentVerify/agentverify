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

## Full-corpus engine benchmark

The 2026-08-21 default scan covered 70 source-bearing repositories plus one docs-only upstream
snapshot. It parsed 10,594 selected Python/TypeScript/JavaScript files plus 155 configuration files,
resolved 1,353 relationships, and completed in 29.59 seconds on the development machine. Three parse warnings were isolated and
reported without aborting the run. Tests and fixtures are inventoried but excluded from findings by
default; `--include-tests` enables them. The pinned corpus contains no AgentVerify inline directives,
so the benchmark records zero suppressed findings.

Engine benchmark schema v3 retains stable component-name taxonomies, category presence counts,
matched-versus-identified endpoint counts, and TypeScript graph precision measures. It intentionally
excludes arbitrary agent/tool display names from the summary. The resulting
framework/provider/protocol/capability coverage and unsupported syntax are published in
`docs/frontend-coverage.md`; presence counts are discovery observations, not recall measurements.

The benchmark now also measures identity coverage: 8,204 agent/tool component observations carry
module-qualified IDs. Of 2,706 relationship endpoints, 1,887 carry symbol IDs and 1,885 resolve to an
observed component (1,651 Python and 234 TypeScript). The two unmatched IDs are explicit Python
re-export targets; capability, control, and taxonomy endpoints intentionally remain evidence
observations without source-symbol IDs.

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
and Cline `createTool`. The full sample contains 95 structure-backed agent edges: 14 delegations and
81 tool edges, all with targets that resolve to observed components. The prior token heuristic could
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
candidates. Corpus totals are now 21 `AV-EXEC001` findings and seven `AV-APPROVAL001` reviews.

## AV-MCP002 — dynamic MCP forwarding

The rule requires an MCP import plus a non-literal tool name. A fixed tool name is the negative
regression. The full benchmark reports 43 default-scope forwarding sites across 22 repositories.
Hand-reviewed pinned examples include:

- [CrewAI client](https://github.com/crewAIInc/crewAI/blob/456c67d7c27923ed3c3dca202c6f56651d8e6063/lib/crewai/src/crewai/mcp/client.py#L599)
- [browser-use client](https://github.com/browser-use/browser-use/blob/85ddbfedf609166b2d2c76c3d80506649fee82a9/browser_use/mcp/client.py#L324)
- [Semantic Kernel connector](https://github.com/microsoft/semantic-kernel/blob/b39d95a34435f4c1d55dd00c86120ce118d847e1/python/semantic_kernel/connectors/mcp.py#L618)
- [ChatDev tool manager](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/runtime/node/agent/tool/tool_manager.py#L291)

These are legitimate protocol boundaries in framework code and are therefore `review` results. A
later policy-resolution pass will suppress sites governed by a resolved allowlist rather than
claiming that the forwarding operation itself is unsafe.

That policy pass now handles a same-function `not in` guard followed by `raise`/`return`. Guards are
applied in statement order: a rejection after the forwarding call does not govern the earlier action.
It resolves
and suppresses CAMEL's [registered-tool guard](https://github.com/camel-ai/camel/blob/473388d36390b22e0df31e25b7b2d50db55310d2/camel/utils/mcp_client.py#L1054)
before the dynamic call, while retaining the forwarding capability and a `tool-allowlist` control edge.

## AV-FS001 — dynamic writable tool path

The rule requires a writable dynamic path inside a resolved tool; ordinary application writes and
fixed tool paths do not trigger it. The full benchmark reports 16 default-scope sites across six
repositories. A hand-reviewed case is ArcadeAI's
[local-filesystem MCP `write_file`](https://github.com/ArcadeAI/arcade-ai/blob/597debaa1593b54172061ce36a414cc29aa8fc6a/examples/mcp_servers/local_filesystem/src/local_filesystem/tools.py#L154),
which resolves a caller-provided path before writing. No workspace-root constraint is visible in the
tool function, but the result remains `review` because enclosing server policy is unresolved.

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

`benchmarks/truthset.json` contains 129 exact labels across all seven enabled rules: 73 positives and 56
negatives. Labels mix local fixtures, immutable real positives, and unmatched real corpus observations,
including a CAMEL allowlist, fixed-name MCP, ordinary non-tool filesystem writes, fixed argv and
literal TypeScript shell calls, constant/test-only eval, non-approval skip flags, disabled
auto-approval, late MCP guards, and safe Compose/Kubernetes/Docker SDK settings. All 129 currently pass; each rule's seed precision and
recall are 1.0. Negative labels must retain either an observed Agent IR component anchor or verified
source text at the exact pinned line, preventing a missing or drifting location from passing silently.

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

Three import labels cover a resolved relative fixture, a missing-module negative, and the pinned
CrewAI-LangGraph draft-tool edge. Seven approval labels cover enabled, disabled, callback, and
automatic-handler policies plus pinned Python and TypeScript OpenAI shell edges. Four TypeScript graph
labels cover inline and assigned agent adapters, the Cline tool path, and a nested-token negative. All
18 IR labels pass: three approval positives/four negatives, two audit positives/two negatives, two
import positives/one negative, and three TypeScript graph positives/one negative.

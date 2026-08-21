# Detection validation log

Validation date: 2026-08-21. Repositories are partial checkouts pinned by
`research/repository-data.json`; paths and results can be reproduced from the corpus scripts.

## AV-EXEC001 — dynamic command through system shell

| Repository | Commit | Selected files scanned | Findings | Representative path |
|---|---|---:|---:|---|
| Aider-AI/aider | `5dc9490b` | 152 | 4 | `aider/editor.py:134` |
| bytedance/trae-agent | `e839e559` | 75 | 2 | `trae_agent/tools/bash_tool.py:44` |
| FoundationAgents/MetaGPT | `11cdf466` | 174 | 1 | `metagpt/tools/libs/shell.py:52` |
| SWE-agent/SWE-agent | `3ea751c0` | 102 | 1 | `sweagent/environment/repo.py:115` |

These are pattern detections, not claims that each application is exploitable. Caller provenance,
input constraints, containment, and approval policy determine exploitability. The rule reports the
dangerous execution primitive with high pattern confidence and leaves reachability for graph analysis.

## Regression cases

- `cases/python_dangerous/agent.py`: positive dynamic string plus `shell=True`.
- `examples/safe_agent/agent.py`: negative fixed argv plus default `shell=False`.
- `cases/typescript_mcp`: MCP inventory and approval-bypass candidate.
- `cases/typescript_approved`: literal TypeScript tool approval resolves a governing control, while
  callback and disabled forms remain unresolved.

## Full-corpus engine benchmark

The 2026-08-21 default scan covered 70 source-bearing repositories plus one docs-only upstream
snapshot. It parsed 8,840 selected Python/TypeScript/JavaScript files plus 40 configuration files,
resolved 1,593 relationships, and completed in 19.44 seconds on the development machine. Two syntax warnings were isolated and
reported without aborting the run. Tests and fixtures are inventoried but excluded from findings by
default; `--include-tests` enables them.

The approval-policy resolver found a literal `needsApproval: true` in the pinned OpenAI Agents JS
[human-in-the-loop example](https://github.com/openai/openai-agents-js/blob/0b944370c6fe019ac5b08364ca013826cd7d0668/examples/docs/human-in-the-loop/toolApprovalDefinition.ts#L11)
and attached a tool-to-control edge. The adjacent callback form remains unresolved because its result
depends on invocation arguments.

During validation, import-aware shell resolution reduced Cline's TypeScript dynamic-shell candidates
from 16 to zero after proving the matches were `RegExp.exec()`, not `child_process.exec()`. Truthy
approval-bypass matching plus test-scope filtering reduced Cline approval candidates from 41 to five.
The remaining candidates are explicit policy assignments or an `--auto-approve` path and remain
`review` results rather than confirmed vulnerabilities.

Expanding the truth set exposed two additional false-positive families. Literal TypeScript commands
were incorrectly classified as dynamic; resolving complete string literals removed five corpus
findings while preserving interpolated templates. Broad approval-name matching confused warning-state
and version-check flags with human approval; requiring approval-specific names removed six review
candidates. Corpus totals are now 20 `AV-EXEC001` findings and six `AV-APPROVAL001` reviews.

## AV-MCP002 — dynamic MCP forwarding

The rule requires an MCP import plus a non-literal tool name. A fixed tool name is the negative
regression. The full benchmark reports 36 default-scope forwarding sites across 20 repositories.
Hand-reviewed pinned examples include:

- [CrewAI client](https://github.com/crewAIInc/crewAI/blob/456c67d7c27923ed3c3dca202c6f56651d8e6063/lib/crewai/src/crewai/mcp/client.py#L599)
- [browser-use client](https://github.com/browser-use/browser-use/blob/85ddbfedf609166b2d2c76c3d80506649fee82a9/browser_use/mcp/client.py#L324)
- [Semantic Kernel connector](https://github.com/microsoft/semantic-kernel/blob/b39d95a34435f4c1d55dd00c86120ce118d847e1/python/semantic_kernel/connectors/mcp.py#L618)
- [ChatDev tool manager](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/runtime/node/agent/tool/tool_manager.py#L291)

These are legitimate protocol boundaries in framework code and are therefore `review` results. A
later policy-resolution pass will suppress sites governed by a resolved allowlist rather than
claiming that the forwarding operation itself is unsafe.

That policy pass now handles a same-function `not in` guard followed by `raise`/`return`. It resolves
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

The rule found seven default-scope boundary crossings across six repositories. It reports development
and production configuration alike but retains their source path so policy can distinguish them.
Hand-reviewed examples include:

- [AutoGen devcontainer Docker socket](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/.devcontainer/docker-compose.yml#L11)
- [Langflow deployment Docker socket](https://github.com/langflow-ai/langflow/blob/09ef6b2b7119e35a6787fc249f916f8b47b28615/deploy/docker-compose.yml#L10)
- [Bytebot privileged container](https://github.com/bytebot-ai/bytebot/blob/3d37894ce07ef8d8b40adc7fd309ad96c2a71313/docker/docker-compose.yml#L15)
- [AutoGPT read-only Docker socket mount](https://github.com/Significant-Gravitas/AutoGPT/blob/601093ddfe23a3d58a9c8f4a208bd49b203ee612/autogpt_platform/db/docker/docker-compose.yml#L471)

A read-only Docker socket mount is still reported because the Docker API can create privileged
workloads even when the socket file itself is mounted read-only.

## Seed truth-set metrics

`benchmarks/truthset.json` contains 56 exact labels across all six enabled rules. Labels mix local
positive/negative fixtures, immutable real positives, a real CAMEL allowlist negative, fixed-name MCP,
fixed-path filesystem, fixed-argv and literal TypeScript shell calls, constant-eval, non-approval skip
flags, disabled auto-approval, and commented safe compose cases. All 56 currently pass; each rule's
seed precision and recall are 1.0.

This is a curated regression seed, not an unbiased estimate of ecosystem precision or recall. The
next benchmark milestone is at least 100 independently reviewed labels sampled from unmatched as well
as matched corpus locations.

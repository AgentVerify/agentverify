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

## Full-corpus engine benchmark

The 2026-08-21 default scan covered 70 source-bearing repositories plus one docs-only upstream
snapshot. It parsed 8,840 selected Python/TypeScript/JavaScript files, resolved 1,591 relationships,
and completed in 19.17 seconds on the development machine. Two syntax warnings were isolated and
reported without aborting the run. Tests and fixtures are inventoried but excluded from findings by
default; `--include-tests` enables them.

During validation, import-aware shell resolution reduced Cline's TypeScript dynamic-shell candidates
from 16 to zero after proving the matches were `RegExp.exec()`, not `child_process.exec()`. Truthy
approval-bypass matching plus test-scope filtering reduced Cline approval candidates from 41 to five.
The remaining candidates are explicit policy assignments or an `--auto-approve` path and remain
`review` results rather than confirmed vulnerabilities.

## AV-MCP002 — dynamic MCP forwarding

The rule requires an MCP import plus a non-literal tool name. A fixed tool name is the negative
regression. The full benchmark reports 37 default-scope forwarding sites across 20 repositories.
Hand-reviewed pinned examples include:

- [CrewAI client](https://github.com/crewAIInc/crewAI/blob/456c67d7c27923ed3c3dca202c6f56651d8e6063/lib/crewai/src/crewai/mcp/client.py#L599)
- [browser-use client](https://github.com/browser-use/browser-use/blob/85ddbfedf609166b2d2c76c3d80506649fee82a9/browser_use/mcp/client.py#L324)
- [Semantic Kernel connector](https://github.com/microsoft/semantic-kernel/blob/b39d95a34435f4c1d55dd00c86120ce118d847e1/python/semantic_kernel/connectors/mcp.py#L618)
- [ChatDev tool manager](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/runtime/node/agent/tool/tool_manager.py#L291)

These are legitimate protocol boundaries in framework code and are therefore `review` results. A
later policy-resolution pass will suppress sites governed by a resolved allowlist rather than
claiming that the forwarding operation itself is unsafe.

## AV-FS001 — dynamic writable tool path

The rule requires a writable dynamic path inside a resolved tool; ordinary application writes and
fixed tool paths do not trigger it. The full benchmark reports 16 default-scope sites across six
repositories. A hand-reviewed case is ArcadeAI's
[local-filesystem MCP `write_file`](https://github.com/ArcadeAI/arcade-ai/blob/597debaa1593b54172061ce36a414cc29aa8fc6a/examples/mcp_servers/local_filesystem/src/local_filesystem/tools.py#L154),
which resolves a caller-provided path before writing. No workspace-root constraint is visible in the
tool function, but the result remains `review` because enclosing server policy is unresolved.

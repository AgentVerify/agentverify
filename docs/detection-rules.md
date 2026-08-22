# Detection rule specifications

Rules distinguish facts (`inventory`), review candidates (`warning`), and demonstrated unsafe flows
(`finding`). Absence-based findings are forbidden until the analyzer has sufficient file and config
coverage to justify them.

| ID | Kind | Default severity | Description | Initial evidence |
|---|---|---|---|---|
| AV-AI001 | inventory | info | Identify model provider and model configuration | 44/71 repositories reference multiple providers |
| AV-AG001 | inventory | info | Identify agent framework, agent definitions, handoffs, and graph edges | Framework signatures span 12 families |
| AV-TOOL001 | inventory | info | Enumerate tools and privileged capability classes | 69/71 expose browser/filesystem/code/shell signals |
| AV-MCP001 | inventory | info | Identify MCP clients, servers, transports, commands, URLs, and declared tools | MCP signals in 50/71 |
| AV-EXEC001 | finding | high | Dynamic command executed through a system shell | 21 default-scope engine matches after literal-command and API resolution |
| AV-EXEC002 | finding | high | Dynamic input reaches an evaluator/interpreter | 51 default-scope matches across 15 repositories; browser-page promotion additionally requires a proven receiver |
| AV-APPROVAL001 | review | high | Enabled auto-approve or skip-confirmation path | 15 default-scope engine candidates after semantic-name and approval-flow filtering |
| AV-APPROVAL002 | review | high | Reachable local OpenAI Agents Python/TypeScript shell tool uses the SDK's disabled approval policy | 2 default-scope matches in the pinned SDK examples; schema v64 separately inventories one disabled-default agent→MCP binding without promoting it absent a proven destructive MCP capability |
| AV-APPROVAL003 | finding | high | Reachable local shell or apply-patch tool has a same-file approval callback that transitively returns approval from an environment flag | 3 exact default-scope matches across the pinned OpenAI Agents Python and JavaScript SDK examples |
| AV-FS001 | review | high | Agent tool writes, copies, moves, or deletes a tool-input-controlled filesystem path without a proven narrow path-boundary control | 32 default-scope matches across 9 repositories after literal tool-role recovery and fixed-path filtering; four newly reachable Marvin sinks are pinned |
| AV-FS002 | review | high | Agent tool relies on `str(resolved).startswith(str(root))` as a filesystem boundary check | 4 default-scope matches in CrewAI Examples |
| AV-NET001 | review | high | Agent tool sends an HTTP request to a parameter-controlled origin | 23 default-scope matches across 12 repositories; schema v64 retains five exact Google ADK Python project-local helper paths, Composio CLI's schema-gated URL upload, and proof that Google ADK OpenAPI model arguments cannot replace the spec-configured origin alongside the other exact Python and TypeScript control states |
| AV-A2A001 | review | high | A remotely fetched A2A AgentCard can select a downstream RPC origin without a proven source-origin binding | 2 default-scope matches: Google ADK JS and Gemini CLI; two ADK Python client-construction paths are guarded by all-interface HTTPS/loopback and same-origin validation |
| AV-MCP002 | review | high | Dynamic MCP tool name and arguments are forwarded to a server | 49 default-scope matches across 23 repositories after policy resolution |
| AV-MCP003 | review | high | An MCP server is automatically installed from an unpinned or floating `npx`/`uvx` package reference | 16 default-scope matches across Marvin, Qwen-Agent, Agno, and CAMEL; exact OpenHands pins and non-auto-install `npx` calls remain negative |
| AV-SANDBOX001 | review | high | Container/Kubernetes workload or Docker SDK call exposes a host, privilege, credential, or service-account boundary | 20 matches across 10 repositories; Goose adds an exact read-only host `~/.ssh` bind |
| AV-AUDIT001 | review | medium | Consequential action has a durable record with explicit unresolved actor attribution | 1 production Skyvern Task v3 path; requires an exact durable-action-record edge and nullable/unset actor state, while generic absence and attributable ADK records remain negative |

## Rule contract

Every result must include:

- rule ID, severity, confidence, and result kind;
- source location and a concise explanation tied to code;
- relevant Agent IR path (agent → tool → capability → control);
- what was resolved and what remains unknown;
- remediation appropriate to the detected framework;
- a stable fingerprint for baselining.

## Validation gate

A rule is not enabled by default until it has:

1. A pinned real-repository case showing why the pattern matters.
2. A minimal positive regression case.
3. At least one negative/near-miss regression case.
4. Documented limitations and remediation.
5. A reviewed confidence level; lexical-only absence checks cannot be “high confidence.”

Tests and fixtures are inventoried but excluded from findings by default. Use `--include-tests` when
auditing framework test suites or validating rule behavior.

Inline suppression uses a standalone comment immediately before the finding:
`# agentverify: ignore AV-RULE until 2026-12-31 -- reviewed reason` (or `//` in TypeScript).
Suppressions are exact-rule, single-line, and reason-bearing; reports preserve their source,
rationale, optional ISO expiry, and active/expired/invalid status. Expired and malformed dates never
suppress. CI can require dates with `--require-suppression-expiry`; UTC dates remain active through the
stated day.

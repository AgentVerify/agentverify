# Detection rule specifications

Rules distinguish facts (`inventory`), review candidates (`warning`), and demonstrated unsafe flows
(`finding`). Absence-based findings are forbidden until the analyzer has sufficient file and config
coverage to justify them.

| ID | Kind | Default severity | Description | Initial evidence |
|---|---|---|---|---|
| AV-AI001 | inventory | info | Identify model provider and model configuration | 44/71 repositories reference multiple providers |
| AV-AG001 | inventory | info | Identify agent framework, agent definitions, handoffs, and graph edges | Exact framework signatures cover 25 families |
| AV-TOOL001 | inventory | info | Enumerate tools and privileged capability classes | 69/71 expose browser/filesystem/code/shell signals |
| AV-MCP001 | inventory | info | Identify MCP clients, servers, transports, commands, URLs, and declared tools | MCP signals in 50/71 |
| AV-EXEC001 | finding | high | Dynamic command executed through a system shell | 25 default-scope engine matches after schema v120 resolves Continue CLI's plan-mode Bash tool through a login-shell spawn, schema v119 resolves Letta Code's default Bash tool through an explicit `zsh`/`bash -c` launcher, and schemas v118/v117 resolve Roo Code and Trae Agent command paths |
| AV-EXEC002 | finding | high | Dynamic input reaches an evaluator/interpreter | 51 default-scope matches across 15 repositories; browser-page promotion supports API-specific script arguments for `evaluate`, `evaluate_handle`, `eval_on_selector`, `eval_on_selector_all`, and `evaluate_all` and requires a provenance-backed parameter, constructor/straight-line or all-writes branching lifecycle field or property, local/module page, exact local context-manager yield, unanimous private same-class or same-module helper parameter, immutable alias of an exact imported-class Playwright field, derived Locator, pinned factory receiver, or Skyvern's exact imported-factory wrapper scope, while exact hosted-sandbox `CodeInterpreterTool` assets remain inventory |
| AV-APPROVAL001 | review | high | Enabled auto-approve or skip-confirmation path | 15 default-scope engine candidates after semantic-name, approval-flow, and specialized MCP-sampling filtering |
| AV-APPROVAL002 | review | high | Reachable local agent shell tool has approval disabled or exposes no per-action decision hook | 4 default-scope matches: two OpenAI Agents shell paths plus exact default host-local Bash tools in Trae Agent and Letta Code; Letta's explicit deny and always-ask precedence remain recorded, 5 test-scoped Python `LocalShellTool` assets remain inventory, and unresolved executors are not treated as missing controls |
| AV-APPROVAL003 | finding | high | Reachable local shell or apply-patch tool has a same-file approval callback that transitively returns approval from an environment flag | 3 exact default-scope matches across the pinned OpenAI Agents Python and JavaScript SDK examples |
| AV-APPROVAL004 | review | high | Reachable writable local filesystem MCP server is converted by OpenAI Agents JS with approval disabled by default | 3 exact default-scope matches in the pinned SDK examples; one static read-only tool-filter example and one unbound server remain negative |
| AV-APPROVAL005 | review | high | Reachable Agno filesystem MCP toolkit leaves mutating tools outside its confirmation policy | 2 exact default-scope matches in pinned Agno examples; a static read-only include list remains negative |
| AV-APPROVAL006 | review | high | OpenHands conversation analyzes privileged actions while confirmation remains at the `NeverConfirm` SDK default | 1 exact pinned SDK example; the paired `ConfirmRisky` security example is negative |
| AV-APPROVAL007 | review | high | Reachable command auto-approval allowlist uses raw string-prefix matching without an executable or argument token boundary | 1 exact Roo Code production path; the default prompt state, denylist precedence, command-chain parser, and dangerous-substitution checks remain explicit, while a token-boundary fixture is negative |
| AV-APPROVAL008 | review | high | Selected plan mode discards a shell risk evaluator's approval escalation short of a hard block | 1 exact Continue CLI production path; normal mode still asks, plan mode is non-default, and critical-command blocking remains explicit while high-risk and unknown commands become effective allow decisions |
| AV-APPROVAL009 | review | high | Selected read-oriented mode wildcard-allows unclassified MCP tools | 1 exact Continue CLI production path; normal mode asks and plan mode is non-default, but discovered server tools have no retained read-only/risk classification before `callTool` |
| AV-APPROVAL010 | review | high | Spawned sub-agent loses the parent tool policy and approval callback | 2 exact Cline production paths: VS Code auto-approves an unlisted default-enabled `spawn_agent`, while CLI sandbox mode can approve `spawn_agent`; both reach the local session wrapper that creates child shell/edit tools without forwarding either supported approval input |
| AV-FS001 | review | high | Agent tool writes, copies, moves, or deletes a tool-input-controlled filesystem path without a proven narrow path-boundary control | 39 default-scope matches across 11 repositories; schema v119 adds Letta Code's default Write tool while retaining its cross-agent guard and optional workspace sandbox as compensating controls, schema v117 adds Trae Agent's absolute-only but root-unconstrained default editor, and schema v116 adds six OpenHands file editors |
| AV-FS002 | review | high | Agent tool relies on `str(resolved).startswith(str(root))` as a filesystem boundary check | 4 default-scope matches in CrewAI Examples |
| AV-NET001 | review | high | Agent tool sends an HTTP request to a parameter-controlled origin | 18 default-scope matches across 11 repositories; schema v112 proves five Google ADK Python helper calls use an immutable imported `https://api.github.com` origin, while retaining Composio CLI's schema-gated URL upload and the exact Python and TypeScript control states; exact provider-hosted OpenAI web search remains inventory because no caller-selected origin is proven |
| AV-A2A001 | review | high | A remotely fetched A2A AgentCard can select a downstream RPC origin without a proven source-origin binding | 2 default-scope matches: Google ADK JS and Gemini CLI; two ADK Python client-construction paths are guarded by all-interface HTTPS/loopback and same-origin validation |
| AV-MCP002 | review | high | Dynamic MCP tool name and arguments are forwarded to a server | 49 default-scope matches across 23 repositories after policy resolution |
| AV-MCP003 | review | high | An MCP server is automatically installed from an unpinned or floating `npx`/`uvx` package reference | 34 default-scope matches across Marvin, Qwen-Agent, Agno, CAMEL, and the TypeScript SDK; exact OpenHands pins and non-auto-install `npx` calls remain negative |
| AV-MCP004 | review | high | A reachable Semantic Kernel MCP server can auto-approve its own model-sampling requests | 1 exact default-scope match in the pinned sampling example; six reachable default-denied server bindings remain negative |
| AV-MCP005 | review | high | An MCP client automatically fulfills server sampling requests without a proven user decision | 3 exact default-scope matches across the MCP Python tutorial and TypeScript SDK examples; PydanticAI adds four test-scope SDK-generated model adapters, while the SDK host with full-request confirmation and a token cap remains negative |
| AV-MCP006 | review | high | An MCP client accepts server elicitation without a proven user decision | 3 exact default-scope matches in TypeScript SDK examples; FastMCP adds one test-scope implicit acceptance, while the TypeScript SDK host, FastMCP CLI, and Microsoft Python tutorial preserve direct user decisions |
| AV-MCP007 | review | high | An MCP client asks the user to accept URL elicitation without showing the full target URL | 2 exact default-scope matches in the Microsoft Python tutorial and FastMCP CLI; the TypeScript SDK host displays and validates the complete URL |
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

## Runtime rule catalog

`agentverify rules` is the authoritative discovery surface for enabled reporting rules. It lists
each rule's result kind, default severity, confidence, summary, and baseline remediation. Use
`agentverify rules AV-FS001` for one rule or `agentverify rules --format json` for a stable
schema-versioned payload. `agentverify schema rules` emits the bundled validation contract for that
payload, including the enabled rule-ID enum. The engine checks every emitted finding against the same
catalog, so a call site cannot silently drift to a different kind, severity, or confidence.
Inventory-only IDs in the specification table above are not reporting rules and therefore do not
appear in the runtime catalog or emit policy-counted findings; policy rule filters reject those IDs.
SARIF rule descriptors use the catalog's stable summary, remediation, kind, severity, and confidence
while individual results retain their context-specific messages.

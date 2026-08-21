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
| AV-EXEC002 | finding | high | Dynamic input reaches an evaluator/interpreter | 51 default-scope matches across 15 repositories, including one tool-controlled Playwright evaluator |
| AV-APPROVAL001 | review | high | Enabled auto-approve or skip-confirmation path | 15 default-scope engine candidates after semantic-name and approval-flow filtering |
| AV-APPROVAL002 | review | high | Reachable local OpenAI Agents Python/TypeScript shell tool uses the SDK's disabled approval policy | 2 default-scope matches in the pinned SDK examples |
| AV-FS001 | review | high | Agent tool writes, copies, moves, or deletes a tool-input-controlled filesystem path without a proven narrow path-boundary control | 26 default-scope matches across 9 repositories after Python registry-decorator recovery and fixed-path filtering |
| AV-FS002 | review | high | Agent tool relies on `str(resolved).startswith(str(root))` as a filesystem boundary check | 4 default-scope matches in CrewAI Examples |
| AV-NET001 | review | high | Agent tool sends an HTTP request to a parameter-controlled origin | 9 default-scope matches across 7 repositories, including two exact imported-helper flows |
| AV-MCP002 | review | high | Dynamic MCP tool name and arguments are forwarded to a server | 49 default-scope matches across 23 repositories after policy resolution |
| AV-SANDBOX001 | review | high | Container/Kubernetes workload or Docker SDK call exposes a host, privilege, or service-account boundary | 19 matches across 9 repositories |
| AV-AUDIT001 | warning | medium | Consequential action has no attributable durable audit edge | Requires action-level data flow |

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

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
| AV-EXEC001 | finding | high | Dynamic command executed through a system shell | 20 default-scope engine matches after literal-command resolution |
| AV-EXEC002 | finding | high | Dynamic input reaches an evaluator/interpreter | 43 repositories have code-execution signals |
| AV-APPROVAL001 | review | high | Enabled auto-approve or skip-confirmation path | 7 default-scope engine candidates after semantic-name filtering |
| AV-APPROVAL002 | finding | high | Reachable destructive action has no governing approval edge | Requires graph/config resolution |
| AV-FS001 | review | high | Agent tool writes to a dynamic filesystem path | 16 default-scope matches across 6 repositories |
| AV-MCP002 | review | high | Dynamic MCP tool name and arguments are forwarded to a server | 43 default-scope matches across 22 repositories after policy resolution |
| AV-SANDBOX001 | review | high | Container/Kubernetes workload exposes a host, privilege, or service-account boundary | 9 matches across 7 repositories |
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
`# agentverify: ignore AV-RULE -- reviewed reason` (or `//` in TypeScript). Suppressions are exact-rule,
single-line, and reason-bearing; reports preserve their source and rationale for auditability.

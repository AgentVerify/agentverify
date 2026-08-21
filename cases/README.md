# Cases

Small cases preserve detection behavior independently of framework installation. Source is parsed but
never imported or executed.

- `python_dangerous`: OpenAI Agents SDK inventory plus `AV-EXEC001`.
- `typescript_mcp`: OpenAI Agents SDK, MCP client/server inventory, plus `AV-APPROVAL001`.
- `python_approved`: privileged tool with a resolved human-approval control edge.
- `typescript_approved`: literal per-tool approval plus unresolved conditional/disabled forms.
- `python_auto_approval`: Python truthy auto-approval review candidate.
- `model_providers`: Anthropic and Azure OpenAI provider/model attribution.
- `mcp_forwarder`: dynamic MCP forwarding positive case plus fixed-tool negative case.
- `external_actions`: browser, network, and consequential external-action graph inventory.
- `typescript_eval`: TypeScript dynamic evaluation with a resolved agent/tool path.
- `filesystem_scope`: dynamic writable tool path plus fixed-path negative case.
- `network_dynamic_origin`: parameter-controlled Requests and import-proven urllib origins, urllib
  `Request` objects, fixed-origin inventory, shadowed/rebound opener negatives, and exact fail-closed
  scheme/hostname controls versus late, partial, continuing, rebound, shadowed, mutable-policy, and
  rejection-branch-sink non-controls.
- `typescript_network_origin_policy`: same-file URL validation with an always-on scheme set and an
  optional environment-backed hostname list whose empty default remains open; late, rebound, nested,
  scheme-only, and branch-only paths do not acquire the policy edge.
- `sandbox_boundary`: Compose and Kubernetes host/privilege boundaries plus explicit safe negatives.
- `constant_eval`: constant Python evaluation negative case.
- `python_browser_evaluate`: exact Playwright `Page` annotations and immutable aliases prove dynamic
  receivers; ordinary same-module `.evaluate(...)` methods and reassigned pages remain negative.
- `approval_safe`: disabled auto-approval negative case.
- `test_scope`: findings are suppressed by default and enabled with `--include-tests`.
- `symbol_collision`: same-named cross-file tools cannot leak agents or controls into a finding.
- `imported_tool`: a local Python import resolves an agent to a tool defined in another module.
- `imported_ts_tool`: a relative TypeScript import resolves an aliased tool across modules.
- `typescript_tool_registrations`: import-aware Mastra object-property tools and MCP `registerTool` callbacks.
- `typescript_helper_summary`: same-file network helper flow, fixed-host negative, and regex-literal masking.
- `typescript_path_boundary`: imported normalized-root validator control and name-only weak-guard negative.
- `../examples/safe_agent`: near-miss showing fixed argv is inventory-only.

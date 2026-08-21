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
- `sandbox_boundary`: four unsafe container boundaries plus a safe compose negative case.
- `constant_eval`: constant Python evaluation negative case.
- `approval_safe`: disabled auto-approval negative case.
- `test_scope`: findings are suppressed by default and enabled with `--include-tests`.
- `symbol_collision`: same-named cross-file tools cannot leak agents or controls into a finding.
- `imported_tool`: a local Python import resolves an agent to a tool defined in another module.
- `imported_ts_tool`: a relative TypeScript import resolves an aliased tool across modules.
- `../examples/safe_agent`: near-miss showing fixed argv is inventory-only.

# Cases

Small cases preserve detection behavior independently of framework installation. Source is parsed but
never imported or executed.

- `python_dangerous`: OpenAI Agents SDK inventory plus `AV-EXEC001`.
- `typescript_mcp`: OpenAI Agents SDK, MCP client/server inventory, plus `AV-APPROVAL001`.
- `python_approved`: privileged tool with a resolved human-approval control edge.
- `typescript_approved`: literal per-tool approval plus unresolved conditional/disabled forms.
- `python_auto_approval`: Python truthy auto-approval review candidate.
- `model_providers`: Anthropic and Azure OpenAI provider/model attribution.
- `framework_provider_taxonomy`: exact frontend-specific framework and provider imports, Gemini and
  Bedrock proof, Vercel AI SDK TypeScript subpaths, import-proven Mistral/Groq/Cohere/Ollama calls and
  literal models, official TypeScript AI SDK factories and dynamic imports, plus rebinding,
  near-name, and unrelated-service negatives.
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
- `python_secure_network_helper`: source-proven imported HTTP transport that validates initial and
  redirect origins, rejects private peers and proxies, and preserves explicit opt-out configuration;
  incomplete redirect validation and rebound imports remain negative.
- `python_proxy_conditional_network_helper`: source-proven direct and redirecting transports that
  pin direct sockets but preserve environment/caller proxy DNS as a residual; fixed validation,
  detached DNS, missing peer/proxy flow, unbounded redirects, and ordinary requests stay negative.
- `python_configurable_network_helper`: default-on connector validation, configured allowlists and
  loopback exemptions, enforcement-conditional DNS pinning/proxy rejection, and redirect policy;
  disabled defaults, unpinned transports, and ordinary requests remain negative.
- `typescript_configurable_ssrf_composition`: default-off service-versus-passthrough composition
  propagated into an Axios-backed tool with bounded redirect hooks and a custom lookup; composition,
  lookup, redirect, and raw-Axios near misses remain negative, while a literal default-on mutation
  changes the recorded enforcement state.
- `typescript_flowise_secure_request`: variable Flowise node URLs reach either a fixed Axios request
  object with proxy-conditional pinning or `secureFetch` with a post-spread pinned agent; both helpers
  are default-on, normalize mapped IPv6, and validate every redirect hop.
- `typescript_google_adk_secure_fetch`: Google ADK's `FunctionTool` validates a model URL and every
  preflight DNS answer before unpinned global `fetch`; redirects are disabled and the DNS-rebinding
  residual remains explicit.
- `typescript_axios_instance`: immutable same-file Axios instances preserve direct verb and
  `.request(...)` origin flow, including fixed-base and `allowAbsoluteUrls: false` negatives;
  shadowed local clients and no-base instances remain distinct.
- `typescript_activepieces_safe_http`: Activepieces' imported `safeHttp.axios` client composes both
  request-filtering agents after caller configuration, a pinned filtering-library version, and MCP
  transport propagation; import, ordering, manifest, and caller-override mutations withhold the edge.
- `typescript_composio_ssrf_safe_fetch`: Composio's imported Undici-backed guard validates every
  redirect and pins direct connections while retaining configured-route residuals; edge-runtime
  fail-closed and intentionally unguarded fallback exports remain distinct.
- `typescript_composio_cli_upload`: Composio's schema-gated tool arguments recursively reach raw
  global fetch for URL file uploads; guarded transport, fixed arguments, broken schema gates, and
  wrong imports withhold the path.
- `typescript_google_adk_openapi_rest_tool`: Google ADK's generated OpenAPI tool keeps model path,
  query, header, and body values off the spec-configured origin; segment encoding, dot-segment
  rejection, server-variable defaults, query-only credential mutation, and factory provenance are
  required for the control edge.
- `python_openai_mcp_approval_default`: OpenAI Agents Python propagates the absent
  `MCPServerStdio.require_approval` argument through its disabled SDK default into every discovered
  MCP `FunctionTool`; explicit approval and broken import/binding/default propagation stay negative.
- `typescript_openai_mcp_approval`: OpenAI Agents TypeScript converts writable local filesystem MCP
  tools into reachable function tools whose omitted approval policy defaults to disabled; an exact
  static read-only tool filter, unbound server, unrelated imports, and rebound constructors remain
  negative.
- `python_agno_mcp_confirmation`: Agno maps `requires_confirmation_tools` into each discovered MCP
  function while defaulting the list to empty; direct and session-backed filesystem servers retain
  writable tools, while a static read-only include list, complete mutation confirmation, dynamic
  policy, disconnected session, unbound toolkit, and wrong imports remain conservative
  counterexamples.
- `python_semantic_kernel_mcp_sampling`: Semantic Kernel MCP plugins expose server-originated model
  sampling through an exact Agent binding. Explicit auto-approval is reviewable; default/explicit
  denial, callback-controlled and dynamic policies, disconnected plugins, wrong imports, and changed
  SDK propagation remain distinct counterexamples.
- `mcp_sampling_consent`: exact Python `ClientSession` callbacks, TypeScript MCP client request
  handlers, and PydanticAI `MCPToolset(sampling_model=...)` adapters distinguish automatic sampling
  fulfilment from fail-closed interactive consent, denial, unresolved callbacks, token caps, late
  confirmation, conflicting handlers, disabled models, conditional or reassigned imports, missing capability
  declarations, disconnected receivers, and unrelated imports.
- `mcp_elicitation_consent`: exact Python `ClientSession` callbacks, TypeScript MCP client request
  handlers, and FastMCP `Client(elicitation_handler=...)` adapters distinguish automatic elicitation
  acceptance from user-mediated acceptance, decline-only and unresolved handlers, missing capability
  declarations, disconnected or reassigned receivers, rebound response factories, unreturned or
  nested action objects, full-URL versus message-only disclosure, and unrelated imports.
- `python_google_adk_bigquery_audit`: Google ADK Runner composition attaches its default-enabled
  BigQuery analytics plugin to one tool action while retaining an explicit disabled near miss.
- `python_skyvern_action_history`: Skyvern Task v3 records post-dispatch browser actions in a
  committed SQLAlchemy table while preserving best-effort delivery and unresolved actor attribution.
- `python_import_shadowing`: a package import remains available for direct use while function
  parameters and assignments with the same name retain local, unresolved identity.
- `python_block_dominance`: repeated agent bindings resolve only when an exact constructor assignment
  is the sole same-block mutation before use; local block definitions override broader lexical/module
  candidates, while cross-branch and reassigned bindings stay unresolved.
- `python_computer_tool`: import-proven OpenAI Agents `ComputerTool` constructors produce
  computer-control inventory and exact inline/repeated-binding agent edges; an unimported lookalike
  stays ignored.
- `python_direct_callable_tool`: a sole same-block Python function passed through a literal Agent
  tools list becomes an analyzed tool asset; reassigned, cross-branch, forward, and parameter
  forms—including a parameter shadowing a unique module tool—remain unresolved.
- `python_function_tool_wrapper`: import-proven OpenAI `function_tool(function)` assignments retain
  the wrapped body, approval, and Agent identity; wrong/shadowed factories, reassigned bindings,
  cross-branch definitions, lambdas, and multiply wrapped functions remain unresolved.
- `python_agent_helper_return`: exact same-class helpers propagate a direct or tuple-returned Agent
  into Crew composition; conditional, reassigned, transformed, cross-branch, rebound-helper, and
  external-receiver flows remain unresolved.
- `python_typed_tool_parameter`: an import-proven OpenAI built-in tool annotation plus unanimous
  same-module positional, keyword, and inline constructor call sites creates an exact parameter
  binding; mismatched, reassigned, uncalled, rebound/import-redefined, class-body or nested-scope
  shadowed, union-typed, and wrong-annotation forms remain unresolved.
- `typescript_a2a_card_endpoint`: ADK JS and Gemini compositions preserve remotely supplied
  AgentCard authority at SDK client construction; fixed/local cards, wrong imports, and unproven
  transports stay negative.
- `python_a2a_card_endpoint`: both ADK client-construction paths are governed by all-interface
  HTTPS/loopback and same-origin validation; incomplete predicates withhold the control.
- `sandbox_boundary`: Compose and Kubernetes host/privilege boundaries, exact host credential bind
  mounts, named-volume/near-name negatives, and literal privileged Docker SDK calls.
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

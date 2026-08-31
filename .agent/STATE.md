# AgentVerify state

## Current milestone

CI and integration polish on top of the schema-backed report, policy, baseline, SARIF, and rule
catalog workflows.

## Completed recently

- Extended TypeScript OpenAI Agents JS tool-guardrail reject-condition metadata through exact
  same-file helper predicates. Unique helper functions that return literal string checks can now
  annotate guarded `if (helper(...)) return rejectContent(...)` branches with
  `guardrail_reject_condition_helpers` plus inherited literal/source metadata, and that metadata
  propagates through tool and Agent governance edges. Focused
  `IR-TS-OPENAI-TOOL-GUARDRAILS` labels pass 47/47, the full reporting truth set passes 733/733,
  the full public IR truth set passes 2,569/2,569, and benchmark verification passes 3,302/3,302
  combined public-regression labels.
- Extended TypeScript OpenAI Agents JS tool-guardrail governance across imported guarded
  `tool(...)` bindings. Agents that attach a proven imported tool now receive exact `governed-by`
  edges to the producer-file `tool-guardrail-policy` controls via the existing Agent-to-tool
  relationship and the tool control's stable source-tool id, preserving `via_tool_id`, guardrail
  source/name/action/reject-condition metadata, and producer control path/line. Focused
  `IR-TS-OPENAI-TOOL-GUARDRAILS` labels passed 44/44 before the later helper-predicate expansion;
  the current aggregate public-regression counts are recorded in the latest entry above.
- Extended OpenAI Agents Python `ComputerTool(on_safety_check=...)` inventory with exact
  non-acknowledgement metadata for boolean callbacks. Inline `lambda ...: False` and scope-proven
  same-file callbacks ending in a single `return False` now record
  `safety_check_policy: acknowledge-none` / `safety_check_decision: return-false` and remain
  `AV-APPROVAL011` non-findings, while exact `return True` auto-acknowledgement paths still report.
  Focused `AV-APPROVAL011` labels pass 13/13, focused `IR-APPROVAL-CONTROL` labels pass 140/140,
  and the current aggregate public-regression counts are recorded in the latest entry above.
- Extended exact TypeScript OpenAI Agents JS Codex extension tool inventory through relative
  imported `codexTool({...})` bindings from sibling modules, including exact named local reexports
  and unambiguous star reexports. Imported Codex tools now preserve producer-file tool/control
  identity, consumer Agent-to-tool edges, thread-option governance metadata, and binding-source
  resolution, while ambiguous two-source star barrels remain unresolved. Focused Codex-tool labels
  pass 38/38; the current aggregate public-regression counts are recorded in the safety-check entry
  below.
- Extended TypeScript OpenAI Agents JS `computerTool({ onSafetyCheck })` inventory with exact
  empty-acknowledgement metadata. Callbacks that return `[]` or
  `pendingSafetyChecks.slice(0, 0)` through an SDK acknowledgement field now record
  `safety_check_policy: acknowledge-none` and stay outside `AV-APPROVAL011`, while auto-ack paths
  remain reportable. Focused `AV-APPROVAL011` labels pass 11/11, focused
  `IR-APPROVAL-CONTROL` labels pass 138/138, the full reporting truth set passes 731/731, the full
  public IR truth set passes 2,560/2,560, and benchmark verification passes 3,291/3,291 combined
  public-regression labels.
- Extended exact TypeScript OpenAI RealtimeSession output-guardrail inventory through relative
  imported typed `RealtimeOutputGuardrail[]` arrays, including exact named local reexports used
  directly or through exact typed `RealtimeSessionOptions` spreads. Imported Realtime guardrails now
  preserve names, literal/dynamic `tripwireTriggered` metadata, debounce settings from spread
  options, and source-agent governance edges; ambiguous two-source star barrels remain binding-only.
  Focused Realtime guardrail labels pass 25/25; the current public IR aggregate is recorded in the
  latest entry above.
- Extended exact TypeScript OpenAI Agents SDK tool guardrail inventory through relative imported
  typed `ToolInputGuardrailDefinition[]` / `ToolOutputGuardrailDefinition[]` arrays, including exact
  named local reexports. Imported tool guardrail controls now preserve literal names, allow/reject
  action metadata, shallow reject-condition literals, tool governance edges, and Agent-to-tool
  guardrail bridge edges; ambiguous two-source barrels remain binding-only. The latest tool
  guardrail aggregate is recorded in the imported guarded-tool entry above.
- Extended exact TypeScript OpenAI Agents SDK Agent guardrail inventory through relative imported
  typed `InputGuardrail[]` / `OutputGuardrail[]` const arrays, including exact named local
  reexports. Imported guardrail controls now preserve literal names and `tripwireTriggered`
  source counts on both the control and agent governance edge, while ambiguous two-source star
  barrels remain binding-only. The local guardrail fixture now covers direct import, named
  reexport, and ambiguous barrel negatives; focused guardrail labels pass 49/49, the full public
  IR truth set passes 2,528/2,528, and benchmark verification confirms the refreshed digest.
- Added opt-in source-validated scanner IR caching to `scripts/evaluate_truthset.py` via
  `--scan-cache-dir`. Cache entries are keyed by target, selected-path scope, scanned source-file
  digest, and AgentVerify package source digest, then rehydrate `RepositoryIR` from JSON only when
  those values still match. This supports repeated local truth-set runs with repository-wide
  semantics instead of weakening evidence with selected-path scans. A real two-pass
  `IR-TS-TOOL-GRAPH` smoke showed the first full-scan cache fill as misses and the second pass as
  cache hits under ~0.05 seconds per target, with identical result JSON except `generated_at`.
  Summary-format output now includes aggregate cache hit/miss counts; a focused Vercel/local
  two-target smoke printed `hit=0 miss=2` on fill and `hit=2 miss=0` on reuse.
- Added `scripts/evaluate_truthset.py --expand-local-imports` as an opt-in companion to
  `--scan-label-paths` for focused public-IR development scans. The evaluator now expands selected
  label files through local Python imports and TypeScript/JavaScript import, export, dynamic
  import, and `require(...)` edges, records `benchmark.scan_path_expansion:
  local-import-closure`, and `agentverify benchmark verify` surfaces that metadata in verifier
  output. A real focused `IR-TS-TOOL-GRAPH` run passed 16/16 labels in about 0.4 seconds of timed
  scan work, covering cross-file helper/reexport dependencies that plain selected-path scans missed.
  Full release claims still require repository-wide benchmark commands.
- Added `scripts/evaluate_truthset.py --format summary` for compact evaluator stdout while still
  writing the full benchmark-result JSON artifact selected by `--output`. The real expanded
  selected-path `IR-TS-TOOL-GRAPH` smoke prints a short 16/16 pass summary; a full public IR
  expanded selected-path profiling run passed 2,350/2,522 labels and narrowed the remaining misses
  to architecture slices whose evidence spans non-import-neighbor sidecar files or scanner-wide
  summaries, especially Cline subagent approval, Letta default tools, Continue plan approval, Roo
  command approval, and several Python MCP/helper callback families.
- Added `agentverify schema editor-diagnostics`, a bundled JSON schema for LSP-style editor
  diagnostic adapter payloads derived from AgentVerify JSON reports. `agentverify contracts` now
  exports `agentverify-editor-diagnostics-v1.schema.json` as a required contract artifact and
  verifies its schema validity before consumers load copied bundles. The existing plain and
  policy-aware editor diagnostic examples now validate against this schema, and wheel/source
  distribution verification requires the new schema.
- Added a checked policy-aware editor diagnostics example derived from
  `agentverify scan cases/approval_callback_bypass --policy examples/repository-policy.json --format json`.
  The fixture shows how editor/review-bot integrations can join ordinary LSP-style diagnostics to
  `policy_summary.gates[].matched_fingerprints`, adding per-diagnostic `policy_gate_ids` and
  top-level `policy_groups` without duplicating finding bodies. Tests regenerate the fixture from
  the scanner and policy evaluator, and source-distribution verification now requires it.
- Added `agentverify contracts --verify-dir ... --format summary` for compact human-facing editor
  contract verification logs while keeping JSON as the default machine-readable verifier artifact.
  The copyable GitHub editor-contract workflow now writes
  `agentverify-editor-contract-verification.json`, prints the compact summary, validates both
  manifest/verifier JSON files against bundled schemas, and distribution checks require the summary
  step so packaged examples stay tied to the CLI contract.
- Hardened the copyable GitHub Actions policy gate so it validates `agentverify-policy.json` against
  a committed local digest trust root (`agentverify-policy-trust-root.json`) with
  `--require-trusted` before scanning. Policy docs now tell users to generate and commit the trust
  root after finalizing composed policy inputs, and source-distribution checks require the workflow's
  trusted-policy fragments. The checked example trust root is now regression-tested against a fresh
  `agentverify policy examples/repository-policy.json --export-trust-root` export so policy edits
  cannot silently leave stale example digests.
- Strengthened `agentverify benchmark verify-engine` so it now recomputes flat detector metric
  summaries from successful repository entries, then generalized the verifier to
  discover and recompute every flat summary metric field represented by per-repository entries. The
  checked verification output now lists 606 aggregate fields instead of only the 12 core
  file/relationship totals, including OpenAI streaming-run/Codex-tool slices and reporting-rule
  finding counts; CLI tests cover metric-summary drift. Added
  `agentverify benchmark verify-engine --format summary` and
  `agentverify benchmark verify --format summary` for compact human-facing CI logs while the
  defaults remain JSON for release artifacts.
- Exposed OpenAI Agents JS Codex extension tool inventory as a first-class engine benchmark metric.
  The 71-repository snapshot still passes 71/71 repositories with 2,975 relationships / 10,848
  symbolized components, and now includes `typescript_openai_codex_tool`: eight Codex-specific
  components from one repository, including four `Codex tool` components, four policy controls,
  three explicit `approvalPolicy: "never"` controls, one default thread-options control without an
  explicit approval policy, four agent-tool edges, and four configured-by edges. The slice also
  counts workspace-write sandbox, network/web-search, stream callback, run-context thread reuse,
  and literal/binding working-directory evidence so stale Codex scanner snapshots are caught by
  benchmark tests.
- Added exact OpenAI Agents JS streaming-run IR for literal `stream: true` on source-proven direct
  `run(agent, input, {...})` calls and stable `Runner.run(agent, input, {...})` calls. The new
  `streaming-run` control records streaming runtime mode and event-surface scope without treating
  streaming as durable audit proof. Eight labels under `IR-TS-OPENAI-RUN-STREAMING` pass from the
  local conversation fixture and the pinned hosted MCP human-in-the-loop example; the refreshed
  71-repository engine benchmark records
  2,975 relationships / 10,848 symbolized components. The benchmark summary now includes a
  first-class `typescript_openai_run_streaming` slice with 17 controls: 11 direct `run(...)`,
  six stable `Runner.run(...)`, and 17 configured-by edges in one repository.
- Added exact OpenAI Agents JS Codex extension tool IR for `codexTool(...)` when a source-proven
  `@openai/agents` `Agent` includes either a stable same-file Codex tool binding or an inline
  `codexTool({...})` call in its literal `tools` array. The scanner records workspace-write
  sandbox mode, default Codex thread model/reasoning, `approvalPolicy: "never"`, network/web-search
  toggles, stream callbacks, run-context thread reuse, top-level or default-thread working-directory
  values including shorthand bindings, and default thread options without explicit approval policy.
  Mutated tool bindings are not treated as executable agent tools. This same-file/inline slice was
  later extended with imported/reexported Codex bindings; see the current Codex entry above for the
  latest public-IR counts.
- Added exact Vercel `WorkflowAgent` framework-runtime approval IR for the pinned
  `packages/workflow/src/workflow-agent.ts` implementation: the scanner records the
  `tool.needsApproval` run-loop policy, writable-stream `tool-approval-request` chunk format, and
  approval-response continuation path that revalidates through `validateApprovedToolApprovals(...)`
  before approved execution or `execution-denied` results. Seven real labels under
  `IR-APPROVAL-CONTROL` passed in the then-current public IR refresh, and the then-current
  71-repository engine benchmark recorded 2,958 relationships / 10,831 symbolized components.
- Extended exact Vercel `WorkflowAgent` observability IR from constructor options to same-file
  `agent.stream({ ... })` telemetry and callback options when the agent binding is source-proven
  and unreassigned before the stream call. The pinned Vercel AI `telemetry-agent.ts` stream
  `telemetry: createTelemetryOptions(...)` and `onError: recordCallback(...)` call-site now add
  four public labels, so `IR-TS-WORKFLOW-AGENT-OBSERVABILITY` passes 10/10 and the public IR truth
  set stayed green after refresh. During the schema-v159 engine refresh, TypeScript imported-binding
  shadow checks were bulked across local object/tool/model/function/provider resolvers so
  import-heavy files do not rerun whole-file regex scans per local import.
- Added exact Vercel `WorkflowAgent` observability IR for constructor-level `telemetry` options and
  lifecycle/tool callback properties on source-proven `@ai-sdk/workflow` agents. The new controls
  are linked back to the source agent and intentionally represent instrumentation-hook inventory,
  not durable audit completeness. Six real Vercel labels under
  `IR-TS-WORKFLOW-AGENT-OBSERVABILITY` passed before the stream-call extension. The full
  71-repository schema-v159 engine benchmark was refreshed.
- Accepted narrow trailing TypeScript `as` / `satisfies` assertions after exact AI SDK provider
  model calls for Vercel `WorkflowAgent.model` detection. Direct model properties, same-file const
  bindings, imported bindings, and exact reexports now preserve exact model attribution through
  static-only type assertion suffixes, while mutated and ambiguous bindings remain unresolved.
  Focused `IR-TS-WORKFLOW-AGENT-MODEL` labels pass 17/17, and the public IR truth set now passes
  2,472/2,472 labels.
- Extended imported Vercel `WorkflowAgent.tools` execute-helper capability propagation through
  exact named reexports and unambiguous star reexports of stable helper functions. Ambiguous
  reexport barrels stay unresolved. Focused `IR-TS-TOOL-GRAPH` labels pass 16/16, and the public IR
  truth set now passes 2,470/2,470 labels.
- Added evaluator regression coverage for dependency-aware `--scan-label-paths` expansion through
  AgentVerify symbol IDs. Focused benchmark development scans now explicitly cover cross-file
  relationship/component labels whose evidence path differs from the source component path, matching
  the imported WorkflowAgent execute-helper benchmark shape.
- Added conservative cross-file TypeScript Vercel `WorkflowAgent.tools` capability propagation for
  direct relative named imports of stable exported `execute` helper functions. Exactly one object
  tool using an imported helper now gets concrete code-execution/shell/filesystem/network
  capability evidence from the helper body; shared imported helpers remain unlinked. The public IR
  truth set now passes 2,470/2,470 labels.
- Extended exact Vercel AI `WorkflowAgent.model` provenance through stable same-file const bindings
  and imported sibling model bindings when the initializer is exactly one immutable AI SDK provider
  model call. Same-file bindings, direct relative named imports, exact named reexports, and
  unambiguous star reexports now emit source-agent-linked `model-settings-policy` controls; casted,
  mutated, wrapped, and ambiguous forms stay unresolved. The public IR truth set now passes
  2,470/2,470 labels.
- Added per-result `all_labels_passed` to benchmark verifier output entries, regenerated the checked
  `examples/benchmark-verification.json` artifact, and updated release/docs guidance so multi-result
  release tooling can inspect each result file without re-deriving the all-pass state from counts.
- Added a copyable `examples/github-editor-contracts.yml` workflow for editor/review-bot
  integrations. It exports editor contracts from the installed CLI, validates the manifest and
  verification JSON against bundled schemas, verifies the copied bundle before upload, and ships as a
  source-distribution-required workflow with regression tests for read-only permissions and required
  command fragments.
- Added optional top-level `all_labels_passed` to benchmark-result artifacts emitted by
  `scripts/evaluate_truthset.py` and accepted by the bundled benchmark-result schema. The verifier
  recomputes the boolean when present, so stale all-pass claims fail release checks without making
  older external benchmark-result files invalid. Checked rule and IR result artifacts were
  regenerated and passed the then-current public-regression labels.
- Extended exact TypeScript OpenAI Agents SDK `Agent.clone(...)` source lineage through relative
  named and star reexports of exported OpenAI `Agent` bindings. Clone sources reached through
  barrels keep the original source-agent ID, ambiguous/conflicting reexports remain unresolved, and
  RealtimeAgent imports are no longer marked as OpenAI clone sources. The local imported-clone case
  now covers direct import, named reexport, star reexport, ambiguous reexport, and lookalike clone
  negatives; the refreshed public IR truth set passed 2,451/2,451 labels.
- Added conservative cross-file TypeScript Vercel `WorkflowAgent.tools` edges for direct relative
  named imports, exact named reexports, and unambiguous star reexports of immutable exported
  tool-set objects. Imported tool-set entries now resolve to their original sibling-module
  object-tool component IDs when every entry is a concrete object tool, while duplicate tool
  identities, shadowed imports, conflicting reexports, reassigned bindings, and property-mutated
  local tool sets remain unresolved. Focused scanner tests cover imported and barrel-reexported
  `workflowTools` plus helper-mapped code-execution evidence; the pinned corpus does not yet contain
  a real cross-file `WorkflowAgent` fixture, so benchmark claims remain unchanged.
- Extended source-distribution engine-results validation to recompute the same stable integer
  aggregate totals as `agentverify benchmark verify-engine`, so a packaged
  `benchmarks/engine-results.json` fails release verification even when it is schema-valid but has
  stale summary counts.
- Strengthened `agentverify benchmark verify-engine` from repository-count checks to recomputing
  stable integer summary totals from repository entries, including scanned files, dependency/config
  files, relationships, symbol endpoints, resolved import edges, parse warnings, and suppressed
  findings. The schema-backed checked example now records the exact aggregate fields verified.
- Added a checked `examples/engine-results-verification.json` artifact generated by
  `agentverify benchmark verify-engine`, required it in source-distribution verification, and linked
  it from README/release checklist as a fixture for downstream release tooling.
- Added installed CLI verification for engine benchmark snapshots:
  `agentverify benchmark verify-engine` validates `benchmarks/engine-results.json` against the
  bundled schema and checks that core summary totals match the packaged repository entries. The
  verifier emits schema-backed JSON via `agentverify schema
  engine-results-verification`, runs in default CI and the copyable benchmark-verification workflow,
  and fresh wheel/sdist smoke verification passed with 17 bundled schemas.
- Extended installed-wheel smoke verification to validate the checked
  `benchmarks/engine-results.json` snapshot against the installed `engine-results` schema. The
  smoke payload now reports `engine_results_snapshot_valid`, and a fresh wheel/sdist verification
  passed with the value set to true.
- Extended source-distribution verification from presence checks to content validation for
  `benchmarks/engine-results.json`: release archives must now include the source copy of the
  engine-results schema and the verifier validates the packaged snapshot against it. Distribution
  tests cover the valid checked snapshot path and a malformed missing-repositories archive.
- Added generator-side validation for `scripts/benchmark_engine.py`: every generated
  engine-results payload is validated against the bundled `agentverify schema engine-results`
  contract before it is written. Unit tests cover both the checked 71-repository snapshot and a
  malformed missing-repositories negative case, and a focused Vercel benchmark run exercised the
  validation hook on the real script path.
- Bundled a structural engine-results schema behind `agentverify schema engine-results`, validated
  the checked 71-repository `benchmarks/engine-results.json` snapshot against it, and extended
  distribution verification so wheels must ship the schema and source distributions must ship the
  evidence artifact. CLI and distribution tests now cover schema discovery, schema validation, and
  package-artifact expectations.
- Refreshed the full 71-repository schema-v159 engine benchmark after the Vercel Code Mode IR
  additions. The benchmark passes 71/71 repositories, scans 10,797 selected source files plus 155
  config files, and then recorded 2,942 relationships / 10,814 symbolized components. The benchmark
  summary now exposes a first-class `typescript_vercel_code_mode` slice with one repository, eight
  components, and seven approval/tool-surface relationships.
- Added a repeatable, unit-tested `scripts/benchmark_engine.py --repository <owner/name>` filter for
  focused single-repository or small-set metric refreshes before running the full 71-repository
  benchmark.
- Added exact Vercel AI Code Mode model-visible tool-surface inventory for `codeModeTool()` /
  `experimental_toolCaller(...)`, including its sandboxed TypeScript code-execution capability from
  `runCodeMode({ js: input.js, tools })`, generated host-tool prompt surface, and link to the
  approval runtime. The public IR truth set covers 2,446/2,446 passing labels.
- Added exact Vercel AI Code Mode host-tool approval-flow inventory for the runtime gate in
  `invokeHostTool(...)`, the `ai-sdk-code-mode/tool-approval` interrupt payload, and
  `continueCodeModeApproval(...)` response validation/approval-id matching. The public IR truth set
  covers 2,440/2,440 passing labels.
- Added exact Vercel AI `WorkflowAgent.model` model-setting controls for direct AI SDK provider
  calls in `@ai-sdk/workflow` constructors. The pinned Vercel AI `agent-chat.ts` WorkflowAgent now
  records its Anthropic provider/model selection as a source-agent-linked control, while bound model
  variables and cast expressions remain unresolved. The public IR truth set covers 2,435/2,435
  passing labels.
- Added exact TypeScript OpenAI Agents SDK tool guardrail reject-condition metadata for shallow
  `if` branches that directly return `rejectContent`, including literal string-includes and
  string-not-equals predicates in pinned OpenAI Agents JS examples.
- Added exact Agent-to-tool-guardrail governance edges when an OpenAI Agents JS Agent uses a
  same-file tool that already has proven `tool({ inputGuardrails, outputGuardrails })` controls.
- Added exact TypeScript OpenAI Agents SDK `Agent.clone(...)` inventory for same-file source
  Agents, including source lineage, list-property overrides, and shared omitted-list semantics.
- Extended exact TypeScript OpenAI Agents SDK `Agent.clone(...)` inventory to imported sibling
  source Agents when the import resolves to one exported OpenAI `Agent`, preserving clone lineage
  and list-property semantics without treating lookalike `.clone(...)` methods as Agents.
- Added exact TypeScript OpenAI Agents SDK `hostedMcpTool({ requireApproval, onApproval })`
  approval inventory for default, explicit-never, inline selective, stable same-file const object,
  imported local const object, aliased imported local const object, named local reexported const
  object, and callback-handled hosted MCP tools, including inline literal/result-binding
  `onApproval` return-shape metadata plus same-file readline prompt-helper source-shape metadata in
  local and pinned OpenAI examples, while mutated local/imported/reexported policy objects remain
  dynamic.
- Added exact TypeScript OpenAI Agents SDK local builtin-tool `onApproval` return-shape metadata for
  `shellTool` and `applyPatchTool` examples, including shorthand `{ approve }` returns, same-file
  readline prompt-helper source shapes, and conditional prompt-call fallback rejection for the
  pinned apply-patch example, while preserving existing auto-approval environment-bypass evidence.
- Added exact TypeScript OpenAI Agents SDK run-state approval-decision prompt-review metadata for
  direct braced `if` approval branches guarded by a same-file readline confirmation helper, covering
  pinned human-in-the-loop and hosted MCP human-loop examples while leaving reject branches and helper
  propagation separate.
- Propagated exact same-file readline prompt-review metadata through TypeScript OpenAI Agents SDK
  helper-parameter run-state approval summaries while preserving per-call source-agent provenance.
  The pinned `examples/tools/computer-use-hitl.ts` helper approval now records both
  `AUTO_APPROVE_HITL` bypass evidence and `confirm` yes/no prompt-review source shape on the
  call-site-expanded approval control.
- Added conservative same-file TypeScript object-tool `execute: helper` body mapping. A plain
  object/factory/register tool now owns capability detections inside a unique, stable same-file
  function or block-arrow helper, while shared helpers and reassigned helpers remain unresolved.
  The helper span parser now skips TypeScript return type literals such as `Promise<{...}>` before
  choosing the real function body. The pinned Vercel AI `agent-chat.ts` `calculate` tool now links
  to its delegated `new Function(...)` code-execution capability, producing a reachable AV-EXEC002
  finding through the WorkflowAgent. The slice passed the then-current reporting and public IR
  truth sets.
- Added conservative TypeScript object-tool inventory for plain object properties with top-level
  `execute` plus `inputSchema`/`parameters`, including static `needsApproval: true as const`
  normalization. The pinned Vercel AI `examples/next-workflow/workflow/agent-chat.ts` `deleteFile`
  tool now records `needs_approval: true`, and the public IR truth set covers 2,430/2,430 passing
  labels.
- Added exact Vercel AI `WorkflowAgent` constructor inventory from `@ai-sdk/workflow` and stable
  `tools` object binding edges. The pinned Vercel AI `agent-chat.ts` WorkflowAgent now links to its
  `deleteFile` object tool through `WorkflowAgent.tools`, and the public IR truth set covers
  2,432/2,432 passing labels.
- Added exact Python OpenAI Agents SDK `HostedMCPTool(tool_config={...})` approval inventory for
  explicit `"never"`, explicit or same-block/imported local literal `"always"`, shallow selective
  dict policies, imported local literal policies, named local reexported literal policies, consumer
  star-imported literal policies, imported, named-reexported, or producer-star-reexported literal
  whole `tool_config` dictionaries, and consumer-star-imported `tool_config` dictionaries,
  configured approval callbacks with exact same-file direct approval-dict return predicates and
  exact same-function result-binding approval dictionaries from the pinned OpenAI example,
  dynamic/imported-mutated bindings, dynamic imported/reexported-mutated `tool_config` bindings, and
  exact ordered local multi-star imports when the later visible source is literal, plus exact hosted
  MCP capability edges. The public IR truth set now covers 2,429/2,429 passing labels.
- Added exact Python OpenAI Agents SDK non-hosted MCP server `require_approval` call-site inventory
  for `MCPServerStdio(...)`, `MCPServerSse(...)`, `MCPServerStreamableHttp(...)`, and imported
  subclasses of exact `agents.mcp.MCPServer`, including literal never/always booleans, same-block
  literal string/dict bindings, imported local literal approval policies, selective tool-list
  policies, dynamic bindings, report-safe remote URL metadata, redacted remote
  auth/header/client-factory presence metadata, OpenAI-vs-lookalike import separation, and pinned
  OpenAI SDK remote transport corpus labels. Regenerated public IR truth-set results then covered
  2,401/2,401 passing labels.
- Added exact TypeScript OpenAI Agents SDK Agent guardrail tripwire metadata for direct returned
  `tripwireTriggered` objects in inline guardrails and stable typed `InputGuardrail`/
  `OutputGuardrail` bindings. Regenerated public IR truth-set results then covered 2,387/2,387
  passing labels; a later full engine refresh now reports 2,975 relationships / 10,848 symbolized
  components.
- Added exact TypeScript OpenAI Agents SDK Agent guardrail direct-throw metadata for stable guardrail
  bindings whose `execute` body directly throws, including official `GuardrailExecutionError`
  fallback examples.
- Added exact TypeScript OpenAI RealtimeSession output guardrail tripwire metadata for direct
  returned `tripwireTriggered` objects in inline and typed `RealtimeOutputGuardrail[]` bindings,
  including typed `RealtimeSessionOptions` spreads, while mutated arrays and settings-only
  guardrails remain unresolved.
- Added exact TypeScript OpenAI Agents SDK tool-level guardrail inventory for
  `tool({ inputGuardrails, outputGuardrails })`, including
  `defineToolInputGuardrail`/`defineToolOutputGuardrail` binding names and exact
  allow/reject-content action metadata when source-proven. Regenerated public IR truth-set results
  now cover 2,308/2,308 passing labels, and the 71-repository engine benchmark now reports
  2,898 relationships / 10,687 symbolized components.
- Added exact post-construction TypeScript OpenAI Agents SDK Agent guardrail assignment inventory
  for stable same-file `agent.inputGuardrails = [...]` and `agent.outputGuardrails = [...]`
  bindings. Regenerated public IR truth-set results now cover 2,321/2,321 passing labels, and the
  71-repository engine benchmark at that slice reported 2,900 relationships / 10,689 symbolized
  components.
- Added compact scan summaries for CI logs.
- Added deterministic `risk_summary` data to JSON reports and native AI BOM governance.
- Added bundled schemas for JSON reports, native AI BOMs, and policies.
- Versioned normal JSON reports with `report_format: AgentVerify JSON Report` and
  `schema_version: 1`.
- Hardened baseline parsing so unknown JSON and malformed report entries fail closed instead of
  behaving like empty baselines.
- Aligned example policies with all current high-severity approval-review rules.
- Added and validated a bundled rules-catalog schema so `agentverify rules --format json` has a
  first-class machine contract.
- Added a reusable distribution verifier that checks built wheels for every runtime schema file.
- Added a sealed holdout benchmark design to separate public regression metrics from unbiased
  evaluation claims.
- Added public holdout manifest/label templates while keeping real sealed labels out of the repo.
- Added benchmark evaluator metadata for public-regression versus sealed-holdout outputs.
- Added a benchmark result JSON schema and tests for checked-in and synthetic sealed outputs.
- Extended distribution verification to cover the wheel console-script entry point and optional
  installed-CLI smoke tests.
- Added a benchmark result verifier that validates result JSON and recomputes label/manifest digests.
- Added `agentverify policy PATH` to validate/explain composed policy provenance without scanning a
  repository and without treating content hashes as signatures.
- Added a bundled policy-summary schema and included it in wheel/content and installed CLI checks.
- Added local policy digest trust roots for `agentverify policy`, including `--require-trusted`
  gating while still reporting `signature_verified: false`.
- Added benchmark-result release guardrails: verifier flags can require public-regression or
  sealed-holdout metadata, sealed status, manifests, and label scopes; docs now spell out claim
  boundaries before publishing benchmark numbers.
- Bundled the benchmark-result schema behind `agentverify schema benchmark-result`, with distribution
  smoke coverage and a drift test against the canonical `benchmarks/benchmark-results-v1.schema.json`.
- Added a checked-in runnable policy trust-root example for the composed organization/repository
  policy pair, and extended installed-wheel smoke tests to require that trust root to pass.
- Added `agentverify schema` discovery output so installed users can list all bundled machine
  contracts from the same schema registry used by rendering and smoke tests.
- Added `agentverify policy --export-trust-root` so teams can generate a schema-v1 local digest
  allowlist directly from composed policy inputs, with installed-wheel smoke coverage that exports
  and then requires the generated trust root.
- Added exact local package reexport-chain attribution for AgentScope/PydanticAI provider-wrapper
  symbols, including direct/transitive/wildcard provider-model positives, rebound and filtered
  negatives, imported simple wrapper-factory positives with ambiguous/rebound negatives, and
  regenerated IR truth-set results then covering 1,466 labels.
- Added literal-`__all__` star-import resolution for selected local callables used in Python Agent
  literal tool lists, with wildcard positive/filtered-negative IR labels and regenerated IR
  truth-set results now covering 1,469 labels.
- Added literal-visibility star-import resolution for simple local provider wrapper factories, with
  exported/static positives, a filtered negative, and regenerated IR truth-set results now covering
  1,474 labels.
- Added exact local reexport-chain resolution for simple provider wrapper factories, with
  direct/wildcard reexport positives, filtered/rebound negatives, and regenerated IR truth-set
  results now covering 1,487 labels.
- Added exact Python framework agent constructor aliases and selected local reexport/star-reexport
  resolution for import-proven AgentScope/CAMEL/Marvin-style constructors, with hidden-export and
  rebound negatives, and regenerated IR truth-set results now covering 1,496 labels.
- Preserved constructor provenance attributes for those exact framework agent aliases and local
  reexports, recording the origin module, imported symbol, and exact resolution mode while keeping
  the public IR truth set at 1,496 passing labels.
- Added OpenAI Agents SDK `agents.Agent` alias, named-reexport, and star-reexport regression labels
  for the same constructor-provenance contract, bringing the public IR truth set to 1,499 passing
  labels.
- Added Google ADK `google.adk.agents.Agent` alias, named-reexport, and star-reexport regression
  labels for generic framework-prefix constructor provenance, bringing the public IR truth set to
  1,502 passing labels.
- Added exact Semantic Kernel `semantic_kernel.agents.ChatCompletionAgent` constructor provenance
  through direct aliases plus local named/star reexports, bringing the public IR truth set to 1,505
  passing labels.
- Added direct, named-reexport, and star-reexport provenance coverage for the remaining exact Python
  framework constructor table entries: Qwen-Agent `Assistant`, Lagent `AgentForInternLM`, and MetaGPT
  `Role`, bringing the public IR truth set to 1,514 passing labels.
- Added exact module-qualified Python framework constructor provenance for top-level absolute imports
  such as AgentScope, OpenAI Agents SDK, Google ADK, Semantic Kernel, Qwen-Agent, Lagent, and MetaGPT,
  with root-rebound, constructor-attribute-rebound, and near-package negatives, bringing the public IR
  truth set to 1,525 passing labels.
- Added a narrow exact absolute star-import path for the same Python framework constructor families,
  with ambiguous-star, shadowed-name, and near-package negatives, bringing the public IR truth set to
  1,536 passing labels.
- Extended same-block local Agent factory-return resolution to exact module-qualified framework
  constructors, with AgentScope/OpenAI/Google ADK factory positives and conditional/forward/rebound
  negatives, bringing the public IR truth set to 1,545 passing labels.
- Extended native TypeScript provider typed-parameter attribution to non-exported `const` arrow
  helpers with balanced block bodies under the same call-site consensus rule, while exported,
  mixed-call-site, escaped, and expression-bodied arrows remain unresolved; regenerated public IR
  truth-set results now cover 1,552 labels.
- Added a concrete signed policy provenance design that keeps digest allowlists separate from author
  authenticity and specifies detached source-digest payloads plus local key trust roots.
- Added `agentverify policy --export-signing-payload` and a bundled policy-signing-payload schema so
  composed policy source digests can be handed to external signing tools without claiming signature
  verification.
- Added bundled policy-signature and policy-key-trust-root schemas for the planned detached
  signature bundle and local Ed25519 key trust-root contracts, still without reporting signature
  verification.
- Implemented fail-closed detached Ed25519 policy signature verification for `agentverify policy`
  with `--signature` plus a local key trust root, including signed-manifest digest coverage,
  machine-readable failure reasons, schema validation, and CLI gating via `--require-trusted`.
- Added a signed-policy dry-run walkthrough that generates an ephemeral key only in a temporary
  directory, demonstrates detached signature verification, and warns production users to rely on
  their own key-management workflow.
- Extended source-distribution verification to require `pyproject.toml`, so source releases carry
  the runtime dependency declaration that signed policy verification relies on.
- Extended installed-wheel smoke verification to install runtime dependencies and exercise a full
  ephemeral detached-policy-signature verification path through the installed `agentverify`
  executable.
- Added a reusable ephemeral signed-policy verification helper and wired default CI plus installed
  wheel smoke checks through that same helper, proving detached Ed25519 policy verification without
  committing durable private-key material.
- Extended distribution verification so release checks can require a source distribution containing
  README-linked examples, policy docs, benchmark contracts, and public truth sets.
- Extended source-distribution verification to require the checked public benchmark result outputs
  alongside their labels, so release artifacts carry both benchmark contracts and verifier evidence.
- Added installed CLI benchmark result verification via `agentverify benchmark verify`, backed by
  the bundled benchmark-result schema, shared with the source-checkout verifier script, and covered
  by installed-wheel smoke tests.
- Added a copyable local pre-commit config and tests for both the future release hook manifest and
  current local setup, and extended source-distribution verification to require those pre-commit
  adoption artifacts.
- Added an editor/CI contract exporter that writes the report schema, rules schema, current rules
  catalog, optional sample report, and digest manifest, with tests and source-distribution coverage
  for the exporter and integration guide.
- Promoted editor/CI contract export into the installed CLI as `agentverify contracts`, with the
  source-checkout script reduced to a wrapper and installed-wheel distribution smoke coverage that
  exports the schema/catalog/sample-report bundle.
- Added a checked Language Server Protocol-style editor diagnostics example derived from the
  `cases/approval_callback_bypass` report, including tests that regenerate the mapping from a real
  scan and source-distribution coverage for the linked example artifact.
- Added a copyable GitHub Actions policy-gate workflow that uses read-only repository permissions,
  validates policy composition before scanning, emits compact summary output, requires suppression
  expiry, and is now required in source-distribution verification.
- Added explicit all-labels-passed benchmark verification output and a `--require-all-passed` gate,
  so public regression release checks can fail closed on honest failing-label result files while
  still allowing failed sealed-holdout metrics to be validated when intentionally published.
- Hardened benchmark result verification to reject cross-field drift between labels, outcomes,
  passed totals, and outcome-derived metrics, so release gates cannot be satisfied by editing
  aggregate result fields without matching per-label evidence.
- Wired the default CI workflow to run the installed CLI benchmark verification gate on checked-in
  public regression results, with a workflow regression test and release-checklist guidance.
- Bound benchmark result outcomes back to the digested label file's label scope, label ids,
  rule/check ids, and expected values before accepting aggregate metrics.
- Extended TypeScript model literal binding so module-level template strings composed only from
  earlier immutable literal constants resolve as exact model ids for native OpenAI/Anthropic calls
  and official AI SDK provider calls; runtime, mutable, forward, shadowed, rebound, and unknown
  template expressions remain unresolved.
- Added a checked copyable GitHub SARIF upload workflow in `examples/github-code-scanning.yml`,
  documented it separately from policy enforcement, and made it a required source-distribution
  artifact so SARIF adoption guidance survives release packaging.
- Added two explicit TypeScript unknown-template negative model-binding labels so runtime-derived
  template interpolations remain guarded in the public IR regression set.
- Added a checked GitHub code-scanning SARIF payload example generated from
  `cases/approval_callback_bypass`, with a regression test proving it matches real renderer output
  and source-distribution verification requiring the artifact.
- Added a checked copyable GitHub benchmark-verification workflow that runs the installed
  `agentverify benchmark verify` public-regression/all-labels-passed gate, validates the JSON output,
  uploads it as a workflow artifact, and is now required in source distributions.
- Extended Python filesystem mutation detection to follow same-function, statement-ordered callable
  alias chains while every hop copies an already proven compatible `os`/`shutil` mutator. Added
  positive and negative rule/IR labels.
- Added explicit CAMEL and Marvin regression coverage for exact module-qualified and absolute
  star-import Python framework agent constructors, plus matching module-attribute-rebound and
  star-shadowed negative guards, bringing that slice of the public IR truth set to 1,567 labels.
- Extended `agentverify contracts` manifest artifacts with explicit `kind`, `contract`, and
  `required` metadata while preserving path/byte/digest fields, so editor and CI integrations can
  distinguish report schemas, rules schemas, rules catalogs, and optional sample reports without
  hard-coding filenames.
- Added a bundled `editor-contract-manifest` schema and runtime validation for `agentverify
  contracts`, with CLI schema discovery and installed-wheel smoke checks proving the schema ships
  with release artifacts.
- Added `agentverify contracts --verify-dir` to validate copied editor/CI contract bundles against
  their manifest schema, required artifact entries, recomputed byte counts and SHA-256 digests, and
  bundled rules/sample-report schemas. Installed-wheel smoke now exports and verifies a bundle.
- Hardened contract-bundle verification so malformed manifests cannot cause verification to read
  parent-relative, nested, absolute, or otherwise non-basename artifact paths.
- Added a bundled `editor-contract-verification` schema and runtime validation for
  `agentverify contracts --verify-dir`, with CLI discovery and installed-wheel smoke coverage.
- Added a malformed-manifest regression proving verifier failure output stays schema-valid and
  normalizes invalid artifact metadata instead of leaking unexpected JSON types.
- Added a bundled `benchmark-verification` schema and runtime validation for
  `agentverify benchmark verify` JSON output, and upgraded the copyable GitHub benchmark workflow to
  validate its uploaded verifier artifact against that schema.
- Extended Python registered-class network propagation to exact local module-qualified constructors,
  while preserving local module-alias shadowing as an unresolved counterexample; the current
  regenerated IR truth-set results now cover 1,574 passing labels after the later TypeScript
  CommonJS Google coverage.
- Extended native TypeScript provider SDK CommonJS proof to exact top-level direct and aliased
  `GoogleGenAI` named destructuring, with a scoped-require negative guard; regenerated IR truth-set
  results now cover 1,574 passing labels.
- Pinned native TypeScript provider SDK CommonJS named-destructuring aliases for OpenAI and
  Anthropic alongside the existing Google GenAI case, proving constructor and model attribution for
  `const { OpenAI: Alias } = require("openai")` and
  `const { Anthropic: Alias } = require("@anthropic-ai/sdk")` while keeping scoped named requires
  unresolved; regenerated IR truth-set results then covered 1,584 passing labels.
- Added TypeScript native-provider type-only negative coverage for `import type` and inline
  `import("openai").default...` annotations, reflecting a Roo Code corpus pattern where SDK types
  describe tool schemas without proving runtime provider construction.
- Pinned an MCP TypeScript quickstart-shaped lazy `Anthropic` class getter with an immutable
  module-level model literal in the local fixture, so provider and exact model attribution fail fast
  without relying only on the cached real repository; regenerated IR truth-set results then covered
  1,586 passing labels.
- Added a local negative IR label for class-field native SDK calls whose provider is proven but
  model argument is a method parameter, keeping exact model attribution unresolved when no literal or
  immutable module-level binding is available; regenerated IR truth-set results then covered 1,587
  passing labels.
- Added a named OpenAI `import type { OpenAI as ... } from "openai"` negative to the TypeScript
  native-provider type-only fixture, mirroring Roo Code's SDK type-only tool-schema pattern and
  keeping exact provider/model attribution tied to runtime value-import/constructor proof;
  regenerated IR truth-set results then covered 1,588 passing labels.
- Added a checked `examples/benchmark-verification.json` public-regression verifier artifact that is
  regenerated by the installed CLI shape, schema-validated in tests, linked from release guidance,
  and required in source distributions.
- Required `benchmarks/holdout-labels.template.json` in source distributions and README artifact
  links, so the sealed-holdout public scaffold ships both the manifest and label templates promised
  by `benchmarks/holdout-design.md`.
- Added bundled `holdout-manifest` and `holdout-labels` schemas exposed through
  `agentverify schema`, validating the checked public sealed-holdout setup templates and extending
  installed-wheel schema smoke coverage to 15 schemas.
- Added `agentverify holdout validate` so installed CLIs can validate public or private holdout
  manifest/label setup files directly against the bundled schemas, with text/JSON output, fail-closed
  exit code 2 on malformed inputs, README/checklist guidance, tests, and installed-wheel smoke
  coverage.
- Wired the default CI workflow and copyable GitHub benchmark verification workflow to run
  `agentverify holdout validate` on the checked public setup templates, with regression tests so the
  benchmark release recipe keeps validating setup files as well as result files.
- Extended benchmark result and verification contracts with derived `failed` counts and
  `failure_summary` buckets for observation, anchor, and source-snippet mismatches. Regenerating the
  public truth sets exposed and corrected a stale `AV-NET001` reporting-rule label for exact local
  module-qualified registered-class network propagation; reporting-rule labels now pass 719/719 and
  IR labels then passed 1,588/1,588 with zero mismatch summaries.
- Hardened source/wheel distribution smoke verification to preserve and require the installed CLI's
  benchmark failure summaries, so packaging checks now prove the `failed` and `failure_summary`
  contract survives installation rather than only checking label counts.
- Extended TypeScript exact model attribution to immutable module-level literal object maps, so
  native SDK and official AI SDK calls can resolve `MODEL_IDS.chat`-style model IDs while mutable
  object properties and nonliteral object values remain unresolved; regenerated public IR truth-set
  results then covered 1,595 passing labels.
- Extended that TypeScript object-map proof to exact literal bracket reads such as
  `MODEL_IDS["chat"]` while keeping dynamic bracket keys unresolved; regenerated public IR truth-set
  results then covered 1,600 passing labels.
- Extended exact literal bracket reads to quoted object-map keys such as `MODEL_IDS["chat-model"]`
  and hardened object-map stability so any bracket member write invalidates the map; regenerated
  public IR truth-set results then covered 1,605 passing labels.
- Added exact TypeScript AI SDK local named-reexport proof for supported `@ai-sdk/*` provider
  instance/factory symbols, including a bounded transitive local export hop, while ambiguous
  reexports and local shadowing remain unresolved; regenerated public IR truth-set results then covered
  1,613 passing labels.
- Added real Activepieces negative labels for its source-visible but implementation-hidden
  `@activepieces/ai-providers` `createLanguageModel({ provider, modelId })` workspace wrapper and
  Cloudflare `@ai-sdk/openai-compatible` custom endpoint branch; regenerated public IR truth-set
  results then covered 1,616 passing labels.
- Added exact official TypeScript AI SDK Azure OpenAI attribution for `@ai-sdk/azure` imports and
  `createAzure` factory/configured embedding calls, while allowing only endpoint-neutral
  `spreadIfDefined('apiVersion', ...)` spreads and keeping baseURL spreads unresolved. A real
  Activepieces Azure embedding provider is now pinned; regenerated public IR truth-set results now
  covered 1,622 passing labels.
- Extended exact local TypeScript AI SDK named-reexport regression coverage to the Azure factory
  path, including a provider/model positive and provider/model negatives for a baseURL-spread
  reexport. Regenerated public IR truth-set results then covered 1,626 passing labels.
- Added exact TypeScript AI SDK local star-reexport proof for single-symbol OpenAI/Azure barrels,
  including a local transitive Azure `export *` hop, while duplicate star-barrel provenance remains
  unresolved. Regenerated public IR truth-set results then covered 1,631 passing labels.
- Added exact TypeScript AI SDK CommonJS named-destructuring proof for top-level supported
  `@ai-sdk/*` provider symbols, including OpenAI and Azure configured embedding positives plus a
  rebound-alias negative. Regenerated public IR truth-set results then covered 1,637 passing labels.
- Added exact TypeScript OpenAI Agents sandbox inventory for `@openai/agents/sandbox`
  `SandboxAgent` direct assignments and literal `capabilities: [shell()]` entries. SDK sandbox shell
  execution is recorded separately from host-local shell execution, with local near/rebound negatives
  and two real OpenAI Agents JS example positives. Regenerated public IR truth-set results then
  covered 1,659 passing labels.
- Extended TypeScript OpenAI Agents sandbox inventory to same-file helper returns of exact
  `@openai/agents/sandbox` `SandboxAgent` constructors, preserving SDK-sandbox shell classification
  and keeping near/rebound/conditional helper forms unresolved. Local helper fixtures plus
  shared-session and memory multi-agent OpenAI Agents JS examples are pinned. Regenerated public IR
  truth-set results then covered 1,686 passing labels.
- Extended exact TypeScript OpenAI Agents sandbox capability inventory to unshadowed `filesystem()`
  and `memory()` factories in literal capability lists. The scanner records SDK-sandbox filesystem
  and memory reachability separately from host-local filesystem risk, while rebounded capability
  aliases stay unresolved. Local fixtures plus OpenAI Agents JS `memory.ts` and
  `memory-generation.ts` labels raised regenerated public IR truth-set results to 1,712 passing
  labels.
- Extended exact TypeScript OpenAI Agents sandbox capability inventory to unshadowed `skills()`
  factories in literal capability lists, recording `skill-loading` as SDK-sandbox reachability while
  leaving aggregate `Capabilities.default()` and rebounded skill aliases unresolved. Local fixtures
  plus OpenAI Agents JS sandbox coding/capability/docs examples raised regenerated public IR
  truth-set results to 1,729 passing labels.
- Added exact TypeScript OpenAI Agents sandbox runtime-client inventory for
  `@openai/agents/sandbox/local` `UnixLocalSandboxClient` and `DockerSandboxClient` constructors
  wired into `run(..., { sandbox: { client/session } })`. Direct client bindings, inline client
  construction, one exact `client.create(...)` session binding, and object-shorthand `{ session }`
  now produce agent `configured-by` `sandbox-runtime` control edges. Rebounded local-client imports
  and unknown sessions stay unresolved. Local fixtures plus four OpenAI Agents JS examples raised
  regenerated public IR truth-set results to 1,747 passing labels.
- Extended that runtime-client inventory to exact ternary client initializers whose outer expression
  is a conditional and whose branches each contain exactly one unshadowed sandbox-local
  `DockerSandboxClient`/`UnixLocalSandboxClient` constructor. The scanner records one
  `conditional-local` `sandbox-runtime` control with Docker/Unix options and carries it through
  direct `client.create(...)` session bindings into `run(..., { sandbox: { session } })`; half-known
  ternaries remain unresolved. Local positive/negative fixtures plus OpenAI Agents JS
  `examples/sandbox/basic.ts` and `examples/sandbox/resume.ts` raised regenerated public IR
  truth-set results to 1,755 passing labels.
- Extended sandbox runtime session binding through exact local `const resumableClient = client as ...`
  aliases and `resumedSession = await resumableClient.resume(...)` assignments. The resumed session
  inherits the original proven `sandbox-runtime` control rather than creating a second control;
  unknown resumable aliases remain unresolved. Local positive/negative fixtures plus OpenAI Agents JS
  `examples/sandbox/resume.ts` and `examples/sandbox/memory.ts` raised regenerated public IR
  truth-set results to 1,759 passing labels.
- Added exact OpenAI Agents JS extension sandbox runtime inventory for
  `@openai/agents-extensions/sandbox/blaxel` `BlaxelSandboxClient` and
  `@openai/agents-extensions/sandbox/cloudflare` `CloudflareSandboxClient`, including
  `new Runner({ sandbox: { client } })` bindings and `runner.run(agent, ...)` agent
  `configured-by` edges. Unknown Runner sandbox clients remain unresolved. Local fixtures plus
  Blaxel/Cloudflare OpenAI Agents JS examples raised regenerated public IR truth-set results to
  1,768 passing labels.
- Extended exact local OpenAI Agents JS sandbox session binding to inline
  `await new DockerSandboxClient(...).create(...)` and
  `await new UnixLocalSandboxClient(...).create(...)` assignments when the constructor import is
  exact and unshadowed. The created session now links `run(..., { sandbox: { session } })` back to a
  `sandbox-runtime` control, while unknown inline constructors remain unresolved. Local
  positive/negative fixtures plus OpenAI Agents JS
  `examples/docs/sandbox-agents/conversation-identity.ts` raised regenerated public IR truth-set
  results to 1,774 passing labels.
- Extended sandbox runtime edge attribution through variables initialized by direct calls to
  already-proven same-file `return new SandboxAgent(...)` helpers. This recovers shared-session
  `run(..., { sandbox: { session } })` edges in OpenAI Agents JS
  `examples/sandbox/shared-session-workdirs.ts` and
  `examples/sandbox/memory-multi-agent-multiturn.ts`, while unknown helper factories remain
  unresolved. Regenerated public IR truth-set results then covered 1,781 passing labels.
- Added exact option-level OpenAI Agents JS `Runner.run(...)` sandbox session attribution for
  imported Runner instances, plus typed session-variable binding when the initializer is still a
  proven sandbox-local `client.create(...)` call. Local positives/negative and the real
  `examples/sandbox/memory-generation.ts` edge raised regenerated public IR truth-set results to
  1,785 passing labels.
- Added exact `SandboxAgent.asTool(...)` `runConfig.sandbox.session` runtime attribution for
  delegated sandbox agents. Local positive/negative fixtures plus the real OpenAI Agents JS
  `examples/sandbox/sandbox-agents-as-tools.ts` pricing and rollout agent runConfig sessions raised
  regenerated public IR truth-set results to 1,789 passing labels.
- Added exact OpenAI Agents JS sandbox `exposedPorts` inventory for literal numeric arrays on
  unshadowed `@openai/agents/sandbox/local` client constructors. The scanner now records a
  `sandbox-network-exposure` control linked back to the corresponding `sandbox-runtime`, while
  unknown same-named clients remain unresolved. Local fixtures plus the real
  `examples/docs/sandbox-agents/exposed-ports.ts` example raised regenerated public IR truth-set
  results to 1,795 passing labels.
- Added exact OpenAI Agents JS `Manifest({ extraPathGrants: [...] })` inventory for direct literal
  or earlier immutable module-level literal paths with literal boolean `readOnly`. The scanner now
  records `sandbox-path-grant` controls while unknown Manifest constructors remain unresolved. Local
  fixtures plus the real `examples/docs/sandbox-agents/path-grants.ts` example raised regenerated
  public IR truth-set results to 1,798 passing labels.
- Added exact OpenAI Agents JS Manifest `environment` inventory for direct literal string values or
  earlier immutable module-level literal string bindings. The scanner now records
  `sandbox-environment-variable` controls, redacts values for secret-like variable names, and leaves
  unknown Manifest constructors unresolved. Local fixtures plus the real
  `examples/docs/sandbox-agents/manifest.ts` and `examples/sandbox/extensions/blaxel-runner.ts`
  examples raised regenerated public IR truth-set results to 1,803 passing labels.
- Added exact OpenAI Agents JS Manifest `entries` inventory for supported literal source forms:
  `file(...)`, `gitRepo(...)`, direct `{ type: "file" }`, and `localDir(...)` with direct or earlier
  immutable module-level literal `src`. The scanner now records `sandbox-manifest-entry` controls
  without copying file contents into IR, and unknown Manifest constructors remain unresolved. Local
  fixtures plus real docs examples raised regenerated public IR truth-set results to 1,810 passing
  labels.
- Added exact OpenAI Agents JS `sandbox.concurrencyLimits` runtime-option inventory for direct
  integer literal limit objects attached to proven sandbox runtime client/session options. The
  scanner now records `sandbox-concurrency-limit` controls linked back to the runtime control while
  unknown clients and nonliteral limit values remain unresolved. Local fixtures plus the real
  `examples/docs/sandbox-agents/manifest-concurrency.ts` example raised regenerated public IR
  truth-set results to 1,815 passing labels.
- Added exact OpenAI Agents JS Manifest `root` workspace-path inventory for direct literal strings
  or earlier immutable module-level literal string bindings. The scanner now records
  `sandbox-workspace-root` controls while unknown Manifest constructors and dynamic root values
  remain unresolved. Local fixtures plus real docs and Blaxel extension examples raised regenerated
  public IR truth-set results to 1,819 passing labels.
- Added exact OpenAI Agents JS local sandbox `snapshot` inventory for `type: "local"` plus direct or
  earlier immutable module-level literal `baseDir` values on proven sandbox-local clients. The
  scanner now records `sandbox-state-persistence` controls linked back to the corresponding
  `sandbox-runtime`, while unknown clients and dynamic snapshot directories remain unresolved. Local
  fixtures plus the real `examples/docs/sandbox-agents/resume-session-state.ts` example raised
  regenerated public IR truth-set results to 1,825 passing labels.
- Strengthened source-release verification for the packaged GitHub workflow examples:
  `verify_sdist()` now checks benchmark verifier output/schema/upload, policy-gate
  permission/policy/summary/expiry arguments, and code-scanning SARIF permission/upload contracts.
  Negative distribution tests prove the sdist verifier rejects removed verifier upload, missing
  policy argument, and missing SARIF upload cases.
- Added exact OpenAI Agents JS sandbox `memory(...)` policy inventory for literal generation
  toggles, read live-update settings, memory/session layout directories, and literal generation
  model/prompt settings. Dynamic memory option values remain unresolved. Local fixtures plus real
  OpenAI Agents JS memory docs/examples raised regenerated public IR truth-set results to 1,838
  passing labels.
- Added exact OpenAI Agents JS nested Manifest directory/file seed inventory: literal
  `entries` directories with literal `children` are flattened into `sandbox-manifest-entry`
  controls for each visible directory/file path, while dynamic child maps remain unresolved. Local
  fixtures plus a real `memory-multi-agent-multiturn.ts` example raised regenerated public IR
  truth-set results to 1,849 passing labels.
- Added exact OpenAI Agents JS `sandbox.cwd` inventory for direct `run(...)`, `runner.run(...)`,
  `Runner({ sandbox })`, and delegated `asTool({ runConfig })` sandbox option objects when a proven
  sandbox runtime is already attached. Literal or earlier immutable module-level working directories
  become `sandbox-working-directory` controls linked to the runtime; dynamic cwd values remain
  unresolved. Local fixtures plus the real `shared-session-workdirs.ts` example raised regenerated
  public IR truth-set results to 1,856 passing labels.
- Added exact OpenAI Agents JS Manifest composition links from proven consumers back to emitted
  Manifest policy controls. `client.create(manifest)`, `client.create({ manifest })`,
  `SandboxAgent({ defaultManifest: manifest })`, and same-file one-return Manifest helper calls now
  add `configured-by` edges to entries, workspace roots, path grants, and environment controls while
  ambiguous helpers and dynamic Manifest values remain unresolved. An ambiguous-helper regression
  pins that no-link boundary. Local fixtures plus real OpenAI Agents JS examples raised regenerated
  public IR truth-set results to 1,872 passing labels.
- Added focused truth-set evaluation filters for development runs. `scripts/evaluate_truthset.py`
  now accepts repeated `--check-id`, `--rule-id`, and `--label-id-prefix` filters, records the
  filter in schema-backed benchmark-result metadata, and `agentverify benchmark verify` applies that
  filter before checking outcome counts and label IDs. A real focused OpenAI sandbox IR run verified
  235/235 labels in a few seconds instead of scanning every public truth-set target.
- Added optional evaluator progress timing with `scripts/evaluate_truthset.py --progress`. The flag
  prints per-target scan timings to stderr without changing benchmark-result JSON, and a focused
  OpenAI sandbox IR run showed the cached `openai/openai-agents-js` checkout dominating that slice
  at roughly 3.5 seconds versus subsecond local fixtures.
- Added an explicit `--scan-label-paths` development shortcut for `scripts/evaluate_truthset.py`.
  It scans only files referenced by the evaluated labels through the existing scanner selected-paths
  path, records `benchmark.scan_scope: selected-label-paths`, and surfaces that optional scope from
  benchmark verification. The focused OpenAI sandbox IR slice passed 235/235 in about 1.2 seconds
  wall time, while a full selected-path all-IR experiment dropped timed scan cost from about 482.5
  seconds to 57.5 seconds but failed 285 cross-file-dependent labels, confirming it is a fast
  focused-development mode rather than release evidence.
- Suppressed third-party Python `SyntaxWarning` noise at the scanner boundary, so benchmark progress
  output is no longer polluted by cached repositories with invalid escape sequences in string
  literals. A MetaGPT single-label slice now prints only the `--progress` timing line and passes.
- Added exact OpenAI Agents JS `MemorySession({ sessionId })` conversation-session inventory,
  keeping durable conversation identity distinct from sandbox runtime sessions. Direct
  `run(..., { session })` and `Runner.run(..., { session })` options now link agents to
  `conversation-session` controls when `MemorySession` is an unshadowed `@openai/agents` value
  import and `sessionId` is literal or an earlier immutable module-level literal binding. Dynamic
  session IDs, rebound imports, and unknown same-named constructors remain unresolved. Local
  fixtures plus real `conversation-identity.ts` and `memory-multi-agent-multiturn.ts` examples
  raised regenerated public IR truth-set results to 1,887 passing labels.
- Added exact OpenAI Agents JS server-managed conversation ID inventory. `const client = new
  OpenAI()` from the exact `openai` package plus `const { id: conversationId } = await
  client.conversations.create(...)` now emits a `conversation-session` control and links
  `run(..., { conversationId })` / `Runner.run(..., { conversationId })` options from the agent to
  it. Unknown clients, rebound OpenAI constructors, reassigned IDs, and loose string IDs remain
  unresolved. Local fixtures plus the real `examples/docs/running-agents/conversationId.ts` example
  raised regenerated public IR truth-set results to 1,897 passing labels.
- Added exact OpenAI Agents JS previous-response continuity inventory. A variable derived from
  `first.lastResponseId` is accepted only when `first` is a stable result binding from an exact
  OpenAI Agents `run(agent, ...)` call. Later `run(..., { previousResponseId })` options link the
  agent to a `conversation-continuity` control, while loose strings, unknown run functions, and
  reassigned run-result bindings remain unresolved. Local fixtures plus the real
  `examples/docs/running-agents/previousResponseId.ts` example raised regenerated public IR
  truth-set results to 1,904 passing labels.
- Added exact OpenAI Agents JS `result.history` conversation-continuity inventory. A local input
  array binding can become a `conversation-continuity` control only when it is assigned from
  `.history` on a stable result binding returned by an exact imported `run(agent, ...)` call, and a
  later direct `run(agent, historyInput)` or `runner.run(agent, historyInput)` links the consuming
  agent back to that control if the binding has not been reassigned. Loose arrays, unknown run
  functions, and reassigned history inputs remain unresolved. Local fixtures plus the real
  `examples/tools/web-search.ts` and `examples/agent-patterns/llm-as-a-judge.ts` examples raised
  regenerated public IR truth-set results to 1,916 passing labels.
- Added exact OpenAI Agents JS `result.state` run-state resume inventory for same-file direct
  `run(...)` and `Runner.run(...)` continuations. Inline `run(agent, result.state)` and named
  `const state = stream.state; run(agent, state, ...)` become `conversation-continuity` controls
  only when the state comes from a prior exact OpenAI Agents run result and is consumed before
  invalidating reassignment; same-statement `result = await run(agent, result.state)` is accepted as
  a resume of the old state. Loose state objects, unknown run functions, stale result bindings, and
  reassigned named state inputs remain unresolved. Local fixtures plus real OpenAI Agents JS
  HITL/MCP examples raised regenerated public IR truth-set results to 1,937 passing labels.
- Added exact OpenAI Agents JS generic `tool({ needsApproval })` approval inventory. Literal
  `needsApproval: true` now records tool-level `approval_policy: enabled` metadata and still emits
  the existing `human-approval` governed-by edge, while callback-valued `needsApproval` records
  `approval_policy: callback-controlled` without treating coverage as proven always-present. The
  slice is limited to exact unshadowed `tool` imports from `@openai/agents`; local fixtures plus
  real OpenAI Agents JS docs/Next.js/HITL examples raised regenerated public IR truth-set results to
  1,949 passing labels.
- Added exact OpenAI Agents JS delegated-agent `asTool({ needsApproval })` approval inventory.
  Inline delegated-agent adapter edges now anchor evidence to the exact `agent.asTool(...)` call, so
  repeated adapters to the same target agent remain distinct. Literal `needsApproval: true` records
  always-enabled approval metadata, callback-valued `needsApproval` records callback-controlled
  approval metadata without claiming always-present human approval, and plain delegated-agent tools
  remain unapproved. Local fixtures plus the real OpenAI Agents JS HITL examples raised regenerated
  public IR truth-set results to 1,954 passing labels.
- Added exact OpenAI Agents JS run-state approval-decision inventory. AgentVerify now records
  SDK-native `state.approve(...)`, `state.reject(...)`, `result.state.approve(...)`, and
  `result.state.reject(...)` as `approval-decision` controls only when the receiver is proven to
  come from an exact OpenAI Agents `run(...)`/`Runner.run(...)` result state. Loose approval-shaped
  objects, unknown run results, stale result bindings, and rebound state bindings remain unresolved.
  Local fixtures plus real OpenAI Agents JS streaming HITL and hosted MCP HITL examples raised
  regenerated public IR truth-set results to 1,965 passing labels.
- Added exact OpenAI Agents JS serialized run-state restoration via `RunState.fromString(...)`.
  AgentVerify now follows a narrow same-file chain from `JSON.stringify(result.state, ...)` or
  `result.state.toString()` into a stable serialized-state binding, through literal
  `writeFile`/`readFile` persistence when present, and then into `RunState.fromString(agent,
  serializedState)` only when the target agent matches the original SDK run result. Restored state
  then participates in resume and approval-decision inventory. Local fixtures plus the real
  standard OpenAI Agents JS HITL example raised regenerated public IR truth-set results to 1,974
  passing labels.
- Added exact OpenAI Agents JS builtin-tool callback approval inventory for approval-capable
  builtins such as `computerTool({ needsApproval: async ... })`. Callback-valued builtin
  `needsApproval` now records `approval_policy: callback-controlled`,
  `approval_handler: needsApproval-callback`, and `approval_decision: dynamic-callback` instead of
  the older unresolved-handler fallback, while literal approval semantics remain unchanged. Local
  fixtures plus the real OpenAI Agents JS `examples/tools/computer-use-hitl.ts` singleton and
  per-request examples raised regenerated public IR truth-set results to 1,977 passing labels.
- Added a first exact OpenAI Agents JS approval-predicate inventory slice. Callback-valued
  `needsApproval` now records narrow literal predicate metadata for field prefix checks, field
  substring checks, and field-in-literal-set checks across generic `tool(...)`, delegated
  `agent.asTool(...)`, and approval-capable builtin tool constructors. Local fixtures plus real
  OpenAI Agents JS docs/HITL/computer-use examples raised regenerated public IR truth-set results to
  1,987 passing labels.
- Added exact OpenAI Agents JS `computerTool({ onSafetyCheck })` safety-check inventory and
  high-severity review rule `AV-APPROVAL011`. Exact callbacks that return `true` or acknowledge the
  full `pendingSafetyChecks` list are recorded as `safety_check_policy: auto-acknowledge-all` and
  reported only when the computer-control capability is reachable. Local fixtures plus the real
  OpenAI Agents JS `examples/tools/computer-use-hitl.ts` per-request flow raised regenerated public
  coverage at that checkpoint after adding the SDK-supported `acknowledged_safety_checks` spelling
  and expression-bodied object return shape as local regressions.
- Extended `AV-APPROVAL011` to exact OpenAI Agents Python `ComputerTool(on_safety_check=...)`
  auto-acknowledgement. Inline `lambda ...: True` callbacks and scope-proven same-file callbacks
  with a final `return True` are reported when reachable, while conditional callbacks stay
  unresolved. Local Python fixtures plus real OpenAI Agents Python SDK tests raise the public IR
  truth set to 1,999 labels and the reporting truth set to 729 labels.
- Added exact OpenAI Agents JS run-state approval-decision bypass provenance. `RunState.approve(...)`
  controls now record when their braced approval branch is guarded by a same-file confirmation
  helper with an environment-backed true-return path, while reject branches and reassigned boolean
  guards remain clean. Local fixtures plus real OpenAI Agents JS HITL examples raise the public IR
  truth set to 2,007 labels.
- Added exact OpenAI Agents Python run-state approval-decision inventory. `state.approve(...)` and
  `state.reject(...)` controls are recorded only when the receiver state is proven from
  `Runner.run(...)`/`Runner.run_streamed(...).to_state()` or exact
  `RunState.from_json/from_string(...)` restoration tied to a proven agent. Local fixtures plus real
  OpenAI Agents Python HITL examples raise the public IR truth set to 2,018 labels.
- Added OpenAI Agents Python approval-decision persistence metadata. Exact
  `always_approve`/`always_reject` keywords on proven SDK `state.approve(...)` and
  `state.reject(...)` calls now record sticky, per-call, or dynamic decision persistence based on
  literal booleans and stable same-function boolean bindings. Local sticky fixtures plus the real
  OpenAI shell HITL example raise the public IR truth set to 2,023 labels, and schema-v128 engine
  results report 117 Python run-state approval decisions, including six sticky and two dynamic
  persistence decisions.
- Added custom rejection-message provenance for OpenAI Agents run-state reject decisions. Python
  `rejection_message=` and TypeScript `{ message }` reject options now record custom message
  presence plus literal, literal-binding, template, or dynamic source classification without storing
  message text. Local Python/TypeScript fixtures, the real OpenAI Agents Python custom-rejection
  HITL example, and the real OpenAI Agents JS `computer-use-hitl.ts` helper-parameter HITL example
  raise the public IR truth set to 2,038 labels, and schema-v130 engine results report custom
  message source counts plus TypeScript helper-parameter decision counts.
- Validation for the helper-parameter slice passed focused scanner tests, focused 6/6 IR labels,
  full 2,038/2,038 IR labels, 71/71 engine repositories, checked benchmark verification, full
  `pytest -q` (298 passed), touched-file `ruff`, JSON parsing, diff whitespace checks, and
  `uv build` plus distribution smoke/source verification.
- Added helper-derived OpenAI Agents JS run-state resume continuity using the same narrow
  helper-parameter proof shape: non-exported same-file async helper, first parameter typed as the
  exact SDK `Agent` import, proven `run(agentParam, ...) -> result.state`, and resumed
  `run(agentParam, state)`. The local lexical-scope fixture and real `computer-use-hitl.ts`
  `runWithHitl(agent, ...)` call sites now emit call-line-qualified `conversation-continuity`
  controls plus configured-by resume edges.
- The public IR truth set now passes 2,044/2,044 labels. Schema-v131 engine results report
  TypeScript OpenAI run-state continuity separately from approval decisions: 8 continuity controls,
  2 helper-parameter state resumes, 8 configured-by resume edges, and 2 helper-parameter resume
  edges.
- Validation for the helper-resume slice passed the focused scanner test, focused 12/12 helper IR
  labels, full 2,044/2,044 IR labels, 71/71 engine repositories, checked benchmark verification,
  full `pytest -q` (298 passed), touched-file `ruff`, JSON parsing, diff whitespace checks, and
  `uv build` plus distribution smoke/source verification.
- Added twelve real OpenAI Agents JS built-in-tool approval labels for
  `examples/docs/tools/localBuiltInTools.ts` and `examples/tools/apply-patch.ts`: approval-enabled
  `shellTool` and `applyPatchTool` components, their `human-approval` governed-by edges, their
  reachable `Local tools agent`/`Patch Assistant` tool-use edges, and editor-backed local filesystem
  write capability evidence for literal `applyPatchTool({ editor, ... })` options.
- The public IR truth set now passes 2,062/2,062 labels (1,543 positives and 519 negatives). The
  focused OpenAI built-in shell/apply-patch label slice passes 12/12.
- Validation for the apply-patch local-filesystem slice passed touched-file `ruff`, focused scanner
  and CLI tests (3 passed), focused OpenAI built-in shell/apply-patch IR labels (12/12), full
  2,062/2,062 public IR labels, full 71/71 engine benchmark refresh, checked benchmark
  verification, full `pytest -q` (298 passed), JSON parsing, diff whitespace checks, and `uv build`
  plus distribution smoke/source verification.
- Added TypeScript same-class weak path-prefix detection for editor-style helper methods. The
  scanner now records `path-prefix-check` controls for writes using a path assigned from
  `await this.resolve(...)` when that helper returns a `path.resolve(this.root, input)` candidate
  after a throwing `candidate.startsWith(this.root)` rejection; it keeps unchecked same-class writes
  unresolved. Focused local/real TypeScript path labels pass 8/8.
- Validation for the TypeScript same-class path-prefix slice passed touched-file `ruff`, focused
  scanner/CLI tests (2 passed), focused TypeScript path labels (8/8), full 2,062/2,062 public IR
  labels, full 71/71 engine benchmark refresh, checked benchmark verification, full `pytest -q`
  (298 passed), JSON parsing, diff whitespace checks, and `uv build` plus distribution smoke/source
  verification.
- Added exact OpenAI Agents JS history-feedback continuity. The scanner now links a run to
  `result.history` when the same exact SDK call consumes a caller/loop-owned history binding and
  refreshes that binding from its own history result; local fixtures cover loop-owned `inputs` and
  `thread.concat(...)`, and the real `examples/docs/running-agents/chatLoop.ts` example pins the
  caller-owned helper shape. Focused history-feedback labels pass 6/6, full public IR labels pass
  2,068/2,068, checked benchmark verification passes, and the full 71/71 engine benchmark refresh
  now reports 2,788 relationships.
- Added exact same-file OpenAI Agents JS agent-alias attribution for direct identifier aliases
  feeding run/session analysis. Alias candidates reuse lexical scope and reassignment checks, which
  recovers the real routed `examples/agent-patterns/routing.ts` `let agent: Agent<...> =
  triageAgent` loop without accepting rebound aliases. Focused alias labels pass 6/6, former
  OpenAI sandbox/helper and run-state restore regressions pass focused checks.
- Added exact OpenAI Agents JS trace correlation inventory for imported `withTrace` callbacks
  containing source-proven SDK `run(agent, ...)` calls. `groupId` emits `trace-group` evidence,
  `traceId` emits `trace-id` evidence, and imported `generateTraceId()` bindings preserve generated
  trace-ID plus logged OpenAI platform URL metadata. Focused trace labels pass 12/12, full public
  IR labels pass 2,086/2,086, and the full schema-v135 engine benchmark refresh passes 71/71
  repositories with 2,792 relationships and 10,557 symbolized components.
- Added exact OpenAI Agents JS Runner-level `groupId` trace correlation inventory. Stable exact
  `new Runner({ groupId })` instances now emit `trace-group` controls and configured-by edges when
  a later same-instance `.run(agent, ...)` call supplies a source-proven agent. Focused trace-group
  labels pass 10/10, full public IR labels pass 2,091/2,091, and the full schema-v136 engine
  benchmark refresh passes 71/71 repositories with 2,793 relationships and 10,558 symbolized
  components.
- Added exact OpenAI Agents JS Runner-level tracing-disablement inventory. Stable exact
  `new Runner({ tracingDisabled: true })` instances now emit `tracing-disabled` controls and
  configured-by edges when a later same-instance `.run(agent, ...)` call supplies a source-proven
  agent. Focused tracing-disabled labels pass 8/8, full public IR labels pass 2,099/2,099, and the
  full schema-v137 engine benchmark refresh passes 71/71 repositories with 2,795 relationships and
  10,560 symbolized components.
- Added exact OpenAI Agents JS delegated `asTool({ runConfig: { tracingDisabled: true } })`
  inventory. The scanner now emits `tracing-disabled` controls on the delegated agent, preserves
  parent/orchestrator and tool-name provenance, and leaves explicit `false` unresolved. Focused
  tracing-disabled labels pass 15/15, full public IR labels pass 2,106/2,106, and the full
  schema-v138 engine benchmark refresh passes 71/71 repositories with 2,797 relationships and
  10,562 symbolized components.
- Added exact OpenAI Agents JS delegated `asTool({ runOptions: { maxTurns } })` turn-limit
  inventory. Literal numeric `maxTurns` values now emit `agent-turn-limit` controls on the delegated
  agent with parent-agent and tool-name provenance, while missing or nonliteral values stay
  unresolved. Focused turn-limit labels pass 9/9, full public IR labels pass 2,115/2,115, and the
  full schema-v139 engine benchmark refresh passes 71/71 repositories with 2,800 relationships and
  10,565 symbolized components.
- Added exact OpenAI Agents JS delegated `asTool({ runConfig: { model, modelSettings } })` model
  override inventory. Literal or immutable module-level model strings now emit
  `agent-model-override` controls on the delegated agent with parent-agent, tool-name, provider, and
  shallow literal reasoning/verbosity settings when present. Focused model-override labels pass 5/5,
  full public IR labels pass 2,120/2,120, and the full schema-v140 engine benchmark refresh passes
  71/71 repositories with 2,801 relationships and 10,566 symbolized components.
- Added exact OpenAI Agents JS delegated `asTool({ runConfig: { workflowName } })` trace-workflow
  inventory. Literal or immutable module-level workflow names now emit `trace-workflow` controls on
  the delegated agent with parent-agent and tool-name provenance, while missing or nonliteral values
  stay unresolved. Focused workflow-name labels pass 7/7, full public IR labels pass 2,127/2,127,
  and the full schema-v141 engine benchmark refresh passes 71/71 repositories with 2,803
  relationships and 10,568 symbolized components.
- Added exact OpenAI Agents JS Runner-level `workflowName` trace-workflow inventory. Stable exact
  `new Runner({ workflowName })` instances now emit `trace-workflow` controls and configured-by
  edges for each later same-instance `.run(agent, ...)` call with a source-proven agent, while
  reassigned runners stay unresolved. Focused runner workflow-name labels pass 15/15, full public
  IR labels pass 2,142/2,142, and the full schema-v142 engine benchmark refresh passes 71/71
  repositories with 2,807 relationships and 10,572 symbolized components.
- Added exact OpenAI Agents JS direct and stable Runner run-call `maxTurns` inventory. Literal
  numeric `maxTurns` in exact imported `run(agent, ..., { maxTurns })` and stable
  `runner.run(agent, ..., { maxTurns })` calls now emit `agent-turn-limit` controls on
  source-proven agents, while missing and nonliteral values stay unresolved. Focused run-turn labels
  pass 13/13, full public IR labels pass 2,155/2,155, and the full schema-v143 engine benchmark
  refresh passes 71/71 repositories with 2,825 relationships and 10,590 symbolized components.
- Added exact OpenAI Agents JS Agent-level `modelSettings.toolChoice` inventory. Literal or
  immutable module-level string `toolChoice` settings on exact imported `new Agent(...)`
  configurations now emit `tool-choice-policy` controls on the source agent, while mutable
  bindings stay unresolved. Focused Agent tool-choice labels pass 7/7, full public IR labels pass
  2,162/2,162, and the full schema-v144 engine benchmark refresh passes 71/71 repositories with
  2,836 relationships and 10,601 symbolized components.
- Added exact OpenAI Agents JS Runner-level `modelSettings.toolChoice` inventory. Stable exact
  `new Runner({ modelSettings: { toolChoice } })` instances now emit per-run
  `tool-choice-policy` controls and configured-by edges when later same-instance `.run(agent, ...)`
  calls supply source-proven agents, while reassigned runners stay unresolved. Focused Runner
  tool-choice labels pass 7/7, full public IR labels pass 2,169/2,169, and the full schema-v145
  engine benchmark refresh passes 71/71 repositories with 2,840 relationships and 10,605
  symbolized components.
- Added exact OpenAI Agents JS `computerTool({ computer })` backend lifecycle inventory.
  `computer: { create, dispose }` object factories now record create/dispose-per-run lifecycle
  evidence, create-only factories record missing disposal, and shorthand/external computer bindings
  stay external-binding metadata rather than inferred ownership. Focused approval-control labels
  pass 116/116, full public IR labels pass 2,175/2,175, and the full schema-v146 engine benchmark
  refresh passes 71/71 repositories with 2,840 relationships and 10,605 symbolized components.
- Added exact OpenAI Agents JS Agent-level `modelSettings.reasoning.effort` and
  `modelSettings.text.verbosity` inventory. Literal nested settings now emit
  `model-settings-policy` controls and configured-by edges on the source agent, while mutable
  nested settings stay unresolved. Focused Agent model-settings labels pass 7/7, full public IR
  labels pass 2,182/2,182, and the full schema-v147 engine benchmark refresh passes 71/71
  repositories with 2,846 relationships and 10,611 symbolized components.
- Added exact OpenAI Agents JS hosted web-search policy inventory. Literal
  `webSearchTool({ filters.allowedDomains, searchContextSize, userLocation })` settings now emit
  `web-search-policy` controls on the source tool and matching `external-action` capability
  metadata; literal `Agent.modelSettings.providerData.include` arrays emit `provider-data-policy`
  controls and mark source inclusion for `web_search_call.action.sources`. Dynamic domain/context
  user-location and provider-data include bindings stay unresolved. Focused web-search policy
  labels pass 19/19, full public IR labels pass 2,201/2,201, and the full schema-v149 engine
  benchmark refresh passes 71/71 repositories with 2,850 relationships and 10,615 symbolized
  components.
- Added exact OpenAI Agents JS Agent-level `modelSettings.parallelToolCalls` inventory. Literal
  boolean settings now emit `model-settings-policy` controls and configured-by edges on the source
  agent, while dynamic values stay unresolved. The pinned OpenAI Agents JS `tool-search.ts` example
  contributes two real sequential-tool-call settings. Focused Agent model-settings labels pass
  16/16, full public IR labels pass 2,210/2,210, and the full schema-v150 engine benchmark
  refresh passes 71/71 repositories with 2,852 relationships and 10,617 symbolized components.
- Added exact OpenAI Realtime `RealtimeSession({ config.parallelToolCalls })` inventory.
  Source-proven `RealtimeAgent` constructors are now recognized, and literal RealtimeSession
  boolean concurrency settings emit `realtime-session-config-policy` controls and configured-by
  edges linked to the session's first-agent argument while dynamic values stay unresolved. Focused
  RealtimeSession config labels pass 7/7, full public IR labels pass 2,217/2,217, and the full
  schema-v151 engine benchmark refresh passes 71/71 repositories with 2,859 relationships and
  10,643 symbolized components.
- Extended OpenAI Realtime `RealtimeSession` config inventory to exact
  `config.reasoning.effort` string literals on the same source-proven session config policy. The
  local realtime fixture now covers a reasoning-only positive, and the pinned voice-agent
  `configureSession.ts` example contributes both low reasoning and parallel tool-call metadata on
  one session config control. Focused RealtimeSession config labels pass 9/9, full public IR labels
  pass 2,219/2,219, and the full schema-v152 engine benchmark refresh passes 71/71 repositories
  with 2,859 relationships and 10,643 symbolized components.
- Extended OpenAI Realtime `RealtimeSession` audio transcription config inventory to exact literal
  prompts and keywords on the same source-proven session config policy. The IR records literal
  prompt presence and length, not prompt content, plus literal keyword arrays/counts; dynamic prompt
  and keyword bindings remain unresolved. Focused RealtimeSession config labels pass 17/17 and full
  public IR labels pass 2,227/2,227.
- Extended OpenAI Realtime `RealtimeSession` inventory to exact top-level session model literals on
  the same source-proven session config policy. Dynamic session model bindings remain unresolved;
  the pinned `configureSession.ts` example now records `gpt-realtime-2.1` alongside audio/reasoning
  metadata. Focused RealtimeSession config labels pass 18/18 and full public IR labels pass
  2,228/2,228.
- Extended exact OpenAI Realtime session model inventory to model-only session options without a
  `config` object. The local fixture covers a model-only positive and dynamic model-only negative,
  and the pinned `sendMessage.ts` example proves official docs coverage. Focused RealtimeSession
  config labels pass 23/23, full public IR labels pass 2,233/2,233, and the full schema-v157
  engine benchmark refresh passes 71/71 repositories with 2,867 relationships and 10,651
  symbolized components.
- Extended exact OpenAI Realtime turn-detection inventory to
  `config.audio.input.turnDetection.type/eagerness/createResponse/interruptResponse`. Dynamic
  turn-detection bindings remain unresolved, and the pinned `turnDetection.ts` docs example is
  covered through narrow exported sibling `RealtimeAgent` import resolution back to `agent.ts`.
  Focused RealtimeSession config labels pass 29/29, full public IR labels pass 2,239/2,239, and
  the full schema-v158 engine benchmark refresh passes 71/71 repositories with 2,868
  relationships and 10,652 symbolized components.
- Extended exact OpenAI Realtime session option composition to one narrow spread shape:
  `const sessionOptions: Partial<RealtimeSessionOptions> = { ... }` feeding
  `new RealtimeSession(agent, { ...sessionOptions })`. The resolver refuses direct
  `model`/`config` overrides, unknown or multiple spreads, and later reassignment/mutation of the
  typed options binding. The local spread fixture covers stable positive and dynamic negative
  options, while pinned `sipTransport.ts` proves real spread-derived model/turn-detection policy.
  Focused RealtimeSession config labels pass 34/34, full public IR labels pass 2,244/2,244, and
  the full schema-v159 engine benchmark refresh passes 71/71 repositories with 2,869
  relationships and 10,653 symbolized components.

## Current findings

- The rule catalog is now the authoritative runtime source for reporting metadata and policy rule
  validation. Keeping schemas synchronized with `RULE_CATALOG` prevents generated policy/editor
  tooling from drifting.
- Editor/CI contract export is now an installed-package behavior. Integrations can ask any
  AgentVerify installation for a digest-manifested report schema, rules schema, current rules
  catalog, and optional sample report without relying on source-tree scripts.
- Editor diagnostic integrations should preserve `result_kind`, `confidence`, `fingerprint`, and
  `ir_path` in diagnostic metadata; otherwise they lose the distinction between review signals,
  policy-gated findings, and rerun correlation.
- CI policy-gate examples should stay separate from SARIF upload workflows so deliberate policy
  failures do not prevent diagnostic ingestion.
- Baseline handling is intentionally conservative: malformed recognized artifacts are usage errors;
  partial selected-path scans do not claim no-longer-reported counts.
- TypeScript model binding now has one bounded composition rule: direct quoted constants and
  module-level backtick templates whose interpolations are all earlier immutable literal constants
  can carry exact model provenance; other expression forms are withheld rather than guessed.
- Code-scanning adoption artifacts now distinguish two local examples: SARIF upload belongs in the
  copyable `examples/github-code-scanning.yml` workflow with `security-events: write`, while
  enforcement-only gates belong in `examples/github-policy-gate.yml` without code-scanning upload
  permissions.
- The checked SARIF example preserves the same integration metadata GitHub receives from the CLI:
  rule descriptors, `agentverify/v1` partial fingerprints, source locations, result kind,
  confidence, analysis details, and Agent IR paths.
- Benchmark release-claim guardrails now have a copyable CI artifact, not just prose and this
  repository's internal CI: `examples/github-benchmark-verify.yml` uses only read permission and
  archives schema-validated installed CLI verifier JSON for release review.
- Editor/CI contract manifests now identify each artifact's role directly through `kind`,
  `contract`, and `required` fields while retaining SHA-256 digests for reproducibility.
- The editor/CI contract manifest is now itself schema-backed via `agentverify schema
  editor-contract-manifest`, matching the broader installed machine-contract pattern.
- Copied editor/CI contract bundles can now be independently verified with `agentverify contracts
  --verify-dir`, giving downstream tools a fail-closed integrity check before loading schemas or rule
  catalogs.
- Contract-bundle artifact paths are intentionally basename-only; invalid manifest paths are reported
  as verification failures before any artifact file is read.
- Contract-bundle verification output is now itself schema-backed via `agentverify schema
  editor-contract-verification`, so editor bootstrap and CI logging code can validate verifier JSON
  the same way they validate exported manifests.
- Verifier failure output should stay consumable even when manifest metadata fields are malformed;
  invalid `kind`, `contract`, and `required` values are normalized to `null` in artifact results.
- Benchmark release evidence now has two installable contracts: `benchmark-result` for measured
  result files and `benchmark-verification` for the release-gate artifact emitted after digest,
  outcome, and claim-boundary checks.
- Benchmark release tooling now has a checked verifier-output example, not only a workflow recipe:
  `examples/benchmark-verification.json` matches the current `agentverify benchmark verify
  --require-evaluation-kind public-regression --require-all-passed` output and is source-release
  required.
- Source-release verification now protects both public sealed-holdout templates:
  `holdout-manifest.template.json` for samples and `holdout-labels.template.json` for adjudicated
  label shape.
- Sealed-holdout setup templates are now machine contracts: installed CLIs expose
  `agentverify schema holdout-manifest` and `agentverify schema holdout-labels`, and the checked
  templates validate against those schemas before any private labels are introduced.
- Holdout setup validation is now an installed CLI behavior: `agentverify holdout validate` validates
  manifest and/or labels files with the bundled schemas and reports per-file schema/parse/read errors
  without claiming sealed benchmark success or trust authenticity.
- Benchmark release workflows should validate setup artifacts and result artifacts separately:
  `agentverify holdout validate` catches manifest/label shape drift, while `agentverify benchmark
  verify` checks generated result JSON, digests, outcomes, and claim-boundary gates.
- Benchmark result JSON now distinguishes detection failures from label freshness failures:
  `failure_summary.observation_mismatch` tracks expected-versus-observed scanner mismatches, while
  `anchor_mismatch` and `source_mismatch` expose stale anchors or expected source snippets that can
  otherwise be hidden by unchanged precision/recall metrics.
- Python registered-class network propagation now accepts exact `module_alias.ClassName()` calls only
  when `module_alias` resolves to one local imported module and is unrebound in the method; locally
  shadowed module aliases, mutable fields, duplicate classes, and rebound constructors remain
  unresolved.
- Python filesystem callable aliasing is deliberately narrow: local alias chains may copy already
  proven same-function callable bindings, but aliases before source proof, rebound alias targets,
  incompatible operation families, and imported wrapper helpers remain unresolved.
- OpenAI Agents JS delegated-agent approvals live on the adapter edge, not on a separate delegated
  tool component yet. This preserves source/target agent identity while still exposing
  `approval_policy`, `approval_handler`, and `approval_decision` metadata for `asTool` governance
  review.
- OpenAI Agents JS approval-state handling is now separate from approval-policy declaration:
  `needsApproval` metadata says a tool/delegated tool may require approval, while
  `approval-decision` controls prove source-visible SDK state approval/rejection handling. Exact
  approval decisions now cover TypeScript direct run-result state, bound state, narrowly restored
  `RunState.fromString(...)` state, and Python `result.to_state()`/`RunState.from_json` state when
  the SDK chain is proven.
- OpenAI Agents JS serialized run-state restoration can be source-proven for simple same-file
  file-persistence flows. The scanner intentionally requires literal file names and matching agent
  identity, so arbitrary strings passed to `RunState.fromString` remain unresolved.
- OpenAI Agents JS builtin approval-capable tools now share the generic-tool approval distinction:
  literal `needsApproval: true` proves always-enabled approval metadata, while callback-valued
  `needsApproval` is callback-controlled policy evidence, not unresolved handler evidence and not
  full human-approval coverage until predicate/action coverage is analyzed.
- OpenAI Agents JS `applyPatchTool({ editor, ... })` with literal options is editor-backed local
  filesystem write capability evidence; nonliteral `applyPatchTool(options)` remains unresolved.
- The first OpenAI Agents JS predicate-quality inventory is intentionally literal and shallow:
  `field.startsWith("literal")`, `field.includes("literal")`, and
  `["literal"].includes(action.field)` are recorded, while compound conditions, helper calls, and
  nonliteral values remain callback-controlled without predicate attributes.
- OpenAI Agents JS `withTrace(..., { groupId })`, stable exact `new Runner({ groupId })`,
  `withTrace(..., { traceId })`, stable exact `new Runner({ tracingDisabled: true })`, and exact
  delegated `agent.asTool({ runConfig: { tracingDisabled: true } })` calls are now represented as
  separate trace/observability governance evidence, not conversation memory. Delegated
  `agent.asTool({ runOptions: { maxTurns } })` calls additionally expose bounded delegated-run
  execution as `agent-turn-limit` controls, and delegated
  `agent.asTool({ runConfig: { model } })` calls expose model override policy as
  `agent-model-override` controls. Delegated
  `agent.asTool({ runConfig: { workflowName } })` calls expose workflow naming policy as
  `trace-workflow` controls, and stable exact `new Runner({ workflowName })` instances expose
  Runner-level workflow naming for source-proven `.run(agent, ...)` calls. Exact direct
  `run(agent, ..., { maxTurns })` and stable exact `runner.run(agent, ..., { maxTurns })` calls
  expose per-run execution bounds as `agent-turn-limit` controls on source-proven agents. Exact
  `new Agent({ modelSettings: { toolChoice } })` settings expose source-agent tool-choice policy as
  `tool-choice-policy` controls, and stable exact
  `new Runner({ modelSettings: { toolChoice } })` instances expose per-run tool-choice policy for
  source-proven `.run(agent, ...)` calls. Exact Agent-level literal
  `modelSettings.reasoning.effort`, `modelSettings.text.verbosity`, and
  `modelSettings.parallelToolCalls` values expose `model-settings-policy` controls. Exact imported
  RealtimeSession options/config with top-level session model including model-only options,
  `parallelToolCalls`,
  `reasoning.effort`, literal
  `outputModalities`, literal audio input/output formats, and literal audio transcription
  model/delay/languages plus privacy-preserving prompt/keyword metadata, and literal
  `audio.input.turnDetection.type/eagerness/createResponse/interruptResponse` exposes
  `realtime-session-config-policy` controls linked to source-proven RealtimeAgents. Narrow
  same-repository named sibling imports resolve only when the target exports one exact
  `RealtimeAgent`, covering the pinned OpenAI Agents JS `turnDetection.ts` example without
  broadening into arbitrary spread/config composition. Exact imported
  `RealtimeSession` bindings such as `import { session } from './agent'` now resolve only when the
  sibling target exports one exact `new RealtimeSession(sourceAgent, ...)` whose source agent is a
  proven `RealtimeAgent`; this supports exact `tool_approval_requested` event decisions without
  treating lookalike `.on(...)` objects as SDK evidence. Realtime event handlers now emit
  `approval-decision` controls only for callback request parameters passed as
  `session.approve(request.approvalItem)` or `session.reject(request.approvalItem)`.
  Exact Realtime `session.connect({ apiKey })` calls now emit `realtime-session-auth-policy`
  controls when the receiver is a proven `RealtimeSession`, with redacted classification for
  literal placeholders, literal ephemeral `ek_` client secrets, `process.env.OPENAI_API_KEY`
  server-key environment usage, fetch-derived ephemeral-key bindings, dynamic bindings, and direct
  literal/custom-constructor transport context such as `websocket` or `OpenAIRealtimeSIP`.
  Exact imported
  `withTrace` callbacks containing
  source-proven SDK `run(agent, ...)` calls, exact Runner instances with source-proven
  `.run(agent, ...)` calls, and exact delegated-agent `asTool` adapters emit `trace-group`,
  `trace-id`, `tracing-disabled`, `agent-turn-limit`, `agent-model-override`, or
  `trace-workflow` controls and configured-by edges, while exact Agent settings emit
  `tool-choice-policy` and `model-settings-policy` configured-by edges.

## Blockers

- External publishing, trust-root configuration, issue creation, and repository-access-dependent
  work are intentionally deferred until the user grants access or explicit authorization.

## Next action

Continue toward the highest-value local P1/P2 work: additional exact OpenAI Agents JS sandbox or
session-governance policy fields, approval predicate/action quality, real-world framework coverage
without broad name matching, concrete CI/editor integration fixtures, benchmark performance work, or
release-artifact checks that stay local until release publishing is explicit. For OpenAI session
work, keep local `MemorySession`, server-managed `conversationId`, `previousResponseId`,
same-block `result.history`, same-file `result.state`, and serialized `RunState.fromString` resume
semantics distinct from trace-correlation `withTrace(..., { groupId/traceId })` and stable
`Runner({ groupId })` evidence, plus explicit tracing disablement through stable
`Runner({ tracingDisabled: true })`, delegated
`asTool({ runConfig: { tracingDisabled: true } })`, and delegated
`asTool({ runOptions: { maxTurns } })`, `asTool({ runConfig: { model } })`, and
`asTool({ runConfig: { workflowName } })`, plus stable
`Runner({ workflowName })` runner-level workflow evidence and exact direct/stable Runner
`run(..., { maxTurns })` per-run turn-limit evidence, plus exact Agent
  `modelSettings.toolChoice` evidence and stable Runner-level `modelSettings.toolChoice` per-run
  evidence, plus exact `computerTool({ computer })` backend lifecycle metadata for external
  bindings, inline static objects, create/dispose per-run factories, and create-only factories, plus
  exact Agent-level `modelSettings.reasoning.effort`, `modelSettings.text.verbosity`, and
  `modelSettings.parallelToolCalls` metadata, plus exact RealtimeSession top-level `model`
  including model-only session options,
  `config.parallelToolCalls`, `config.reasoning.effort`, literal `config.outputModalities`, audio
  input/output format, and audio transcription model/delay/languages plus privacy-preserving
  prompt/keyword policy, plus exact literal
  `config.audio.input.turnDetection.type/eagerness/createResponse/interruptResponse` policy
  through direct same-file agents, narrow exported sibling `RealtimeAgent` imports, or one exact
  typed `Partial<RealtimeSessionOptions>` spread, plus exact
  `tool_approval_requested` event approval/rejection decisions through direct or narrow exported
  sibling `RealtimeSession` bindings, plus exact `session.connect({ apiKey })` auth-source evidence
  through direct `RealtimeSession` bindings. For OpenAI
approval work, keep literal always-approval, callback-controlled
approval on generic tools/delegated tools/approval-capable builtin tools, delegated-agent adapter
approval metadata, literal predicate metadata, SDK state approval decisions, helper-parameter
  decision provenance, and proven human approval/resume handling separate. For performance work, use
`--progress` plus focused
`--scan-label-paths` only when the target labels are self-contained; broader benchmark acceleration
likely needs dependency-aware path expansion or scan-result reuse to preserve cross-file evidence.

## Latest local milestone

- Added exact TypeScript OpenAI Realtime output-guardrail inventory. Proven
  `new RealtimeSession(agent, { outputGuardrails, outputGuardrailSettings })` options now emit
  `realtime-session-guardrail-policy` controls linked to the source `RealtimeAgent`, including
  inline arrays, typed `RealtimeOutputGuardrail[]` const arrays, typed `RealtimeSessionOptions`
  spreads, literal guardrail names/counts, and signed integer `debounceTextLength` values. Dynamic
  debounce values, mutated guardrail arrays, comment-only placeholders, and lookalike objects remain
  bounded. Public IR truth set: 2,276/2,276. Engine benchmark: 71/71 repositories, 2,880
  relationships, 10,664 symbolized components.
- Added exact TypeScript OpenAI Agents SDK Agent-level input/output guardrail inventory. Proven
  `new Agent({ inputGuardrails })` and `new Agent({ outputGuardrails })` constructor options,
  including `new Agent<...>(...)` generics, now emit `agent-guardrail-policy` controls linked to the
  source agent. Inline arrays, typed `InputGuardrail`/`OutputGuardrail` object bindings including
  generic `OutputGuardrail<typeof schema>` forms, literal names/counts, and binding-only fallbacks
  are covered; dynamic arrays, mutated guardrail objects, and object lookalikes remain bounded.
  Public IR truth set: 2,292/2,292. Engine benchmark: 71/71 repositories, 2,894 relationships,
  10,683 symbolized components.

# AgentVerify decisions

## Rule catalog is a machine contract

- Decision: Treat the runtime rule catalog as an externally consumable schema-versioned contract.
- Evidence: `agentverify rules --format json` already emits `schema_version: 1`; policies and SARIF
  descriptors depend on the same rule metadata. Generated CI/editor integrations need validation
  without scraping documentation.
- Alternative: Leave rules JSON self-describing only. Rejected because it creates a weaker contract
  than reports, BOMs, and policies.
- Revisit when: rule metadata needs nested examples, tags, CWE/CAPEC-style mappings, or standard
  references that require a schema version bump.

## Baselines must fail closed

- Decision: Unknown JSON objects and malformed recognized baseline entries are usage errors.
- Evidence: An empty or partially parsed baseline can silently hide the fact that known-debt
  suppression did not apply. Recent tests cover raw lists, JSON reports, native AI BOMs, and SARIF.
- Alternative: Ignore malformed entries. Rejected because CI would appear green while evaluating a
  different debt set than intended.
- Revisit when: a migration tool exists that can explicitly normalize older report artifacts.

## Policy trust roots start as local digest allowlists, not signatures

- Decision: Add `local-content-digest-allowlist` policy trust roots as a fail-closed local content
  approval mechanism while keeping `signature_verified: false`.
- Evidence: `agentverify policy` already exposes composed policy sources and SHA-256 digests.
  Teams can use those digests in CI before full author/signature infrastructure exists, but a digest
  alone only proves byte identity, not who approved or produced the file.
- Alternative: Call digest matches "signed" or "verified" provenance. Rejected because it would
  overclaim authenticity and weaken future cryptographic trust semantics.
- Revisit when: cryptographic signed policy provenance has a concrete key/trust-root design and
  migration path from digest allowlists.

## Signed policy provenance should sign source digests

- Decision: Design cryptographic policy provenance around detached signatures over a manifest
  of exact composed policy source digests, not over normalized policy objects.
- Evidence: Current policy summaries already preserve source paths and SHA-256 bytes for every
  composed policy. Signing those byte digests avoids JSON canonicalization ambiguity and lets teams
  migrate from existing digest allowlists without changing policy composition semantics.
- Alternative: Sign normalized policy JSON or only the root policy digest. Rejected because
  normalization rules are easy to drift and root-only signatures can hide unapproved base-policy
  substitutions unless the composition graph is separately pinned.
- Revisit when: threshold signatures or a rule-catalog-version binding become necessary.

## Signed policy verification uses local Ed25519 key trust roots

- Decision: Implement policy signature verification with `cryptography` Ed25519 support and a
  fail-closed `local-key-signature` trust root, keeping it separate from digest allowlists.
- Evidence: AgentVerify already exports deterministic source-digest signing payload bytes. Verifying
  detached signatures over those bytes preserves exact source-byte provenance while avoiding policy
  JSON canonicalization drift. Local public-key trust roots keep CI offline and explicit.
- Alternative: Treat digest allowlist matches as signatures or make signature verification a remote
  trust service. Rejected because digest allowlists do not prove author authenticity, and remote
  trust would weaken offline reproducibility for the first implementation.
- Revisit when: threshold signatures, remote transparency logs, hardware-backed key attestations, or
  rule-catalog-version binding become concrete requirements.

## Benchmark release claims must be verifier-gated

- Decision: Treat benchmark result metadata as a release gate, not just explanatory JSON. Release
  workflows can require public-regression or sealed-holdout results, sealed status, label scope,
  manifest provenance, and all-labels-passed claims with `agentverify benchmark verify`; the
  source-checkout `scripts/verify_benchmark_results.py` wrapper delegates to the same verifier.
- Evidence: Checked-in public truth sets are visible during scanner development and therefore only
  support regression claims. The result schema already records `evaluation_kind`, `sealed`, digests,
  and `claim_scope`; enforcing those fields prevents accidental overclaiming. Recomputing
  outcome-derived counts and metrics prevents aggregate result fields from drifting away from
  per-label evidence. Binding outcomes back to the digested label ids, metric keys, and expected
  values prevents same-sized but unrelated outcome lists from satisfying the gate.
- Alternative: Keep claim boundaries in prose only. Rejected because release notes and package pages
  are easy to copy from aggregates while overlooking caveats.
- Revisit when: release automation exists and can attach verifier output artifacts directly to tags.

## Benchmark result schemas are installed contracts

- Decision: Expose the benchmark-result JSON schema through `agentverify schema benchmark-result` and
  include it in wheel verification.
- Evidence: Benchmark results are intended to be attached to release notes and downstream validation
  flows; installed users should not need a source checkout to get the exact contract. A test asserts
  the packaged schema stays byte-identical to `benchmarks/benchmark-results-v1.schema.json`.
- Alternative: Leave the schema only under `benchmarks/`. Rejected because it makes report/policy
  contracts installable while benchmark-result contracts remain source-tree-only.
- Revisit when: benchmark schemas move into a versioned package namespace or release automation
  publishes schema artifacts independently.

## Selected-label-path benchmark scans are development evidence only

- Decision: Allow `scripts/evaluate_truthset.py --scan-label-paths` to scan only files referenced by
  the evaluated labels, but record `benchmark.scan_scope: selected-label-paths` and surface that
  scope from benchmark verification.
- Evidence: Full public IR profiling showed roughly 482.5 seconds of timed scan work, mostly from
  large cached repositories with few labels. The selected-label-path experiment reduced timed scan
  work to roughly 57.5 seconds, and focused OpenAI sandbox labels still passed 235/235, but the full
  all-IR run failed 285 labels that require cross-file helper, import, reexport, or composition
  summaries.
- Alternative: Treat selected label paths as a drop-in benchmark acceleration. Rejected because that
  would silently weaken cross-file evidence and could make release claims incomparable with
  repository-wide scans.
- Revisit when: the evaluator can expand selected paths with dependency-aware helper/reexport files,
  or scanner result caching preserves repository-wide evidence while avoiding repeated parse work.

## Signed policy CI fixtures must use ephemeral keys

- Decision: Prove signed-policy verification in CI with a generated in-memory Ed25519 key and
  throwaway public artifacts, not a checked-in private key or a pretend organizational trust root.
- Evidence: The detached signature verifier only needs the exported signing payload bytes, a
  signature bundle, and a public-key trust root. A reusable helper can generate those public
  artifacts in a temporary directory, require `agentverify policy --signature --trust-root
  --require-trusted`, and report that private-key material was ephemeral-only. The default CI
  workflow and installed-wheel distribution smoke now both exercise that path.
- Alternative: Commit a sample private key or leave the walkthrough as prose only. Rejected because
  durable sample keys invite misuse, while prose-only examples can drift from the CLI behavior.
- Revisit when: real release automation has an explicit organization trust-root and detached
  signature publishing process.

## Pre-commit integration is a release artifact

- Decision: Treat the pre-commit manifest, setup guide, and copyable local config as source-release
  contract files rather than README-only convenience text.
- Evidence: The README advertises the bundled `.pre-commit-hooks.yaml` manifest and local setup path.
  If a source distribution omits either the manifest or guide, downstream users cannot reproduce the
  advertised hook workflow. The local config intentionally uses `language: system` for an installed,
  reviewed AgentVerify build before a public release URL exists, while the bundled hook uses
  `language: python` for future tagged releases.
- Alternative: Leave the manifest and guide untested. Rejected because pre-commit installation is an
  adoption path and can silently drift from the CLI threshold or repository-wide scan requirement.
- Revisit when: a public remote/tag exists and the docs switch from local-hook-first to
  tagged-release-first instructions.

## Editor integrations get generated contract bundles

- Decision: Provide a reproducible exporter for editor/CI contract artifacts instead of relying only
  on scattered CLI examples.
- Evidence: Editor extensions and review bots need the report schema, rules schema, current rule
  catalog, and representative report shape together. `agentverify schema ...` and `agentverify rules
  --format json` already expose the primitives, but a generated bundle with a digest manifest makes
  local integration and release verification easier to automate. Promoting the exporter to
  `agentverify contracts` makes the contract available from installed wheels, while the
  source-checkout script remains a wrapper. Tests validate the exported rule catalog and sample
  report against the bundled schemas, and installed-wheel smoke tests require the CLI command to
  write every expected artifact. A checked editor-diagnostics example derived from a real fixture
  documents how integrations should map evidence lines, severities, fingerprints, result kinds,
  confidence, and IR paths into LSP-style diagnostics.
- Alternative: Check in generated copies of the rule catalog and schemas. Rejected because generated
  copies would drift whenever rules or schemas change unless every catalog update also regenerated
  secondary artifacts.
- Revisit when: a published package or website hosts versioned schema URLs and editor plugins can
  fetch those directly.

## Policy-gate workflows are checked adoption artifacts

- Decision: Keep a copyable GitHub Actions policy-gate workflow under `examples/` and require it in
  source distributions.
- Evidence: Policy enforcement should be separate from SARIF upload so deliberate gate failures do
  not prevent diagnostic ingestion. A minimal workflow can use only `contents: read`, validate policy
  composition before scanning, emit compact summary output, and require expiry dates on inline
  suppressions. Tests now assert those properties and docs link to the workflow.
- Alternative: Leave the workflow as prose snippets in policy/code-scanning docs. Rejected because
  snippets are easy to copy incompletely and are not caught by release artifact verification.
- Revisit when: a hosted GitHub Action, reusable workflow, or release-pinned installation path
  replaces manual workflow copying.

## OpenAI MemorySession is conversation-state evidence, not sandbox runtime evidence

- Decision: Model exact OpenAI Agents JS `MemorySession({ sessionId })` as a
  `conversation-session` control and link agents to it from top-level `session` run options, while
  keeping sandbox `{ session }` bindings under `sandbox-runtime` only when they derive from a proven
  sandbox client/session.
- Evidence: Pinned `openai/openai-agents-js` examples use both concepts together:
  `conversation-identity.ts` passes a `MemorySession` through top-level `session` while also passing
  a sandbox runtime session through `sandbox.session`; `memory-multi-agent-multiturn.ts` uses two
  named `MemorySession` instances across repeated sandboxed runs. Treating both as one control would
  blur durable conversation memory with execution-environment selection.
- Alternative: Reuse `sandbox-state-persistence` or `sandbox-runtime` controls. Rejected because
  those controls describe sandbox filesystem/session behavior, not agent conversation identity or
  continuity.
- Revisit when: OpenAI Agents JS exposes additional session implementations with materially
  different persistence or external storage semantics that deserve separate control names or
  attributes.

## OpenAI server conversation IDs require source proof from the OpenAI SDK

- Decision: Treat top-level `conversationId` run options as `conversation-session` evidence only
  when the identifier is destructured from `client.conversations.create(...)` and `client` is a
  stable default-endpoint `new OpenAI()` instance from the exact `openai` package.
- Evidence: The pinned OpenAI Agents JS `examples/docs/running-agents/conversationId.ts` example
  creates a server-managed conversation via the native SDK and passes the same `conversationId` to
  repeated `run(...)` calls. A variable named `conversationId` alone is too weak: it could be an
  arbitrary string, reassigned value, or unrelated application ID.
- Alternative: Accept any `conversationId` property passed to `run(...)`. Rejected because that
  would turn naming convention into provider-state evidence and likely create false positives in
  applications with their own conversation IDs.
- Revisit when: additional official examples show safe, exact aliases such as object-property
  conversation results (`conversation.id`) that can be tied back to `conversations.create(...)`
  without broad flow analysis.

## OpenAI previousResponseId requires proof from a prior run result

- Decision: Treat OpenAI Agents JS `previousResponseId` options as conversation-continuity evidence
  only when the ID binding is derived from `.lastResponseId` on a stable result variable assigned by
  an exact imported `run(agent, ...)` call.
- Evidence: The pinned `examples/docs/running-agents/previousResponseId.ts` example creates
  `first = await run(agent, ...)`, then derives `previousResponseId = first.lastResponseId`, then
  passes that value to a later `run(...)`. This proves continuity through SDK result state without
  relying on arbitrary identifier names.
- Alternative: Accept any literal/string variable passed as `previousResponseId`. Rejected because
  a string-shaped ID does not prove it belongs to the OpenAI Agents SDK's previous-response
  continuity mechanism.
- Revisit when: official examples show exact inline forms such as
  `{ previousResponseId: first.lastResponseId }` or continuity through saved run state that can be
  modeled without broad interprocedural flow.

## OpenAI run history continuation requires local result-history proof

- Decision: Treat OpenAI Agents JS `result.history` handoff as `conversation-continuity` evidence
  only when an input binding is assigned from `.history` on a stable result variable returned by an
  exact imported `run(agent, ...)` call, and a later same-file `run(agent, inputBinding)` or
  `runner.run(agent, inputBinding)` consumes that binding before reassignment.
- Evidence: Pinned OpenAI Agents JS examples include `examples/tools/web-search.ts`, where
  `messages = result.history` is extended and passed to a second `run`, and
  `examples/agent-patterns/llm-as-a-judge.ts`, where `inputItems = storyOutlineResult.history` is
  passed to an evaluator run. Local positives cover both direct imported `run` and `Runner.run`;
  local negatives pin loose arrays, unknown run functions, and reassigned history inputs.
- Alternative: Treat any array passed as the second `run` argument as conversation continuity.
  Rejected because OpenAI Agents run inputs can also be fresh user messages; continuity requires
  proof that the input was returned by SDK history.
- Revisit when: same-file helper/caller state flow can be modeled narrowly enough to cover
  chat-loop patterns such as `thread = result.history` across repeated function calls without
  accepting arbitrary mutable state as continuity evidence.

## OpenAI run-state resume requires prior SDK run-state proof

- Decision: Treat OpenAI Agents JS `result.state` resume as `conversation-continuity` evidence only
  when the state expression or state binding is sourced from a prior exact OpenAI Agents `run(...)`
  or `Runner.run(...)` result in the same file and the source is not made stale before use. A
  same-statement assignment such as `result = await run(agent, result.state)` is accepted because the
  right-hand side reads the old result state before replacing the result binding.
- Evidence: Pinned OpenAI Agents JS HITL/MCP examples use this exact resume shape:
  `examples/mcp/hosted-mcp-on-approval.ts`, `examples/docs/mcp/hostedHITL.ts`, and
  `examples/mcp/hosted-mcp-human-in-the-loop.ts` resume with inline `result.state`, while
  `examples/agent-patterns/human-in-the-loop-stream.ts` assigns `const state = stream.state` and
  resumes with that binding. Local negatives pin loose state objects, unknown run functions, stale
  result bindings, and reassigned named state inputs.
- Alternative: Treat any object named `state` or any `.state` property as run-state continuity.
  Rejected because many libraries and applications use generic state objects unrelated to OpenAI
  Agents SDK run resumption.
- Revisit when: approval-quality analysis is added on top of this resume backbone, especially to
  distinguish manual human approval, automatic approval, rejected-state handling, and missing
  approval callbacks.

## OpenAI generic tool approval inventory is exact-import and policy-level

- Decision: Record OpenAI Agents JS `tool({ needsApproval })` approval metadata only when `tool` is
  an exact unshadowed value import from `@openai/agents`. Literal `needsApproval: true` remains the
  only generic-tool form that creates a `human-approval` control edge; callback-valued
  `needsApproval` is recorded as `approval_policy: callback-controlled` without claiming always-on
  approval coverage.
- Evidence: Pinned examples show both official forms: `examples/docs/human-in-the-loop/toolApprovalDefinition.ts`
  contains `sensitiveTool` with literal approval and `sendEmail` with a callback; `examples/nextjs/src/agents.ts`
  contains a literal-approved generic tool; `examples/agent-patterns/human-in-the-loop.ts` and
  `examples/agent-patterns/human-in-the-loop-stream.ts` contain conditional callbacks.
- Alternative: Treat callback-valued `needsApproval` as full `human-approval` coverage. Rejected
  because the callback can approve only some calls and AgentVerify has not proven the predicate
  covers every risky operation.
- Revisit when: predicate-aware tool-risk analysis can relate callback conditions to specific tool
  inputs, or when `agent.asTool({ needsApproval })` delegated-tool approval gets a distinct IR shape.

## OpenAI delegated-agent asTool approval inventory belongs on exact adapter edges

- Decision: Record OpenAI Agents JS `agent.asTool({ needsApproval })` approval metadata on the
  `agent delegates-to agent` adapter relationship, using the exact `asTool(...)` call line as
  evidence. Literal `needsApproval: true` records `approval_policy: enabled`,
  `approval_handler: none`, and `approval_decision: always`; callback-valued `needsApproval`
  records `approval_policy: callback-controlled`, `approval_handler: needsApproval-callback`, and
  `approval_decision: dynamic-callback`; omitted or explicit false approval stays unclaimed.
- Evidence: Local `cases/typescript_structured_tools` now has three `worker.asTool(...)` entries to
  the same target agent, proving that parent-constructor evidence would collapse distinct adapter
  policies. Pinned OpenAI Agents JS HITL examples use `weatherAgent.asTool({ toolName:
  "ask_weather_agent", needsApproval: async ... })` in both standard and streaming flows.
- Alternative: Create a synthetic tool component for each delegated agent adapter. Deferred because
  the current IR already has a source/target agent relationship, and adding delegated-tool
  components would be a larger schema/semantics choice. Edge attributes preserve identity now
  without overclaiming approval coverage.
- Revisit when: predicate-aware approval-quality analysis needs a first-class delegated-tool node,
  or reporting rules need to reason about delegated-agent tools independently of the source/target
  agent relationship.

## OpenAI run-state approval decisions require proven SDK state receivers

- Decision: Record OpenAI Agents JS manual approval/rejection handling as `approval-decision`
  controls only when `state.approve(...)`, `state.reject(...)`, `result.state.approve(...)`, or
  `result.state.reject(...)` can be tied to a proven exact OpenAI Agents `run(...)` or
  `Runner.run(...)` result state. Link the source agent to each decision control with
  `governed-by`, and keep approval decisions separate from conversation-continuity resume controls.
- Evidence: Local fixtures cover bound state, inline result state, loose approval-shaped objects,
  unknown run results, stale result bindings, and rebound state bindings. Pinned OpenAI Agents JS
  examples prove both bound-state decisions in
  `examples/agent-patterns/human-in-the-loop-stream.ts` and inline `result.state` decisions in
  `examples/mcp/hosted-mcp-human-in-the-loop.ts`.
- Alternative: Treat every `.approve(...)`/`.reject(...)` receiver or every variable named `state`
  as approval evidence. Rejected because ordinary application state and same-named helper objects
  can have unrelated methods.
- Revisit when: `RunState.fromString(agent, storedState)` can be linked back to serialized
  `result.state` without broad string/dataflow inference, or when approval predicate analysis can
  classify whether decisions cover specific risky tool calls.

## OpenAI RunState.fromString continuity requires a proven serialized SDK state chain

- Decision: Treat `RunState.fromString(agent, serializedState)` as OpenAI Agents JS run-state
  continuity only when `RunState` is an exact unshadowed import from `@openai/agents`, the first
  argument resolves to the same local agent used by the original exact SDK `run(...)`, and the
  serialized-state argument is sourced from a same-file `result.state.toString()` or literal
  `writeFile`/`readFile` chain around `JSON.stringify(result.state, ...)`.
- Evidence: The real OpenAI Agents JS `examples/agent-patterns/human-in-the-loop.ts` example writes
  `JSON.stringify(result.state, ...)` to `result.json`, reads it back into `storedState`, restores
  with `RunState.fromString(agent, storedState)`, then calls `state.approve/reject` before resuming
  `run(agent, state)`. Local negatives cover loose serialized strings, unknown run results, and
  stale result bindings before serialization.
- Alternative: Accept any string passed to `RunState.fromString`. Rejected because a string can be
  arbitrary application data and does not prove OpenAI SDK run-state continuity or approval
  handling.
- Revisit when: cross-function or nonliteral persistence flows can be modeled with source-proven
  dataflow without accepting unrelated file/string state.

## OpenAI builtin approval callbacks are callback-controlled policy evidence

- Decision: Treat callback-valued `needsApproval` on exact OpenAI Agents JS approval-capable
  builtin tool constructors, such as `computerTool({ needsApproval: async ... })`, as
  `approval_policy: callback-controlled` with `approval_handler: needsApproval-callback` and
  `approval_decision: dynamic-callback`. Keep separate `onApproval`/handler-like options as
  unresolved-handler evidence unless a `needsApproval` policy expression is present.
- Evidence: The pinned OpenAI Agents JS `examples/tools/computer-use-hitl.ts` example configures
  `computerTool` with callback-valued `needsApproval` in both singleton and per-request computer
  flows. Local `cases/typescript_structured_tools` now includes the same shape beside literal
  approval and delegated-agent approval cases, and the public IR truth set regenerates at 1,977/1,977
  passing labels.
- Alternative: Continue classifying builtin callback approval as `unresolved-handler`. Rejected
  because the callback is attached to the SDK-native `needsApproval` policy key and has the same
  meaning as generic `tool({ needsApproval: async ... })`: dynamic policy selection, not an
  unrelated handler.
- Revisit when: predicate-aware approval-quality analysis can inspect callback bodies and relate
  action/input predicates to risky builtin operations, especially automatic approvals or narrow
  action allowlists.

## OpenAI approval predicate inventory starts with shallow literal predicates

- Decision: Record only exact shallow literal `needsApproval` predicates in OpenAI Agents JS
  approval metadata: `field.startsWith("literal")`, `field.includes("literal")`, and
  `["literal", ...].includes(action.field)`. Apply the same vocabulary to generic `tool(...)`,
  delegated `agent.asTool(...)`, and approval-capable builtin constructors.
- Evidence: Pinned OpenAI Agents JS examples cover all three shapes: `command.startsWith(...)` in
  the local CLI fixture, `subject.includes("spam")` in the docs tool definition,
  `city.includes("Oakland")` and `input.includes("San Francisco")` in HITL examples, and
  `["click", "type", "keypress"].includes(action.type)` in the computer-use HITL examples.
  Focused approval-control labels passed 51/51 and the full public IR truth set regenerated at
  1,987/1,987 passing labels.
- Alternative: Interpret arbitrary callback bodies or helper calls as approval-quality evidence.
  Rejected because callback semantics can invert, combine, or delegate decisions in ways that need
  a real expression model; shallow literal predicates add useful review metadata without claiming
  complete risky-action coverage.
- Revisit when: compound boolean predicates, helper-return summaries, or action-specific risk
  mapping can be modeled and regression-labeled without accepting broad same-named fields.

## OpenAI Agents JS computer safety checks are separate from human approval

- Decision: Inventory exact `computerTool({ onSafetyCheck })` callbacks as safety-check metadata,
  not generic human-approval metadata. Report `AV-APPROVAL011` only when a reachable
  computer-control capability auto-acknowledges all pending safety checks by returning `true` or by
  returning the full `pendingSafetyChecks` list through the SDK-supported
  `acknowledgedSafetyChecks` or `acknowledged_safety_checks` result key, including ordinary
  block-body returns and parenthesized expression-bodied object returns.
- Evidence: The pinned OpenAI Agents JS `examples/tools/computer-use-hitl.ts` file contains a
  singleton computer tool with `needsApproval` but no `onSafetyCheck`, and a per-request computer
  tool whose `onSafetyCheck` callback returns the full pending safety-check list as acknowledged.
  Local focused rule and IR labels passed 14/14 before full benchmark regeneration, including the
  SDK-supported snake_case acknowledgement key and expression-bodied object return shape.
- Alternative: Treat any configured safety-check callback as safe or unsafe. Rejected because
  callback existence alone does not prove review quality, while exact pass-through and return-true
  callbacks prove auto-acknowledgement without modeling arbitrary helper logic.
- Revisit when: richer safety-check callback semantics, safety-check type matching, or explicit
  policy/user-review handoff patterns can be source-proven and labeled.

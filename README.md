# AgentVerify

AgentVerify is an evidence-driven static analyzer for AI agent applications. It makes agent
architectures, capabilities, trust boundaries, and risky execution paths visible before an agent is
deployed.

The initial research corpus contains 71 pinned repositories spanning frameworks, coding and browser
agents, MCP servers, workflow platforms, tool integrations, sandboxes, and observability systems.
The first engine supports Python AST analysis, structure-aware TypeScript/JavaScript discovery, MCP
configuration, framework/provider/tool inventory, deterministic JSON, and initial
agent-security review rules. Its curated cross-rule regression set contains 719 pinned positive and
negative labels, plus 1,781 separately scored Agent IR component and relationship labels.

## Install and scan

```console
pip install agentverify
agentverify scan ./project
agentverify scan ./project --format summary
agentverify scan ./project --format json
agentverify scan ./project --format bom
agentverify scan ./project --format sarif
agentverify scan ./project --format sarif --output agentverify.sarif
agentverify schema
agentverify schema benchmark-result --output agentverify-benchmark-result.schema.json
agentverify schema benchmark-verification --output agentverify-benchmark-verification.schema.json
agentverify schema editor-contract-manifest --output agentverify-editor-contract-manifest.schema.json
agentverify schema editor-contract-verification --output agentverify-editor-contract-verification.schema.json
agentverify schema holdout-manifest --output agentverify-holdout-manifest.schema.json
agentverify schema holdout-labels --output agentverify-holdout-labels.schema.json
agentverify schema report --output agentverify-report.schema.json
agentverify schema bom --output agentverify-ai-bom.schema.json
agentverify schema policy --output agentverify-policy.schema.json
agentverify schema policy-key-trust-root --output agentverify-policy-key-trust-root.schema.json
agentverify schema policy-signature --output agentverify-policy-signature.schema.json
agentverify schema policy-signing-payload --output agentverify-policy-signing-payload.schema.json
agentverify schema policy-summary --output agentverify-policy-summary.schema.json
agentverify schema policy-trust-root --output agentverify-policy-trust-root.schema.json
agentverify schema rules --output agentverify-rules.schema.json
agentverify scan ./project --policy agentverify-policy.json
agentverify scan ./project --policy repository-policy.json  # may extend local organization policy
agentverify policy repository-policy.json
agentverify policy repository-policy.json --format json
agentverify policy repository-policy.json --export-trust-root --output policy-trust-root.json
agentverify policy repository-policy.json --export-signing-payload --output policy-signing-payload.json
agentverify policy repository-policy.json --trust-root policy-trust-root.json --require-trusted
agentverify policy examples/repository-policy.json --trust-root examples/policy-trust-root.json --require-trusted
agentverify benchmark verify --require-evaluation-kind public-regression --require-all-passed
agentverify holdout validate --manifest benchmarks/holdout-manifest.template.json --labels benchmarks/holdout-labels.template.json
agentverify contracts --output-dir agentverify-editor-contracts --sample-root examples/safe_agent
agentverify contracts --verify-dir agentverify-editor-contracts
agentverify scan ./project --fail-on high
agentverify scan ./project --fail-on high --fail-on-kind any
agentverify scan ./project --include-tests
agentverify scan ./project --baseline previous-agentverify.json
agentverify scan ./project --paths-from changed-files.txt
agentverify scan ./project --require-suppression-expiry --fail-on high
agentverify rules
agentverify rules AV-EXEC001
agentverify rules --format json
```

Reviewed exceptions can be suppressed only for the immediately following line, with a rule ID and
required reason:

```python
# agentverify: ignore AV-EXEC001 until 2026-12-31 -- command is selected from the fixed deployment allowlist
subprocess.run(command, shell=True)
```

JSON and text reports retain the suppression's rule, reason, directive location, and finding location.
They also retain expiry and status. JSON reports self-identify as `AgentVerify JSON Report` schema
version 1 and include a deterministic `risk_summary` by rule, severity, and result kind after inline
suppression and baseline filtering. Expired or malformed dates never suppress a finding;
`--require-suppression-expiry` also restores reason-only exceptions. Broad file-level or reason-free
inline ignores are intentionally unsupported. Expiry dates are evaluated in UTC and remain active
through the stated date.
When `--baseline` is used, reports separate new and unchanged fingerprints and count fingerprints no
longer reported by a full scan. Partial selected-path scans leave that last count unavailable.
Baselines must be a fingerprint list, an AgentVerify JSON report, a native AI BOM, or a SARIF report;
unknown JSON objects and malformed entries without AgentVerify fingerprints are rejected instead of
treated as an empty baseline.
Reports and schemas are written to standard output by default. Use `--output PATH` (or `-o PATH`)
to write them directly to a file. Output write failures return exit code 2; successful scan writes
still preserve policy and `--fail-on` exit decisions.
`agentverify schema` lists every bundled machine-readable schema.
`agentverify schema benchmark-result` prints the bundled schema for benchmark result files.
`agentverify schema benchmark-verification` validates the JSON emitted by
`agentverify benchmark verify`.
`agentverify schema editor-contract-manifest` validates the manifest emitted by
`agentverify contracts`; `agentverify schema editor-contract-verification` validates the JSON emitted
by `agentverify contracts --verify-dir`.
`agentverify schema holdout-manifest` and `agentverify schema holdout-labels` validate the public
sealed-holdout sampling and adjudicated-label templates.
`agentverify holdout validate --manifest PATH --labels PATH` validates those setup files directly
with the bundled schemas, returning exit code 2 when a template or private setup file is malformed.
`agentverify schema report` prints the bundled schema for validating normal `--format json` reports;
`agentverify schema policy-summary` validates `agentverify policy --format json`,
`agentverify schema policy-signing-payload` validates deterministic source-digest manifests for
external policy signing, `agentverify schema policy-signature` and
`agentverify schema policy-key-trust-root` validate detached signature bundles and local public-key
trust roots, and `agentverify schema policy-trust-root` validates local digest allowlists for policy
summaries.
`agentverify schema rules` validates the machine-readable rule catalog.
`agentverify benchmark verify` validates benchmark result JSON against the bundled schema, recomputes
label and manifest digests, binds outcomes back to exact label ids/rules/expectations, recomputes
outcome-derived passed/failed/metrics totals, and reports failure classes separately for observation,
anchor, and source-snippet mismatches. It can fail closed on release-claim requirements such as
`--require-evaluation-kind sealed-holdout`, `--require-sealed`, `--require-manifest`, and
`--require-all-passed`.
Use `--format summary` for compact CI logs: it reports scan totals, baseline/policy status, counts by
severity/result kind/rule, and the top evidence locations without printing the full component graph.
`agentverify rules` lists every enabled reporting rule with its result kind, default severity,
confidence, summary, and baseline remediation. Pass a rule ID for a focused explanation or
`--format json` for policy tooling and editor integrations; the bundled rules schema preserves this
contract for generated configuration and editor metadata. Policy rule filters reject unknown or
inventory-only IDs before scanning. They also reject selected rules excluded by the gate's result
kind or severity threshold, so a typo or dead filter cannot silently turn a gate into an empty match.
`agentverify policy PATH` validates a policy without scanning a repository and explains composed
gate sources and SHA-256 content digests. These digests make local inputs auditable; they are not
author signatures. A policy trust root can require every composed policy source to match an approved
local SHA-256 digest allowlist while keeping `signature_verified: false`. For author authenticity,
`agentverify policy PATH --signature policy-signature.json --trust-root policy-key-trust-root.json`
verifies a detached Ed25519 signature over the composed source-digest manifest and can be combined
with `--require-trusted` as a fail-closed CI gate. Use
`agentverify policy PATH --export-trust-root --output policy-trust-root.json` to generate a local
digest allowlist from the exact composed policy inputs, or
`agentverify policy PATH --export-signing-payload --output policy-signing-payload.json` to emit the
deterministic source-digest manifest that external signing tools should sign.
See [`docs/policy-signatures.md`](docs/policy-signatures.md) for a local ephemeral-key dry run and
production trust-root guidance.

Example finding:

```text
HIGH AV-EXEC001 [high; finding]
  A dynamic command is executed through a system shell
  agent.py:13
  Path: agent:operator -> tool:run_task -> capability:shell-execution
  Approval coverage: unresolved
  Audit coverage: unresolved
  Remediation: Pass a fixed argv list with shell=False, or strictly validate and allowlist the command.
```

## Evidence first

- [`research/repositories.md`](research/repositories.md) — 71-repository pinned corpus and signals
- [`research/findings.md`](research/findings.md) — quantified findings and limitations
- [`research/patterns.md`](research/patterns.md) — recurring architecture and control patterns
- [`docs/roadmap.md`](docs/roadmap.md) — impact × frequency × feasibility priorities
- [`docs/detection-rules.md`](docs/detection-rules.md) — rule contracts and validation gates
- [`docs/architecture.md`](docs/architecture.md) — Agent IR, graph analysis, and uncertainty model
- [`docs/frontend-coverage.md`](docs/frontend-coverage.md) — supported syntax and empirical gaps
- [`docs/ai-bom.md`](docs/ai-bom.md) — native machine-readable asset and governance inventory
- [`docs/policy.md`](docs/policy.md) — schema-backed, non-hiding CI gate policies
- [`docs/code-scanning.md`](docs/code-scanning.md) — copy-ready GitHub SARIF integration
- [`examples/github-code-scanning.yml`](examples/github-code-scanning.yml) — copyable SARIF upload workflow
- [`examples/github-code-scanning.sarif`](examples/github-code-scanning.sarif) — checked SARIF upload payload example
- [`docs/editor-integration.md`](docs/editor-integration.md) — exportable schemas and rule catalog for editor/CI tooling
- [`docs/pre-commit.md`](docs/pre-commit.md) — local and tagged-release hook setup
- [`docs/backlog.md`](docs/backlog.md) — prioritized issue-ready future work
- [`benchmarks/engine-results.json`](benchmarks/engine-results.json) — full-corpus engine metrics
- [`benchmarks/truthset.json`](benchmarks/truthset.json) — exact hand-labeled positives and negatives
- [`benchmarks/truthset-results.json`](benchmarks/truthset-results.json) — per-rule seed precision/recall and label-failure summary
- [`benchmarks/ir-truthset.json`](benchmarks/ir-truthset.json) — 1,781 separately scored component and relationship labels
- [`benchmarks/holdout-design.md`](benchmarks/holdout-design.md) — sealed benchmark plan for unbiased evaluation
- [`benchmarks/release-checklist.md`](benchmarks/release-checklist.md) — claim boundaries and verifier gates for benchmark releases
- [`examples/github-benchmark-verify.yml`](examples/github-benchmark-verify.yml) — copyable benchmark verifier workflow
- [`examples/benchmark-verification.json`](examples/benchmark-verification.json) — checked verifier-output example for public-regression release gates
- [`benchmarks/holdout-manifest.template.json`](benchmarks/holdout-manifest.template.json) — public sample manifest shape
- [`benchmarks/holdout-labels.template.json`](benchmarks/holdout-labels.template.json) — public sealed-label template shape
- `agentverify schema holdout-manifest` and `agentverify schema holdout-labels` — installed
  contracts for sealed-holdout setup templates
- [`benchmarks/benchmark-results-v1.schema.json`](benchmarks/benchmark-results-v1.schema.json) — benchmark result contract
  (also available from an installed CLI with `agentverify schema benchmark-result`)
- `agentverify schema benchmark-verification` — installed verifier-output contract for
  `agentverify benchmark verify` JSON artifacts

SARIF output includes stable fingerprints, source locations, severity, remediation, Agent IR paths,
and resolved/unresolved control context for code-scanning integrations.

The copyable [GitHub code-scanning workflow](examples/github-code-scanning.yml) uploads results on
pushes, pull requests, and a weekly schedule. It uses a job-scoped token and a stable SARIF category;
see the integration guide before adding an enforcement threshold. This repository also keeps a
project-specific [self-scan workflow](.github/workflows/code-scanning.yml) that scans only `src/`.
For policy-only GitHub Actions gates, start from the checked
[`examples/github-policy-gate.yml`](examples/github-policy-gate.yml) workflow.

The bundled [pre-commit hook manifest](.pre-commit-hooks.yaml) supports repository-wide local scans;
the setup guide and [copyable local config](examples/pre-commit-config.yaml) avoid assuming a public
URL or release tag that does not yet exist.

Reproduce the corpus analysis:

```console
python3 scripts/collect_repositories.py
python3 scripts/render_repositories.py
PYTHONPATH=src python3 scripts/benchmark_engine.py
PYTHONPATH=src python3 scripts/evaluate_truthset.py
PYTHONPATH=src python3 scripts/evaluate_truthset.py --labels benchmarks/ir-truthset.json \
  --output benchmarks/ir-truthset-results.json
PYTHONPATH=src python3 scripts/evaluate_truthset.py --evaluation-kind sealed-holdout \
  --manifest path/to/holdout-manifest.json --labels path/to/sealed-labels.json \
  --output path/to/holdout-results.json
uv run python scripts/verify_benchmark_results.py --require-evaluation-kind public-regression --require-all-passed
agentverify benchmark verify --require-evaluation-kind public-regression --require-all-passed
agentverify holdout validate --manifest benchmarks/holdout-manifest.template.json --labels benchmarks/holdout-labels.template.json
agentverify schema benchmark-result --output agentverify-benchmark-result.schema.json
agentverify schema benchmark-verification --output agentverify-benchmark-verification.schema.json
agentverify schema holdout-manifest --output agentverify-holdout-manifest.schema.json
agentverify schema holdout-labels --output agentverify-holdout-labels.schema.json
```

The default CI workflow runs the installed CLI benchmark gate against the checked-in public
regression results and validates the verifier JSON against the bundled benchmark-verification schema,
so benchmark-result drift fails during pull requests before release packaging. The verifier artifact
also carries per-result `failed` counts and mismatch summaries so release tooling can distinguish
scanner false positives/negatives from stale source anchors or expected snippets. Source-distribution
verification keeps the copyable GitHub workflow examples tied to their contracts: benchmark
verification emits, validates, and uploads `agentverify-benchmark-verification.json`; policy-gate
and code-scanning examples keep their expected permissions and gate/upload commands.
For editor or custom CI integrations, `agentverify contracts --sample-root examples/safe_agent`
exports the report schema, rules schema, current rules catalog, and optional sample report into a
local artifact directory with a schema-backed digest manifest. `agentverify contracts --verify-dir`
rechecks copied bundles before consumers load them, and its JSON result validates against
`agentverify schema editor-contract-verification`. The editor guide also includes a checked
[`examples/editor-diagnostics.json`](examples/editor-diagnostics.json) mapping from AgentVerify
findings to Language Server Protocol-style diagnostics.

The collector reuses commits from `research/repository-data.json` by default and samples up to 220
source/manifest roots plus at most 20 bounded local source dependencies reached from MCP
forwarding/URL-security roots or listed as audited evidence hints per repository. Use `--refresh` only
when intentionally creating a new upstream snapshot; the refreshed output becomes the next lock.

## Development

```console
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/ruff check src tests scripts
uv build --wheel --sdist
python3 scripts/verify_distribution.py --require-sdist
python3 scripts/verify_distribution.py --require-sdist --smoke-install
uv run python scripts/verify_benchmark_results.py --require-evaluation-kind public-regression --require-all-passed
```

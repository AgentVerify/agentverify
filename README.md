# AgentVerify

AgentVerify is an evidence-driven static analyzer for AI agent applications. It makes agent
architectures, capabilities, trust boundaries, and risky execution paths visible before an agent is
deployed.

The initial research corpus contains 71 pinned repositories spanning frameworks, coding and browser
agents, MCP servers, workflow platforms, tool integrations, sandboxes, and observability systems.
The first engine supports Python AST analysis, structure-aware TypeScript/JavaScript discovery, MCP
configuration, framework/provider/tool inventory, deterministic JSON, and initial
agent-security review rules. Its curated cross-rule regression set contains 342 pinned positive and
negative labels.

## Install and scan

```console
pip install agentverify
agentverify scan ./project
agentverify scan ./project --format json
agentverify scan ./project --format bom
agentverify scan ./project --format sarif
agentverify schema bom > agentverify-ai-bom.schema.json
agentverify schema policy > agentverify-policy.schema.json
agentverify scan ./project --policy agentverify-policy.json
agentverify scan ./project --policy repository-policy.json  # may extend local organization policy
agentverify scan ./project --fail-on high
agentverify scan ./project --fail-on high --fail-on-kind any
agentverify scan ./project --include-tests
agentverify scan ./project --baseline previous-agentverify.json
agentverify scan ./project --paths-from changed-files.txt
agentverify scan ./project --require-suppression-expiry --fail-on high
```

Reviewed exceptions can be suppressed only for the immediately following line, with a rule ID and
required reason:

```python
# agentverify: ignore AV-EXEC001 until 2026-12-31 -- command is selected from the fixed deployment allowlist
subprocess.run(command, shell=True)
```

JSON and text reports retain the suppression's rule, reason, directive location, and finding location.
They also retain expiry and status. Expired or malformed dates never suppress a finding;
`--require-suppression-expiry` also restores reason-only exceptions. Broad file-level or reason-free
inline ignores are intentionally unsupported. Expiry dates are evaluated in UTC and remain active
through the stated date.
When `--baseline` is used, reports separate new and unchanged fingerprints and count fingerprints no
longer reported by a full scan. Partial selected-path scans leave that last count unavailable.

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
- [`docs/pre-commit.md`](docs/pre-commit.md) — local and tagged-release hook setup
- [`docs/backlog.md`](docs/backlog.md) — prioritized issue-ready future work
- [`benchmarks/engine-results.json`](benchmarks/engine-results.json) — full-corpus engine metrics
- [`benchmarks/truthset.json`](benchmarks/truthset.json) — exact hand-labeled positives and negatives
- [`benchmarks/truthset-results.json`](benchmarks/truthset-results.json) — per-rule seed precision and recall
- [`benchmarks/ir-truthset.json`](benchmarks/ir-truthset.json) — 322 separately scored relationship labels

SARIF output includes stable fingerprints, source locations, severity, remediation, Agent IR paths,
and resolved/unresolved control context for code-scanning integrations.

The included [GitHub code-scanning workflow](.github/workflows/code-scanning.yml) uploads results on
pushes, pull requests, and a weekly schedule. It uses a job-scoped token and a stable SARIF category;
see the integration guide before adding an enforcement threshold.

The bundled [pre-commit hook manifest](.pre-commit-hooks.yaml) supports repository-wide local scans;
the setup guide avoids assuming a public URL or release tag that does not yet exist.

Reproduce the corpus analysis:

```console
python3 scripts/collect_repositories.py
python3 scripts/render_repositories.py
PYTHONPATH=src python3 scripts/benchmark_engine.py
PYTHONPATH=src python3 scripts/evaluate_truthset.py
PYTHONPATH=src python3 scripts/evaluate_truthset.py --labels benchmarks/ir-truthset.json \
  --output benchmarks/ir-truthset-results.json
```

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
```

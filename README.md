# AgentVerify

AgentVerify is an evidence-driven static analyzer for AI agent applications. It makes agent
architectures, capabilities, trust boundaries, and risky execution paths visible before an agent is
deployed.

The initial research corpus contains 71 pinned repositories spanning frameworks, coding and browser
agents, MCP servers, workflow platforms, tool integrations, sandboxes, and observability systems.
The first engine supports Python AST analysis, TypeScript/JavaScript discovery, MCP configuration,
framework/provider/tool inventory, deterministic JSON, and initial dangerous-execution rules. Its
curated cross-rule regression set contains 100 pinned positive and negative labels.

## Install and scan

```console
pip install agentverify
agentverify scan ./project
agentverify scan ./project --format json
agentverify scan ./project --format sarif
agentverify scan ./project --fail-on high
agentverify scan ./project --fail-on high --fail-on-kind any
agentverify scan ./project --include-tests
agentverify scan ./project --baseline previous-agentverify.json
```

Example finding:

```text
HIGH AV-EXEC001 [high; finding]
  A dynamic command is executed through a system shell
  agent.py:13
  Path: agent:operator -> tool:run_task -> capability:shell-execution
  Approval coverage: unresolved
  Remediation: Pass a fixed argv list with shell=False, or strictly validate and allowlist the command.
```

## Evidence first

- [`research/repositories.md`](research/repositories.md) — 71-repository pinned corpus and signals
- [`research/findings.md`](research/findings.md) — quantified findings and limitations
- [`research/patterns.md`](research/patterns.md) — recurring architecture and control patterns
- [`docs/roadmap.md`](docs/roadmap.md) — impact × frequency × feasibility priorities
- [`docs/detection-rules.md`](docs/detection-rules.md) — rule contracts and validation gates
- [`docs/architecture.md`](docs/architecture.md) — Agent IR, graph analysis, and uncertainty model
- [`docs/backlog.md`](docs/backlog.md) — prioritized issue-ready future work
- [`benchmarks/engine-results.json`](benchmarks/engine-results.json) — full-corpus engine metrics
- [`benchmarks/truthset.json`](benchmarks/truthset.json) — exact hand-labeled positives and negatives
- [`benchmarks/truthset-results.json`](benchmarks/truthset-results.json) — per-rule seed precision and recall

SARIF output includes stable fingerprints, source locations, severity, remediation, Agent IR paths,
and resolved/unresolved control context for code-scanning integrations.

Reproduce the corpus analysis:

```console
python3 scripts/collect_repositories.py
python3 scripts/render_repositories.py
PYTHONPATH=src python3 scripts/benchmark_engine.py
PYTHONPATH=src python3 scripts/evaluate_truthset.py
```

## Development

```console
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/ruff check src tests scripts
```

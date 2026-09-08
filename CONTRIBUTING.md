# Contributing to AgentVerify

AgentVerify favors explainable, validated detections over large rule counts.

## Maintainer

AgentVerify is maintained by **Steven Rosa** ([GitHub: @gangfan](https://github.com/gangfan)).
The GitHub noreply address in commits is for attribution only and cannot receive contact emails.
For private questions or collaboration, contact
[stevenrosafan@icloud.com](mailto:stevenrosafan@icloud.com). Public bug reports and rule proposals
can use the issue forms. For security issues in AgentVerify itself, use that email or
[private vulnerability reporting](https://github.com/AgentVerify/agentverify/security/advisories/new).

## Start small

You do not need to write a new rule to contribute. Try the [demo](docs/getting-started.md), scan a
repository you know, improve a confusing setup step, or minimize a false-positive example.
Use the [issue chooser](https://github.com/AgentVerify/agentverify/issues/new/choose) to share scan
feedback, report a bug, or propose a rule. Remove private code and credentials before posting.

## How feedback becomes a fix

Maintainers triage reports by impact, reproducibility, and frequency. A detection report should
become a minimal positive or negative regression case before the behavior changes. Pull requests
link back to the report, explain the evidence and limitations, and record user-visible changes in
the changelog. Reports without a reproducer may need more evidence before implementation.

The [roadmap](docs/roadmap.md) records priorities; open issues record concrete work. Before a large
feature, describe the user problem and a real example in an issue so contributors can coordinate.

## Development setup

```console
git clone https://github.com/AgentVerify/agentverify.git
cd agentverify
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python scripts/demo.py
.venv/bin/pytest
.venv/bin/ruff check src tests scripts
```

On Windows use the corresponding `.venv\Scripts` executables. The normal test suite uses local
fixtures; you do not need provider keys or a fresh corpus download. Benchmark artifact verification
is separate from the longer network-backed corpus collection described in [the guide](docs/benchmarks.md).

## Adding a rule

Before enabling a rule by default, include:

1. A pinned real-repository case and explanation of impact.
2. A minimal positive regression fixture.
3. A negative or near-miss fixture.
4. Source evidence, confidence, limitations, and remediation.
5. A stable rule ID documented in `docs/detection-rules.md`.

Rules must distinguish a confirmed flow from an unresolved review candidate. Do not infer that a
control is absent merely because a lexical scan did not find it.

## Research updates

Add upstream repositories to `research/corpus.csv`, rerun the collector, review changed evidence, and
regenerate `research/repositories.md`. Never silently replace a pinned case used by a regression rule.

# Contributing to AgentVerify

AgentVerify favors explainable, validated detections over large rule counts.

## Development setup

```console
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/ruff check src tests scripts
```

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


# Getting started

[Documentation index](README.md)

AgentVerify reads a local repository and reports agent capabilities and risky paths. Scanning does
not import the target application, start its agents, install its dependencies, or call an LLM.
You do not need provider credentials or Node.js to scan TypeScript source.

## Install

Use Python 3.11 or newer and Git:

```console
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "agentverify @ git+https://github.com/AgentVerify/agentverify.git@v0.1.0"
agentverify --version
```

On Windows use `py -3 -m venv .venv` and `.venv\Scripts\Activate.ps1` in PowerShell.
If `agentverify` is not on PATH, activate the environment or use `python -m agentverify`.

Without Git, download `agentverify-0.1.0-py3-none-any.whl` from the
[v0.1.0 release](https://github.com/AgentVerify/agentverify/releases/tag/v0.1.0), then run:

```console
python -m pip install ./agentverify-0.1.0-py3-none-any.whl
```

Installation downloads AgentVerify and its dependencies. Scans run locally after installation.
The official package is distributed through GitHub for this release; do not assume a similarly
named PyPI package is this project.

## Try the demonstration

```console
git clone --branch v0.1.0 --depth 1 https://github.com/AgentVerify/agentverify.git
cd agentverify
python scripts/demo.py
```

The demo scans two checked-in fixtures and validates their reports and gate exit codes. The first
has one high-severity `AV-EXEC001` finding: a tool passes a dynamic command to a shell. The second
uses a fixed argv list and has no findings. Neither fixture is executed.

## Scan your repository

```console
agentverify scan /path/to/project --format summary
agentverify scan /path/to/project --format json --output agentverify.json
agentverify scan /path/to/project --format bom --output agentverify-bom.json
```

Start with the summary. Run the default text format for fuller evidence, or open the JSON for
components, relationships, source locations, confidence, and control context. Run
`agentverify rules RULE_ID` to explain a rule. An AI BOM is an inventory rather than a safety verdict.

## Interpret results

`finding` denotes evidence meeting a reporting rule's finding criteria. `review` is a candidate
requiring human judgment. Severity describes impact; confidence describes evidence strength.
Control coverage may be `unresolved`: this means the scanner cannot establish the control, not that
your application lacks one. Inspect the source before changing an approval or security boundary.

A scan with no findings may still contain unsupported syntax or unmodeled runtime behavior. Check
file counts, parse warnings, and [frontend coverage](frontend-coverage.md) if results look incomplete.
Tests and fixtures are normally excluded from findings; use `--include-tests` to include them.

## Add a CI gate after reviewing the first scan

```console
agentverify scan . --fail-on high
```

This fails only on high-severity `finding` results by default. Add `--fail-on-kind any` to include
reviews, or use a [policy](policy.md) for finer control. Exit codes are 0 for success, 1 for a failed
gate, and 2 for invalid input or an operational error. A normal ungated scan returns 0 even when
it reports findings.

To focus on new findings, save a JSON report and use it as a reviewed baseline:

```console
agentverify scan . --format json --output agentverify-baseline.json
agentverify scan . --baseline agentverify-baseline.json --fail-on high
```

Baselines hide matching fingerprints; review them as carefully as exceptions. See the
[CLI reference](cli-reference.md) for expiring inline suppressions and changed-file scan limits.

## Send feedback

[Share your scan experience](https://github.com/AgentVerify/agentverify/issues/new?template=scan-feedback.yml)
or [report a detection mistake](https://github.com/AgentVerify/agentverify/issues/new?template=bug-report.yml).
Include the version, command, language/framework, and a small reproducer. Reports can contain code
snippets, URLs, and local paths: remove sensitive information before posting. Share vulnerabilities
in AgentVerify through [private security reporting](../SECURITY.md).

# AgentVerify

### See what your AI agents can do before you deploy them.

[![CI](https://github.com/AgentVerify/agentverify/actions/workflows/ci.yml/badge.svg)](https://github.com/AgentVerify/agentverify/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/AgentVerify/agentverify)](https://github.com/AgentVerify/agentverify/releases)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

[Quickstart](#try-it) · [Documentation](docs/README.md) · [Detection rules](docs/detection-rules.md) · [Results](#initial-results) · [Report feedback](https://github.com/AgentVerify/agentverify/issues/new/choose)

AgentVerify scans Python and TypeScript/JavaScript source code to show which tools an agent can
reach, what those tools can do, and what approval or sandbox controls are visible. It flags risky
execution paths with source locations, evidence, and remediation.

Runs locally. No model API key, LLM calls, or application execution required.

## Why use it?

- **Review agent permissions:** discover tools, MCP servers, providers, filesystem access, and shell execution.
- **Find risky paths:** detect dynamic shell commands, automatic approval, weak filesystem boundaries,
  unpinned MCP launchers, and other patterns across 25 reporting rules.
- **Bring evidence into pull requests:** export SARIF for GitHub code scanning, JSON for automation,
  or an AI bill of materials for an architecture inventory.

AgentVerify complements general code scanners by connecting agents, tools, capabilities, and controls.
It is an early static analyzer: a clean scan is not proof of safety, and an unresolved control is not
proof that the control is absent. See [coverage and limitations](docs/frontend-coverage.md).

## Try it

Requires Python 3.11+ and Git. Install the GitHub release in a virtual environment:

```console
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "agentverify @ git+https://github.com/AgentVerify/agentverify.git@v0.1.0"
agentverify scan /path/to/your/project --format summary
```

On Windows, activate with `.venv\Scripts\Activate.ps1` in PowerShell.
You can also install the wheel from [Releases](https://github.com/AgentVerify/agentverify/releases).
The official v0.1.0 distribution is on GitHub; these instructions do not depend on a PyPI package.

### Run the included demo

```console
git clone --branch v0.1.0 --depth 1 https://github.com/AgentVerify/agentverify.git
cd agentverify
python scripts/demo.py
```

The demo scans an intentionally unsafe tool and a fixed-command comparison. It checks that the
unsafe case triggers `AV-EXEC001`, the comparison has no findings, and the CI gate returns the
expected exit codes. It only reads the fixtures; it never runs their code.

The unsafe case passes a tool argument to a system shell:

```python
@function_tool
def run_task(command: str) -> str:
    return subprocess.run(command, shell=True, capture_output=True, text=True).stdout
```

Selected output from the real scan:

```text
Findings: 1
Finding counts:
  severity high: 1
  kind finding: 1
  AV-EXEC001: 1 [finding; high; confidence high]

Top findings:
  AV-EXEC001 high/finding at agent.py:13
```

Use `agentverify scan cases/python_dangerous` for the full evidence and remediation.
The [safe comparison](examples/safe_agent/agent.py) uses a fixed argument list without a shell.
[Getting started](docs/getting-started.md) explains how to interpret your own results.

## Use it in your workflow

```console
# Review findings without failing the command.
agentverify scan . --format summary

# Fail CI on high-severity findings.
agentverify scan . --fail-on high

# Export reports for code scanning or tooling.
agentverify scan . --format sarif --output agentverify.sarif
agentverify scan . --format json --output agentverify.json
agentverify scan . --format bom --output agentverify-bom.json

# Explain an enabled rule.
agentverify rules AV-EXEC001
```

Exit codes: `0` = scan completed and gates passed; `1` = a configured gate failed;
`2` = invalid input or an operational error. Without a gate, findings do not change the exit code.

| I want to… | Start here |
| --- | --- |
| Add GitHub alerts | [GitHub code-scanning workflow](examples/github-code-scanning.yml) and [setup guide](docs/code-scanning.md) |
| Set team-specific CI gates | [Policy guide](docs/policy.md) and [`examples/github-policy-gate.yml`](examples/github-policy-gate.yml) |
| Scan before committing | [Pre-commit setup](docs/pre-commit.md) |
| Review architecture and permissions | [AI bill of materials](docs/ai-bom.md) |
| Handle existing findings and exceptions | [CLI reference](docs/cli-reference.md) |
| Build an editor integration | [Editor guide](docs/editor-integration.md), [`examples/github-editor-contracts.yml`](examples/github-editor-contracts.yml), and [`examples/editor-policy-diagnostics.json`](examples/editor-policy-diagnostics.json) |

## Initial results

The v0.1.0 evidence comes from a pinned corpus of **71 repositories** covering agent frameworks,
coding agents, MCP servers, workflow platforms, sandboxes, and observability tools.

| Checked evidence | Result |
| --- | ---: |
| Reporting-rule regression labels | 733 / 733 pass |
| Agent architecture / IR regression labels | 2,621 / 2,621 pass |
| Combined public regression labels | 3,354 / 3,354 pass |
| Repositories in the engine snapshot | 71 / 71 scanned successfully |

These are curated regression results, including positive and negative cases. They measure known-case
coverage, not unbiased ecosystem-wide precision or recall. Verifying the checked artifacts does not
rerun the scanner against upstream projects.

Explore the [corpus](research/repositories.md), [findings and limitations](research/findings.md),
[minimal cases](cases/README.md), and [reproduction guide](docs/benchmarks.md).
Machine-readable evidence is available in
[`examples/benchmark-verification.json`](examples/benchmark-verification.json) and
[`examples/engine-results-verification.json`](examples/engine-results-verification.json).
Use [`examples/github-benchmark-verify.yml`](examples/github-benchmark-verify.yml) to verify it in CI.

## Help shape the next release

For private questions or collaboration, email **Steven Rosa** at
[stevenrosafan@icloud.com](mailto:stevenrosafan@icloud.com).

The most useful contribution is a real scan: tell us what helped, what was noisy, and what we missed.

- [Share scan feedback](https://github.com/AgentVerify/agentverify/issues/new?template=scan-feedback.yml):
  language/framework, command, runtime, and which results were useful.
- [Report a false positive, missed detection, or crash](https://github.com/AgentVerify/agentverify/issues/new?template=bug-report.yml)
  with a minimal example and expected result.
- [Propose a detection rule](https://github.com/AgentVerify/agentverify/issues/new?template=rule-proposal.yml)
  backed by a concrete case.

Reports may include source snippets and local paths; remove private code and credentials before sharing.
For vulnerabilities in AgentVerify itself, use [private security reporting](SECURITY.md).

We turn reproducible feedback into a regression case, a fix, and a changelog entry.
See [Contributing](CONTRIBUTING.md) for small first contributions and the [roadmap](docs/roadmap.md)
for current priorities. If AgentVerify is useful to you, a star helps others discover it.

## Development

```console
git clone https://github.com/AgentVerify/agentverify.git
cd agentverify
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/demo.py
pytest -q
ruff check src tests scripts
```

Release packaging and verification are documented in the
[release checklist](benchmarks/release-checklist.md). Licensed under [Apache 2.0](LICENSE).

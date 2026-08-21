# Pre-commit integration

AgentVerify ships a hook manifest for [pre-commit](https://pre-commit.com/). The default hook scans
the repository and fails only on high-severity `finding` results; review candidates do not block the
commit and remain available in a direct AgentVerify report.

## Use this checkout locally

Until AgentVerify has an approved public remote and release tag, install it as a local hook in the
repository being scanned:

```yaml
repos:
  - repo: local
    hooks:
      - id: agentverify
        name: AgentVerify agent security scan
        entry: agentverify scan . --fail-on high --fail-on-kind finding
        language: system
        pass_filenames: false
        always_run: true
```

Install AgentVerify in the active environment, then run:

```console
pre-commit install
pre-commit run agentverify --all-files
```

`language: system` deliberately uses the reviewed version already installed in that environment.
Pin that package version in the project's development dependencies.

## Use a future tagged release

After an official repository URL and tag exist, consumers can use the bundled
`.pre-commit-hooks.yaml` manifest:

```yaml
repos:
  - repo: <official-agentverify-repository-url>
    rev: <reviewed-release-tag>
    hooks:
      - id: agentverify
```

The distributed hook uses `language: python`, so pre-commit builds an isolated environment from the
selected revision. It intentionally uses `pass_filenames: false`: AgentVerify needs repository
context for imports, reachability, and controls. For fast changed-file CI feedback use
`--paths-from`; retain a full pre-commit or scheduled scan as the authoritative result.

To require expiring exceptions, override the hook arguments:

```yaml
      - id: agentverify
        args: [--require-suppression-expiry]
```

Arguments are appended after the manifest entry, so this preserves the default high-severity
finding threshold.

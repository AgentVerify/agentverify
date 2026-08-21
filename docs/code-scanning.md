# GitHub code scanning

AgentVerify emits SARIF 2.1.0 that GitHub can display as code-scanning alerts. The repository's
[`code-scanning.yml`](../.github/workflows/code-scanning.yml) is a working reference: it scans every
push to `main`, every pull request, and once a week, then uploads `agentverify.sarif` under the stable
`agentverify` category. AgentVerify itself scans `src/` so its intentionally vulnerable regression
fixtures do not become repository alerts; application repositories should normally scan `.`.

## Add it to a repository

Copy the workflow into `.github/workflows/agentverify.yml`. If AgentVerify is not already packaged
inside the repository, replace the install step with a released, organization-approved version such
as `python -m pip install agentverify==<version>`.

The upload job needs these GitHub token permissions:

```yaml
permissions:
  contents: read
  security-events: write
```

Use `github/codeql-action/upload-sarif@v4` with a stable category:

```yaml
- name: Scan repository
  run: agentverify scan . --format sarif > agentverify.sarif
- name: Upload SARIF to GitHub code scanning
  uses: github/codeql-action/upload-sarif@v4
  with:
    sarif_file: agentverify.sarif
    category: agentverify
```

[GitHub code scanning accepts third-party SARIF](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/integrate-with-existing-tools/upload-sarif-file)
for public repositories. Private and internal repositories need GitHub Code Security enabled. The
default AgentVerify exit status does not fail a build merely because review findings exist, so the
SARIF upload still runs. To enforce a policy in a separate step, add a second scan such as:

```yaml
- name: Enforce high-confidence high-severity findings
  run: agentverify scan . --fail-on high --fail-on-kind finding
```

Keep policy enforcement separate from SARIF generation: a failing scan step otherwise prevents the
upload step unless it uses `if: always()`. For an existing repository, `--baseline` can hide known
fingerprints while new results remain visible; commit and review that baseline as policy data.

The workflow deliberately grants `security-events: write` only to the scanning job. Do not pass a
personal token to the upload action; its default is the job-scoped GitHub token.

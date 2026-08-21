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
fingerprints while new results remain visible; commit and review that baseline as policy data. JSON,
text, and SARIF include counts for new, unchanged, and no-longer-reported fingerprints. The last count
is deliberately unavailable for selected-path scans because unscanned findings are not proven fixed.

The workflow deliberately grants `security-events: write` only to the scanning job. Do not pass a
personal token to the upload action; its default is the job-scoped GitHub token.

## Changed-file scans

For a fast pull-request signal, write repository-relative changed paths one per line and pass the
file to AgentVerify:

```console
git diff --name-only --diff-filter=ACMR "$BASE_SHA"...HEAD > changed-files.txt
agentverify scan . --paths-from changed-files.txt --format sarif > agentverify.sarif
```

Absolute paths and paths containing `..` are rejected. Directory entries select their descendants;
deleted or missing files produce no observations, and an empty list intentionally scans zero files.
JSON, text, and SARIF reports identify `selected-paths` scope and retain the normalized filters.

The repository-wide module index is still available for resolving selected files' imports, but
unselected source files are not parsed. A changed-file result therefore cannot prove repository-wide
control coverage or absence. Keep the scheduled full scan as the authoritative audit and use partial
scans only for rapid feedback.

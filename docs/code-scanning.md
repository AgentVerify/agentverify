# GitHub code scanning

AgentVerify emits SARIF 2.1.0 that GitHub can display as code-scanning alerts. The copyable
[`examples/github-code-scanning.yml`](../examples/github-code-scanning.yml) workflow scans every push
to `main`, every pull request, and once a week, then uploads `agentverify.sarif` under the stable
`agentverify` category. AgentVerify's own
[`code-scanning.yml`](../.github/workflows/code-scanning.yml) is a repository-specific reference that
scans `src/` so intentionally vulnerable regression fixtures do not become project alerts;
application repositories should normally scan `.`.

## Add it to a repository

Copy [`examples/github-code-scanning.yml`](../examples/github-code-scanning.yml) into
`.github/workflows/agentverify-code-scanning.yml`. The install step pins the official GitHub
`v0.1.0` tag and does not depend on PyPI. For stricter reproducibility, replace the tag with the
full commit SHA of the release after reviewing it.

The upload job needs these GitHub token permissions:

```yaml
permissions:
  contents: read
  security-events: write
```

Use `github/codeql-action/upload-sarif@v4` with a stable category:

```yaml
- name: Scan repository
  run: agentverify scan . --format sarif --output agentverify.sarif
- name: Upload SARIF to GitHub code scanning
  uses: github/codeql-action/upload-sarif@v4
  with:
    sarif_file: agentverify.sarif
    category: agentverify
```

[GitHub code scanning accepts third-party SARIF](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/integrate-with-existing-tools/upload-sarif-file)
for public repositories. Private and internal repositories need GitHub Code Security enabled. The
checked [`examples/github-code-scanning.sarif`](../examples/github-code-scanning.sarif) artifact is
generated from `agentverify scan cases/approval_callback_bypass --format sarif` and shows the rule
descriptors, `agentverify/v1` partial fingerprints, source locations, result kinds, confidence, and
Agent IR paths that GitHub receives.

The
default AgentVerify exit status does not fail a build merely because review findings exist, so the
SARIF upload still runs. To enforce a policy in a separate step, add a second scan such as:

```yaml
- name: Enforce AgentVerify policy
  run: agentverify scan . --policy agentverify-policy.json
```

Generate the policy schema with `agentverify schema policy`. Policies can independently budget rule
IDs, findings/reviews, and minimum severity while retaining every matched result in the report. The
repository policy may extend checked-in local organization policies; reports retain every source and
gate digest. The legacy `--fail-on high --fail-on-kind finding` threshold remains available for
simple gates.
The checked-in example policies gate all current high-severity approval-review rules; high-severity
approval findings remain covered by the broad high-finding gate.
For a copyable policy-only workflow that keeps enforcement separate from SARIF upload, start from
[`examples/github-policy-gate.yml`](../examples/github-policy-gate.yml).

Keep policy enforcement separate from SARIF generation: a failing scan step otherwise prevents the
upload step unless it uses `if: always()`. For an existing repository, `--baseline` can hide known
fingerprints while new results remain visible; commit and review that baseline as policy data. JSON,
text, and SARIF include counts for new, unchanged, and no-longer-reported fingerprints. The last count
is deliberately unavailable for selected-path scans because unscanned findings are not proven fixed.
Baseline input is fail-closed: AgentVerify accepts only a raw fingerprint list, an AgentVerify JSON
report, a native AI BOM, or SARIF with `agentverify/v1` partial fingerprints. Other JSON objects are
usage errors rather than empty baselines, and malformed entries inside otherwise recognized reports
must still carry the expected fingerprint field.

The workflow deliberately grants `security-events: write` only to the scanning job. Do not pass a
personal token to the upload action; its default is the job-scoped GitHub token.

## Changed-file scans

For a fast pull-request signal, write repository-relative changed paths one per line and pass the
file to AgentVerify:

```console
git diff --name-only --diff-filter=ACMR "$BASE_SHA"...HEAD > changed-files.txt
agentverify scan . --paths-from changed-files.txt --format sarif --output agentverify.sarif
```

Absolute paths and paths containing `..` are rejected. Directory entries select their descendants;
deleted or missing files produce no observations, and an empty list intentionally scans zero files.
JSON, text, and SARIF reports identify `selected-paths` scope and retain the normalized filters.

The repository-wide module index is still available for resolving selected files' imports, but
unselected source files are not parsed. A changed-file result therefore cannot prove repository-wide
control coverage or absence. Keep the scheduled full scan as the authoritative audit and use partial
scans only for rapid feedback.

To prevent permanent exceptions in an enforcement job, add `--require-suppression-expiry`. An inline
directive then suppresses only when it carries a valid, non-expired `until YYYY-MM-DD` date. Expired,
invalid, and missing-expiry directives remain in JSON/text audit data while their findings are
restored and can fail the severity threshold.

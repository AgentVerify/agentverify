# Editor and CI contract export

AgentVerify's JSON report and rule catalog are schema-backed so editor extensions, review bots, and
CI dashboards can consume them without scraping text output.

Export the stable contract bundle:

```console
agentverify contracts \
  --output-dir agentverify-editor-contracts \
  --sample-root examples/safe_agent
```

The exporter writes:

- `agentverify-report-v1.schema.json` — validates `agentverify scan --format json`.
- `agentverify-rules-v1.schema.json` — validates `agentverify rules --format json`.
- `agentverify-rules.json` — the current enabled reporting-rule catalog.
- `agentverify-sample-report.json` — optional sample report when `--sample-root` is provided.
- `manifest.json` — artifact names, `kind`, `contract`, `required`, byte counts, SHA-256 digests,
  and generator version; validates against `agentverify schema editor-contract-manifest`.

Each manifest artifact keeps the original filename-oriented fields and adds `kind`, `contract`, and
`required` so integrations can distinguish required report/rules schemas, the required rules catalog,
and optional sample reports without hard-coding filename conventions.

For installed-package workflows, the equivalent direct commands are:

```console
agentverify schema report --output agentverify-report-v1.schema.json
agentverify schema rules --output agentverify-rules-v1.schema.json
agentverify rules --format json --output agentverify-rules.json
agentverify scan examples/safe_agent --format json --output agentverify-sample-report.json
```

The manifest schema is bundled with installed wheels:

```console
agentverify schema editor-contract-manifest
```

To validate a copied or cached bundle before an editor extension or CI job consumes it, run:

```console
agentverify contracts --verify-dir agentverify-editor-contracts
```

The verifier checks `manifest.json` against the bundled manifest schema, rejects non-basename
artifact paths, confirms every manifest artifact exists, recomputes byte counts and SHA-256 digests,
and validates the rules catalog and sample report against the schemas in the bundle. It exits with
status `1` when the bundle is present but fails verification, and `2` when the manifest or output
path cannot be read or written.

Use `agentverify contracts --verify-dir agentverify-editor-contracts --format summary` for compact
CI logs while keeping JSON as the default machine-readable artifact format.

The verifier JSON is also schema-backed for CI logs and editor bootstrap code:

```console
agentverify schema editor-contract-verification
```

From a source checkout, `python scripts/export_editor_contracts.py` is a thin wrapper around the
same installed package exporter.

For GitHub Actions, start from the copyable
[`examples/github-editor-contracts.yml`](../examples/github-editor-contracts.yml) workflow. It
exports the bundle, writes the manifest and verification JSON as first-class artifacts, validates
both JSON files against the installed schemas, and uploads the verified bundle for editor extension,
review-bot, or custom CI bootstrap jobs.

Editors should use `rule_id`, `result_kind`, `severity`, `confidence`, and `remediation` from the
rules catalog when rendering diagnostics. Normal JSON reports preserve stable finding fingerprints,
source evidence, Agent IR paths, suppression status, baseline summaries, policy summaries, and the
deterministic `risk_summary` counts that CI dashboards can display without walking every finding.

## Mapping findings to editor diagnostics

AgentVerify findings map cleanly to Language Server Protocol-style diagnostics:

- Use `finding.evidence.path` as the file URI/path.
- Convert the 1-based `finding.evidence.line` to a 0-based diagnostic range.
- Map `high` to LSP severity `1` (error), `medium` to `2` (warning), and lower severities to `3`
  (information).
- Use `finding.rule_id` as the diagnostic code and `agentverify` as the source.
- Preserve `fingerprint`, `result_kind`, `confidence`, and `ir_path` in diagnostic `data` so editor
  extensions and review bots can correlate reruns without losing governance context.

[`examples/editor-diagnostics.json`](../examples/editor-diagnostics.json) is a checked example
derived from:

```console
agentverify scan cases/approval_callback_bypass --format json
```

The example intentionally includes both `review` and `finding` result kinds. Editors can choose to
render `review` diagnostics with a different icon or grouping while still preserving AgentVerify's
policy semantics.

## Grouping diagnostics by policy gate

When a scan runs with `--policy`, the JSON report includes `policy_summary.gates[]`. Each gate lists
the `matched_fingerprints` that contributed to its pass/fail decision. Editor extensions and review
bots can join those fingerprints back to diagnostic `data.fingerprint` to show policy-aware groups
without duplicating finding bodies or hiding lower-level diagnostics.

[`examples/editor-policy-diagnostics.json`](../examples/editor-policy-diagnostics.json) is a checked
example derived from:

```console
agentverify scan cases/approval_callback_bypass --policy examples/repository-policy.json --format json
```

The example keeps ordinary LSP-style diagnostics in `diagnostics[]`, adds `policy_gate_ids` and
`policy_status` to each diagnostic's `data`, and exposes `policy_groups[]` with the policy source,
gate threshold, matched summary, and the diagnostic fingerprints matched by that gate.

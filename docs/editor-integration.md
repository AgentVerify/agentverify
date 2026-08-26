# Editor and CI contract export

AgentVerify's JSON report and rule catalog are schema-backed so editor extensions, review bots, and
CI dashboards can consume them without scraping text output.

Export the stable contract bundle:

```console
python scripts/export_editor_contracts.py \
  --output-dir agentverify-editor-contracts \
  --sample-root examples/safe_agent
```

The exporter writes:

- `agentverify-report-v1.schema.json` — validates `agentverify scan --format json`.
- `agentverify-rules-v1.schema.json` — validates `agentverify rules --format json`.
- `agentverify-rules.json` — the current enabled reporting-rule catalog.
- `agentverify-sample-report.json` — optional sample report when `--sample-root` is provided.
- `manifest.json` — artifact names, byte counts, SHA-256 digests, and generator version.

For installed-package workflows, the equivalent direct commands are:

```console
agentverify schema report --output agentverify-report-v1.schema.json
agentverify schema rules --output agentverify-rules-v1.schema.json
agentverify rules --format json --output agentverify-rules.json
agentverify scan examples/safe_agent --format json --output agentverify-sample-report.json
```

Editors should use `rule_id`, `result_kind`, `severity`, `confidence`, and `remediation` from the
rules catalog when rendering diagnostics. Normal JSON reports preserve stable finding fingerprints,
source evidence, Agent IR paths, suppression status, baseline summaries, policy summaries, and the
deterministic `risk_summary` counts that CI dashboards can display without walking every finding.

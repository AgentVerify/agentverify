# Reproducing the evidence

[Documentation index](README.md)

The published results describe curated public regression cases, not unbiased production accuracy.
Checking the existing artifacts is quick and does not rerun corpus collection:

```console
agentverify benchmark verify --require-evaluation-kind public-regression --require-all-passed --format summary
agentverify benchmark verify-engine --format summary
```

Run those commands from a source checkout. To regenerate evidence, use the commands below. Corpus
collection needs network access; full rescans take longer than verification and are not needed to
try the tool. Never use `--refresh` unless intentionally updating the pinned corpus.

## Regenerate results

```console
python3 scripts/collect_repositories.py
python3 scripts/render_repositories.py
PYTHONPATH=src python3 scripts/benchmark_engine.py
PYTHONPATH=src python3 scripts/evaluate_truthset.py
PYTHONPATH=src python3 scripts/evaluate_truthset.py --labels benchmarks/ir-truthset.json \
  --output benchmarks/ir-truthset-results.json
PYTHONPATH=src python3 scripts/evaluate_truthset.py --labels benchmarks/ir-truthset.json \
  --output /tmp/agentverify-sandbox-results.json --check-id IR-TS-OPENAI-SANDBOX \
  --scan-label-paths --progress --format summary
PYTHONPATH=src python3 scripts/evaluate_truthset.py --labels benchmarks/ir-truthset.json \
  --output /tmp/agentverify-ir-results.json --scan-cache-dir .agentverify-cache/scans \
  --progress --format summary
PYTHONPATH=src python3 scripts/evaluate_truthset.py --evaluation-kind sealed-holdout \
  --manifest path/to/holdout-manifest.json --labels path/to/sealed-labels.json \
  --output path/to/holdout-results.json
uv run python scripts/verify_benchmark_results.py --require-evaluation-kind public-regression --require-all-passed
agentverify benchmark verify --require-evaluation-kind public-regression --require-all-passed
agentverify benchmark verify-engine
agentverify holdout validate --manifest benchmarks/holdout-manifest.template.json --labels benchmarks/holdout-labels.template.json
agentverify schema benchmark-result --output agentverify-benchmark-result.schema.json
agentverify schema benchmark-verification --output agentverify-benchmark-verification.schema.json
agentverify schema engine-results --output agentverify-engine-results.schema.json
agentverify schema engine-results-verification --output agentverify-engine-results-verification.schema.json
agentverify schema holdout-manifest --output agentverify-holdout-manifest.schema.json
agentverify schema holdout-labels --output agentverify-holdout-labels.schema.json
```

Use `--scan-label-paths` only for focused development runs: it scans files referenced by the
evaluated labels and records `benchmark.scan_scope: selected-label-paths` in the result metadata.
Add `--expand-local-imports` for focused slices whose labels depend on sibling local imports or
reexports; this records `benchmark.scan_path_expansion: local-import-closure`. `--format summary`
prints a compact pass/fail and failed-check breakdown while still writing the full benchmark-result
JSON file.
For repeated local iterations that need repository-wide semantics, add
`--scan-cache-dir .agentverify-cache/scans`; cached IR is reused only when the scanned source-file
digest and AgentVerify package source digest still match. The cache is for local speed, not a
checked release artifact.
Full public-regression release results should still use repository-wide scans.

The default CI workflow runs the installed CLI benchmark gate against the checked-in public
regression results and validates the verifier JSON against the bundled benchmark-verification schema,
so benchmark-result drift fails during pull requests before release packaging. The verifier artifact
also carries per-result `all_labels_passed`, `failed` counts, and mismatch summaries so release
tooling can distinguish scanner false positives/negatives from stale source anchors or expected
snippets. Source-distribution
verification keeps the copyable GitHub workflow examples tied to their contracts: benchmark
verification emits, validates, and uploads both `agentverify-benchmark-verification.json` and
`agentverify-engine-results-verification.json`, and prints compact summary logs for both verifier
passes; policy-gate and code-scanning examples keep their
expected permissions, trusted-policy validation, and gate/upload commands.
For editor or custom CI integrations, `agentverify contracts --sample-root examples/safe_agent`
exports the report schema, rules schema, current rules catalog, and optional sample report into a
local artifact directory with a schema-backed digest manifest. `agentverify contracts --verify-dir`
rechecks copied bundles before consumers load them, and its JSON result validates against
`agentverify schema editor-contract-verification`. Use
`agentverify contracts --verify-dir ... --format summary` for compact CI logs. The copyable
[`examples/github-editor-contracts.yml`](../examples/github-editor-contracts.yml) workflow exports,
schema-validates, verifies, and uploads that bundle as a CI artifact for editor or review-bot
bootstrap jobs. The editor guide also includes a checked
[`examples/editor-diagnostics.json`](../examples/editor-diagnostics.json) mapping from AgentVerify
findings to Language Server Protocol-style diagnostics and
[`examples/editor-policy-diagnostics.json`](../examples/editor-policy-diagnostics.json) for grouping
diagnostics by policy gate through matched finding fingerprints. Both examples validate against the
bundled `agentverify schema editor-diagnostics` contract, which is also exported by
`agentverify contracts`.

The collector reuses commits from `research/repository-data.json` by default and samples up to 220
source/manifest roots plus at most 20 bounded local source dependencies reached from MCP
forwarding/URL-security roots or listed as audited evidence hints per repository. Use `--refresh` only
when intentionally creating a new upstream snapshot; the refreshed output becomes the next lock.

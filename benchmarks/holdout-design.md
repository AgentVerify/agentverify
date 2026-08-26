# Sealed holdout benchmark design

AgentVerify's checked-in truth sets are public regression suites. They prevent known rule and Agent
IR failures from returning, but they are not an unbiased estimate of accuracy because scanner changes
are made while those labels are visible. A separate sealed holdout is required before publishing
precision/recall claims as product-quality evidence.

## Goals

- Measure rule and IR quality on examples that were not used to design the scanner.
- Preserve reproducibility with pinned repository commits and exact source locations.
- Keep discovery metrics, public regression metrics, and sealed evaluation metrics separate.
- Feed false positives, false negatives, and unsupported syntax back into the public backlog only
  after an evaluation round is closed.

## Non-goals

- Do not use the holdout as another public regression fixture during normal rule development.
- Do not tune thresholds, regexes, graph proofs, or rule metadata after seeing sealed labels unless
  the evaluation round is explicitly closed and archived.
- Do not claim ecosystem-wide prevalence from the holdout; prevalence remains a research-corpus
  measurement.

## Sampling frame

Start from repositories that are not already overrepresented in a rule's public fixtures. Sample
from three buckets:

1. Pinned research-corpus repositories with source roots not used as direct rule fixtures.
2. Newly selected public repositories from the same ecosystem categories in
   [`research/corpus.csv`](../research/corpus.csv).
3. Negative-control repositories that use adjacent packages, tests, examples, or documentation-heavy
   code where AgentVerify should avoid reporting.

Every sampled repository must record:

- repository URL and commit;
- selected source roots and manifest/config roots;
- language/framework/category stratum;
- whether dependency-materialized files are included;
- reason the sample was selected;
- excluded paths and reason for exclusion.

## Strata

Maintain separate strata so a strong result in one area does not hide weakness in another:

| Stratum | Minimum target | Examples |
|---|---:|---|
| Reporting rules | 8–12 labeled positives/negatives per enabled rule where real cases exist | shell, filesystem, approval, MCP, network, audit, sandbox |
| Agent IR components | 150+ component labels | frameworks, providers, agents, tools, MCP servers, controls |
| Agent IR relationships | 150+ relationship labels | agent→tool, tool→capability, tool→control, agent→MCP, server→tool |
| Ambiguity/negative controls | 100+ labels | rebindings, near packages, docs/tests-only cases, incomplete compositions |
| Integration artifacts | 20+ smoke checks | JSON report, AI BOM, SARIF, policy, baseline, schema commands |

The minimums are starting targets, not publication thresholds. Increase them for rules with high
variance or sparse positives.

## Label protocol

1. Freeze a candidate sample manifest before scanning with the current development branch.
2. Assign each location an ID, source path, line, label kind, expected result, and a short rationale.
3. Use two reviewers when possible. Resolve disagreements into a third adjudicated label with the
   alternatives preserved.
4. Record "unsupported" separately from "negative" when the code expresses a real pattern that
   AgentVerify intentionally does not support yet.
5. Store sealed labels outside the public regression files until the evaluation round closes.

Recommended label fields mirror the public truth-set shape:

```json
{
  "id": "holdout-AV-EXEC001-001",
  "target": {
    "kind": "repository",
    "repository": "owner/name",
    "commit": "0123456789abcdef"
  },
  "path": "src/agent/tool.py",
  "line": 42,
  "rule_id": "AV-EXEC001",
  "expected": true,
  "source_contains": "subprocess.run(command, shell=True)",
  "rationale": "Model-supplied command reaches a shell execution primitive."
}
```

## Leakage controls

- Keep sealed labels in a private location or encrypted artifact until an evaluation round is
  complete.
- Do not commit failing holdout examples directly into `cases/` until after the round is closed.
- When a holdout failure becomes a public regression, record the closed evaluation ID and create a
  new replacement holdout sample.
- Report both pre-fix and post-fix metrics if a released evaluation led to scanner changes.

## Metrics

Publish metrics by stratum and rule, not only as an aggregate:

- true positives, false positives, true negatives, false negatives;
- precision and recall where denominators are meaningful;
- unsupported count and category;
- parse/scan warnings;
- runtime and files scanned;
- top failure classes with examples.

For Agent IR labels, report component and relationship metrics separately. For integration artifacts,
report pass/fail smoke checks instead of precision/recall.

## Current local next step

Without external trust or private storage access, the safe local step is to keep public templates for
the sample manifest and label shape:

- [`holdout-manifest.template.json`](holdout-manifest.template.json)
- [`holdout-labels.template.json`](holdout-labels.template.json)

The evaluator accepts an alternate label file through `--labels` plus
`--evaluation-kind sealed-holdout` and `--manifest`, so CI or a trusted maintainer can supply a sealed
label path without checking private labels into the public regression corpus. Result JSON conforms to
[`benchmark-results-v1.schema.json`](benchmark-results-v1.schema.json) and records the evaluation
kind, label scope, input hashes, manifest hash, and claim scope. The actual sealed labels should wait
for approved storage and reviewer workflow.

# Policy as code

AgentVerify policies turn reported results into auditable CI gates without disabling rules or hiding
evidence. Policies are JSON documents conforming to the bundled schema:

```console
agentverify schema policy --output agentverify-policy.schema.json
agentverify scan . --policy agentverify-policy.json
```

The checked-in [`ci-policy.json`](../examples/ci-policy.json) rejects new high-severity findings and
approval-bypass reviews. A policy contains one or more independent count budgets:

```json
{
  "schema_version": 1,
  "name": "production",
  "gates": [
    {
      "id": "no-high-findings",
      "result_kinds": ["finding"],
      "min_severity": "high",
      "max_count": 0
    },
    {
      "id": "mcp-review-budget",
      "rules": ["AV-MCP002"],
      "result_kinds": ["review"],
      "min_severity": "high",
      "max_count": 3
    }
  ]
}
```

## Gate semantics

Each gate counts results satisfying all configured filters:

- `rules`: exact rule IDs; omit it to include every rule.
- `result_kinds`: `finding` and/or `review`; omitted defaults to `finding`.
- `min_severity`: `info`, `low`, `medium`, or `high`; omitted defaults to `high`.
- `max_count`: required non-negative count. The gate passes when matches are less than or equal to
  this value.

All gates must pass. Exit status is `1` when a policy gate or an explicit `--fail-on` threshold fails,
`2` for an invalid policy, and `0` otherwise. `--fail-on` and `--policy` are additive.

Policies are deliberately non-hiding. Matching findings remain in text, JSON, AI BOM, and SARIF
output. Each report includes the policy name, source filename, SHA-256 digest, overall status, gate
filters, matched counts, and matching fingerprints. Unknown fields, duplicate gate IDs, invalid
enumerations, and negative budgets are rejected rather than ignored.

## Organization policy composition

A repository policy can extend one or more local organization or team policies. References are
resolved relative to the policy that declares them, so a checked-in hierarchy remains portable:

```json
{
  "schema_version": 1,
  "name": "repository-release",
  "extends": ["org-policy.json"],
  "gates": [
    {
      "id": "repository-mcp-budget",
      "rules": ["AV-MCP002"],
      "result_kinds": ["review"],
      "max_count": 2
    }
  ]
}
```

[`repository-policy.json`](../examples/repository-policy.json) and
[`org-policy.json`](../examples/org-policy.json) are a runnable pair. Base policies are composed
depth first in listed order, followed by the declaring policy's gates. A policy may contain only
`extends`; each resolved file contributes its gates once. Gate IDs must be unique across the entire
composition. Cycles, compositions deeper than 32 files, absolute paths, URL references, unreadable
files, and malformed included policies fail before scanning.

Reports retain the root policy's source and digest, a source/digest entry for every composed file,
and the source/digest that contributed each gate. These hashes make the evaluated local inputs
auditable; they are not signatures and do not prove who authored a policy.

## Baselines and partial scans

Policy evaluation occurs after `--baseline`, so a gate applies to new results while unchanged known
fingerprints remain accounted for in the baseline summary. This ordering is recorded as
`evaluated_after_baseline: true` in the policy summary.

A selected-path policy run only evaluates results from those selected paths. It cannot prove that the
repository as a whole satisfies the policy. Use it for pull-request feedback and retain a scheduled
full-repository policy scan as the authoritative gate.

Policy budgets are not exceptions. A reviewed, time-bounded exception belongs in an inline
suppression with a rule ID, reason, and expiry date; a baseline records accepted existing debt.

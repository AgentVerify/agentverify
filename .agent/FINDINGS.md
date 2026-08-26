# AgentVerify findings

## Durable facts

- The repository contains a 71-repository pinned research corpus and schema-v123 benchmark outputs.
- The runtime catalog currently contains 24 enabled reporting rules.
- JSON reports, AI BOMs, policies, and rule-catalog JSON now have bundled schemas.
- A freshly rebuilt wheel includes all four runtime schemas; a verifier script now guards that
  package artifact expectation.
- Policy evaluation occurs after baseline filtering and preserves matched findings in all report
  formats.
- Published precision/recall numbers still describe public seed/regression labels only; the holdout
  design records how to produce an unbiased sealed evaluation later.
- The evaluator already accepts alternate `--labels` paths, so sealed labels can be supplied by CI or
  a trusted maintainer without committing them publicly.
- Benchmark result JSON now records evaluation kind, label scope, input digests, sealed status, and
  claim scope, reducing the risk that public regression metrics are reused as holdout claims.

## Hypotheses

- Schema-backed machine contracts reduce adoption friction for CI, editor, and governance tooling
  more effectively than prose-only documentation.
- A separately sampled sealed holdout benchmark will become the next credibility bottleneck once the
  public regression corpus continues to grow.

## Implications

- Keep every contract change covered by runtime/schema consistency tests.
- Avoid external trust/authenticity claims until there is an explicit trust-root design.

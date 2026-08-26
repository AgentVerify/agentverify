# Benchmark release checklist

AgentVerify keeps three benchmark concepts separate:

- discovery measurements from the pinned research corpus;
- public regression metrics from checked-in truth sets;
- sealed holdout metrics from labels that were not visible during scanner development.

Use this checklist before copying benchmark numbers into a release note, README, package page, or
external integration guide.

## Public regression release

Public truth-set results are suitable for claims like "the checked-in regression labels pass at this
commit." They are not suitable for ecosystem-wide precision/recall claims.

```console
PYTHONPATH=src python3 scripts/evaluate_truthset.py
PYTHONPATH=src python3 scripts/evaluate_truthset.py --labels benchmarks/ir-truthset.json \
  --output benchmarks/ir-truthset-results.json
uv run python scripts/verify_benchmark_results.py \
  --require-evaluation-kind public-regression
```

Before publishing public regression numbers:

1. Confirm `benchmarks/truthset-results.json` and `benchmarks/ir-truthset-results.json` were
   regenerated from the same commit being released.
2. Run `uv run python scripts/verify_benchmark_results.py --require-evaluation-kind
   public-regression` and keep the JSON output with the release notes.
3. State the claim boundary explicitly: curated public regression metrics, not an unbiased ecosystem
   accuracy estimate.
4. If a result file changes, review the per-label outcomes rather than relying only on aggregate
   precision and recall.

## Sealed holdout release

Sealed holdout results are the only benchmark results that can support an unbiased accuracy claim,
and only if labels stayed hidden until the evaluation round closed.

```console
PYTHONPATH=src python3 scripts/evaluate_truthset.py \
  --evaluation-kind sealed-holdout \
  --manifest path/to/holdout-manifest.json \
  --labels path/to/sealed-labels.json \
  --output path/to/holdout-results.json

uv run python scripts/verify_benchmark_results.py path/to/holdout-results.json \
  --require-evaluation-kind sealed-holdout \
  --require-sealed \
  --require-manifest
```

Before publishing sealed holdout numbers:

1. Freeze and archive the manifest before running the scanner.
2. Keep labels private or encrypted until the round is closed.
3. Run the verifier with `--require-evaluation-kind sealed-holdout`, `--require-sealed`, and
   `--require-manifest`.
4. Publish the result file, manifest digest, label digest, label scope, and claim scope together.
5. If the holdout exposes failures, report pre-fix and post-fix metrics separately. Move any
   released failures into public regression coverage only after the round is closed.

## Wording guardrails

Allowed wording for public results:

- "All checked-in public regression labels pass."
- "Public reporting-rule regression labels currently show 1.0 precision/recall on the curated truth
  set."

Avoid wording for public results:

- "AgentVerify has 100% precision and recall."
- "AgentVerify is unbiasedly validated across the AI-agent ecosystem."
- "Public regression metrics prove production accuracy."

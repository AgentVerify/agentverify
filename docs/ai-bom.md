# Native AI BOM

AgentVerify can emit a deterministic, evidence-first inventory of an agent application:

```console
agentverify scan . --format bom > agentverify.bom.json
agentverify schema bom > agentverify-ai-bom.schema.json
```

The format is defined by
[`agentverify-ai-bom-v1.schema.json`](../src/agentverify/schemas/agentverify-ai-bom-v1.schema.json).
It is native to AgentVerify and does not claim CycloneDX or SPDX conformance.
The `schema` command reads the copy bundled in the installed wheel, so validators do not need a
source checkout.

The current format version is 1.1. Version 1.1 adds evidence-local relationship endpoint resolution;
the filename remains `v1` because the major schema contract is unchanged.

## Why a native format

[CycloneDX 1.7](https://cyclonedx.org/specification/overview/) can represent software, services,
machine-learning models, datasets, dependencies, and model cards. The
[SPDX 3.0.1 AI profile](https://spdx.github.io/spdx-spec/v3.0.1/conformance/) likewise standardizes
AI/ML system and model information. AgentVerify also needs to preserve source-level agents, tools,
privileged capabilities, governing controls, risky paths, and unresolved symbol identity. Mapping
those facts into either standard without a reviewed profile would overstate interoperability.

The native BOM is therefore the lossless exchange format. A future CycloneDX or SPDX adapter should
map only fields with defined semantics, retain the native evidence as an external artifact, and be
validated against the relevant official schema.

## Contract

The top-level document contains:

- `metadata`: generator version, full or selected-path scope, scanned-file counts, parse warnings,
  suppressions, baseline summary, and policy decision summary. `root` is always `.` and evidence
  paths are relative to it, so local checkout paths are not disclosed.
- `assets`: every Agent IR component with a stable `avc-*` ID, kind, display name, attributes, and
  exact path/line/excerpt evidence. Source-defined agents and tools also retain their Agent IR
  `symbol_id`.
- `relationships`: sorted `avr-*` graph observations with evidence and source/target identity status.
- `governance`: control and sandbox-boundary asset IDs, assets carrying unresolved policy values, and
  risk counts by rule, result kind, and severity.
- `risks`: fingerprinted findings/reviews with remediation, Agent IR path, and resolved or unresolved
  control analysis.

Asset IDs are derived from component kind, display name, path, and line. Relationship IDs additionally
include edge type and both endpoints. There is no generation timestamp, so the same Agent IR produces
byte-for-byte identical BOM output.

## Identity and uncertainty

AgentVerify does not pretend display names are globally unique. A relationship endpoint is marked:

- `symbol-id` when its module-qualified Agent IR ID resolves to exactly one observed asset;
- `evidence-location` when an endpoint without a symbol ID uniquely matches the relationship's exact
  path and line (or an explicit control location carried by the edge); the endpoint records that
  basis as `resolution_path` and `resolution_line`;
- `unique-display-name` when exactly one matching observed asset exists;
- `ambiguous` with all candidate asset IDs when multiple observations share that kind and name;
- `unresolved` when no matching asset observation exists.

`unique-display-name` is an inventory fallback, not a proof of module-qualified identity. Consumers
that enforce policy should prefer `symbol-id`, then `evidence-location`, and treat `ambiguous` and
`unresolved` endpoints as review requirements. Symbol IDs never fall back to coincidental locations
when their target is missing or duplicated. The same principle applies to
`unresolved_policy_asset_ids`: a missing proof is not silently converted into an absent control.

Repeated Python and TypeScript constructor bindings receive occurrence-qualified symbol IDs such as
`#agent:agent@42` for their direct source edges. A later reference to a repeated binding does not pick
an occurrence by name; its relationship attributes record
`target_identity: ambiguous-repeated-binding`, and without assignment-sensitive evidence that target
stays ambiguous or unresolved.

Selected-path scans remain partial. Their metadata records `scan_scope: selected-paths` and the exact
filters; baseline output does not claim that omitted fingerprints are resolved.

A saved native BOM can be passed back through `--baseline`; its risk IDs are the same stable finding
fingerprints used by JSON and SARIF reports.

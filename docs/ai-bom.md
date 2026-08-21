# Native AI BOM

AgentVerify can emit a deterministic, evidence-first inventory of an agent application:

```console
agentverify scan . --format bom > agentverify.bom.json
```

The format is defined by
[`agentverify-ai-bom-v1.schema.json`](../src/agentverify/schemas/agentverify-ai-bom-v1.schema.json).
It is native to AgentVerify and does not claim CycloneDX or SPDX conformance.

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
  suppressions, and baseline summary. `root` is always `.` and evidence paths are relative to it, so
  local checkout paths are not disclosed.
- `assets`: every Agent IR component with a stable `avc-*` ID, kind, display name, attributes, and
  exact path/line/excerpt evidence.
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

- `unique-display-name` when exactly one matching observed asset exists;
- `ambiguous` with all candidate asset IDs when multiple observations share that kind and name;
- `unresolved` when no matching asset observation exists.

`unique-display-name` is an inventory property, not a proof of module-qualified identity. Consumers
that enforce policy should treat `ambiguous` and `unresolved` endpoints as review requirements. The
same principle applies to `unresolved_policy_asset_ids`: a missing proof is not silently converted
into an absent control.

Selected-path scans remain partial. Their metadata records `scan_scope: selected-paths` and the exact
filters; baseline output does not claim that omitted fingerprints are resolved.

A saved native BOM can be passed back through `--baseline`; its risk IDs are the same stable finding
fingerprints used by JSON and SARIF reports.

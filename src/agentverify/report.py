"""AgentVerify report renderers."""

from __future__ import annotations

import json
from collections import Counter
from hashlib import sha256
from importlib.resources import files

from . import __version__
from .ir import Component, Evidence, Relationship, RepositoryIR


def render_json(ir: RepositoryIR) -> str:
    return json.dumps(ir.to_dict(), indent=2, sort_keys=True) + "\n"


def render_schema(name: str) -> str:
    filenames = {
        "bom": "agentverify-ai-bom-v1.schema.json",
        "policy": "agentverify-policy-v1.schema.json",
    }
    schema = files("agentverify").joinpath(f"schemas/{filenames[name]}")
    return schema.read_text(encoding="utf-8")


def render_bom_schema() -> str:
    return render_schema("bom")


def _stable_id(prefix: str, values: tuple[object, ...]) -> str:
    encoded = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
    return f"{prefix}-{sha256(encoded.encode('utf-8')).hexdigest()[:20]}"


def _evidence_dict(evidence: Evidence) -> dict[str, object]:
    return {
        "path": evidence.path,
        "line": evidence.line,
        "excerpt": evidence.excerpt,
    }


def _component_id(component: Component) -> str:
    return _stable_id(
        "avc",
        (
            component.kind,
            component.name,
            component.evidence.path,
            component.evidence.line,
            component.symbol_id,
        ),
    )


def _relationship_id(relationship: Relationship) -> str:
    return _stable_id(
        "avr",
        (
            relationship.source_kind,
            relationship.source_name,
            relationship.relation,
            relationship.target_kind,
            relationship.target_name,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.source_id,
            relationship.target_id,
        ),
    )


def render_bom(ir: RepositoryIR) -> str:
    """Render AgentVerify's evidence-first native AI BOM.

    This is deliberately not labelled CycloneDX or SPDX: those formats do not directly represent
    every agent, capability, control, and uncertain identity in Agent IR.
    """

    ordered_components = sorted(
        ir.components,
        key=lambda item: (
            item.kind,
            item.name,
            item.evidence.path,
            item.evidence.line,
            item.symbol_id or "",
        ),
    )
    assets = [
        {
            "id": _component_id(component),
            "kind": component.kind,
            "name": component.name,
            "attributes": component.attributes,
            "evidence": _evidence_dict(component.evidence),
            **({"symbol_id": component.symbol_id} if component.symbol_id else {}),
        }
        for component in ordered_components
    ]
    assets_by_display_name: dict[tuple[str, str], list[str]] = {}
    assets_by_symbol_id: dict[str, list[str]] = {}
    assets_by_evidence_location: dict[tuple[str, str, str, int], list[str]] = {}
    for component in ordered_components:
        assets_by_display_name.setdefault((component.kind, component.name), []).append(
            _component_id(component)
        )
        if component.symbol_id:
            assets_by_symbol_id.setdefault(component.symbol_id, []).append(_component_id(component))
        assets_by_evidence_location.setdefault(
            (
                component.kind,
                component.name,
                component.evidence.path,
                component.evidence.line,
            ),
            [],
        ).append(_component_id(component))

    def endpoint(
        kind: str,
        name: str,
        symbol_id: str | None,
        location: tuple[str, int],
    ) -> dict[str, object]:
        value: dict[str, object] = {"kind": kind, "name": name}
        if symbol_id:
            value["symbol_id"] = symbol_id
            candidates = sorted(assets_by_symbol_id.get(symbol_id, []))
            if len(candidates) == 1:
                value.update({"resolution": "symbol-id", "asset_id": candidates[0]})
            elif candidates:
                value.update({"resolution": "ambiguous", "candidate_asset_ids": candidates})
            else:
                value["resolution"] = "unresolved"
            return value
        location_candidates = sorted(assets_by_evidence_location.get((kind, name, *location), []))
        if len(location_candidates) == 1:
            value.update(
                {
                    "resolution": "evidence-location",
                    "asset_id": location_candidates[0],
                    "resolution_path": location[0],
                    "resolution_line": location[1],
                }
            )
            return value
        if location_candidates:
            value.update(
                {
                    "resolution": "ambiguous",
                    "candidate_asset_ids": location_candidates,
                }
            )
            return value
        candidates = sorted(assets_by_display_name.get((kind, name), []))
        if len(candidates) == 1:
            value.update({"resolution": "unique-display-name", "asset_id": candidates[0]})
        elif candidates:
            value.update({"resolution": "ambiguous", "candidate_asset_ids": candidates})
        else:
            value["resolution"] = "unresolved"
        return value

    ordered_relationships = sorted(
        ir.relationships,
        key=lambda item: (
            item.source_kind,
            item.source_name,
            item.relation,
            item.target_kind,
            item.target_name,
            item.evidence.path,
            item.evidence.line,
            item.source_id or "",
            item.target_id or "",
        ),
    )
    relationships = []
    for relationship in ordered_relationships:
        target_path = relationship.evidence.path
        target_line = relationship.evidence.line
        if (
            relationship.target_kind == "control"
            and isinstance(relationship.attributes.get("control_path"), str)
            and isinstance(relationship.attributes.get("control_line"), int)
        ):
            target_path = relationship.attributes["control_path"]
            target_line = relationship.attributes["control_line"]
        relationships.append(
            {
                "id": _relationship_id(relationship),
                "source": endpoint(
                    relationship.source_kind,
                    relationship.source_name,
                    relationship.source_id,
                    (relationship.evidence.path, relationship.evidence.line),
                ),
                "relation": relationship.relation,
                "target": endpoint(
                    relationship.target_kind,
                    relationship.target_name,
                    relationship.target_id,
                    (target_path, target_line),
                ),
                "attributes": relationship.attributes,
                "evidence": _evidence_dict(relationship.evidence),
            }
        )

    unresolved_policy_assets = sorted(
        asset["id"]
        for asset in assets
        if any(
            isinstance(value, str) and value.startswith("unresolved")
            for value in asset["attributes"].values()
        )
    )
    risks = [
        {
            "id": finding.fingerprint,
            "rule_id": finding.rule_id,
            "severity": finding.severity,
            "confidence": finding.confidence,
            "result_kind": finding.result_kind,
            "message": finding.message,
            "remediation": finding.remediation,
            "evidence": _evidence_dict(finding.evidence),
            "ir_path": list(finding.ir_path),
            "analysis": finding.analysis,
        }
        for finding in sorted(
            ir.findings,
            key=lambda item: (
                item.rule_id,
                item.evidence.path,
                item.evidence.line,
                item.fingerprint,
            ),
        )
    ]
    payload = {
        "bom_format": "AgentVerify AI BOM",
        "spec_version": "1.1",
        "metadata": {
            "generator": {"name": "AgentVerify", "version": __version__},
            "root": ".",
            "scan_scope": ir.scan_scope,
            "path_filters": ir.path_filters,
            "files_scanned": ir.files_scanned,
            "configuration_files_scanned": ir.config_files_scanned,
            "parse_warnings": len(ir.errors),
            "suppressed_findings": ir.suppressed_findings,
            "baseline_summary": ir.baseline_summary,
            "policy_summary": ir.policy_summary,
        },
        "assets": assets,
        "relationships": relationships,
        "governance": {
            "control_asset_ids": sorted(
                asset["id"] for asset in assets if asset["kind"] in {"control", "control-setting"}
            ),
            "boundary_asset_ids": sorted(
                asset["id"] for asset in assets if asset["kind"] == "sandbox-boundary"
            ),
            "unresolved_policy_asset_ids": unresolved_policy_assets,
            "risk_summary": {
                "by_rule": dict(sorted(Counter(risk["rule_id"] for risk in risks).items())),
                "by_result_kind": dict(
                    sorted(Counter(risk["result_kind"] for risk in risks).items())
                ),
                "by_severity": dict(sorted(Counter(risk["severity"] for risk in risks).items())),
            },
        },
        "risks": risks,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_sarif(ir: RepositoryIR) -> str:
    rules = {}
    results = []
    level = {"high": "error", "medium": "warning", "low": "note", "info": "note"}
    for finding in ir.findings:
        rules.setdefault(
            finding.rule_id,
            {
                "id": finding.rule_id,
                "name": finding.rule_id,
                "shortDescription": {"text": finding.message},
                "help": {"text": finding.remediation},
                "properties": {
                    "defaultSeverity": finding.severity,
                    "precision": finding.confidence,
                },
            },
        )
        results.append(
            {
                "ruleId": finding.rule_id,
                "level": level.get(finding.severity, "warning"),
                "message": {"text": finding.message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": finding.evidence.path},
                            "region": {"startLine": finding.evidence.line},
                        }
                    }
                ],
                "partialFingerprints": {"agentverify/v1": finding.fingerprint},
                "properties": {
                    "confidence": finding.confidence,
                    "resultKind": finding.result_kind,
                    "irPath": list(finding.ir_path),
                    "analysis": finding.analysis,
                },
            }
        )
    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "AgentVerify",
                        "rules": [rules[key] for key in sorted(rules)],
                    }
                },
                "properties": {
                    "scanScope": ir.scan_scope,
                    "pathFilters": ir.path_filters,
                    "baselineSummary": ir.baseline_summary,
                    "policySummary": ir.policy_summary,
                },
                "results": results,
            }
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_text(ir: RepositoryIR) -> str:
    component_counts = Counter(component.kind for component in ir.components)
    lines = [
        "AgentVerify Report",
        f"Root: {ir.root}",
        f"Scan scope: {ir.scan_scope}",
        f"Path filters: {len(ir.path_filters)}",
        f"Files scanned: {ir.files_scanned}",
        f"Configuration files scanned: {ir.config_files_scanned}",
        f"Suppressed findings: {ir.suppressed_findings}",
    ]
    if ir.baseline_summary:
        no_longer_reported = ir.baseline_summary["no_longer_reported"]
        lines.append(
            "Baseline: "
            f"{ir.baseline_summary['new']} new, "
            f"{ir.baseline_summary['unchanged']} unchanged, "
            + (
                f"{no_longer_reported} no longer reported"
                if no_longer_reported is not None
                else "no-longer-reported count unavailable for partial scan"
            )
        )
    if ir.policy_summary:
        status = "passed" if ir.policy_summary["passed"] else "failed"
        lines.append(
            f"Policy: {ir.policy_summary['name']} [{status}; {len(ir.policy_summary['gates'])} gates]"
        )
        for gate in ir.policy_summary["gates"]:
            gate_status = "passed" if gate["passed"] else "failed"
            lines.append(
                f"  {gate['id']}: {gate['matched_count']} matched / "
                f"{gate['max_count']} allowed [{gate_status}]"
            )
    lines += ["", "AI Components:"]
    if not ir.components:
        lines.append("  None detected")
    for kind in sorted(component_counts):
        names = sorted({component.name for component in ir.components if component.kind == kind})
        lines.append(f"  {kind} ({component_counts[kind]}): {', '.join(names)}")
    lines += ["", "Relationships:"]
    if not ir.relationships:
        lines.append("  None resolved")
    for relationship in ir.relationships:
        lines.append(
            f"  {relationship.source_kind}:{relationship.source_name} "
            f"--{relationship.relation}--> "
            f"{relationship.target_kind}:{relationship.target_name} "
            f"({relationship.evidence.path}:{relationship.evidence.line})"
        )
    lines += ["", "Risk Findings:"]
    if not ir.findings:
        lines.append("  No findings")
    for finding in ir.findings:
        lines += [
            (
                f"  {finding.severity.upper()} {finding.rule_id} "
                f"[{finding.confidence}; {finding.result_kind}]"
            ),
            f"    {finding.message}",
            f"    {finding.evidence.path}:{finding.evidence.line}",
        ]
        if finding.ir_path:
            lines.append(f"    Path: {' -> '.join(finding.ir_path)}")
        if finding.analysis.get("approval_coverage"):
            lines.append(f"    Approval coverage: {finding.analysis['approval_coverage']}")
        if finding.analysis.get("audit_coverage"):
            lines.append(f"    Audit coverage: {finding.analysis['audit_coverage']}")
        lines.append(f"    Remediation: {finding.remediation}")
    if ir.suppressions:
        lines += ["", "Inline suppression directives:"]
        for suppression in ir.suppressions:
            expiry = f" until {suppression.expires_on}" if suppression.expires_on else ""
            lines.append(
                f"  {suppression.rule_id} at {suppression.finding.path}:"
                f"{suppression.finding.line} [{suppression.status}{expiry}] -- {suppression.reason}"
            )
    if ir.errors:
        lines += ["", f"Parse warnings: {len(ir.errors)}"]
    return "\n".join(lines) + "\n"

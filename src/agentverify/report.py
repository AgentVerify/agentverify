"""AgentVerify report renderers."""

from __future__ import annotations

import json
from collections import Counter

from .ir import RepositoryIR


def render_json(ir: RepositoryIR) -> str:
    return json.dumps(ir.to_dict(), indent=2, sort_keys=True) + "\n"


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
                        "informationUri": "https://github.com/agentverify/agentverify",
                        "rules": [rules[key] for key in sorted(rules)],
                    }
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
        f"Files scanned: {ir.files_scanned}",
        f"Configuration files scanned: {ir.config_files_scanned}",
        f"Suppressed findings: {ir.suppressed_findings}",
        "",
        "AI Components:",
    ]
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
        lines += ["", "Inline suppressions:"]
        for suppression in ir.suppressions:
            lines.append(
                f"  {suppression.rule_id} at {suppression.finding.path}:"
                f"{suppression.finding.line} -- {suppression.reason}"
            )
    if ir.errors:
        lines += ["", f"Parse warnings: {len(ir.errors)}"]
    return "\n".join(lines) + "\n"

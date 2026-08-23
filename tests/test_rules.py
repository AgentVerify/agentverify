from __future__ import annotations

import ast
from pathlib import Path

from agentverify.ir import Component, Evidence, Relationship, RepositoryIR
from agentverify.rules import REPORTING_RULE_IDS, RULE_CATALOG, RULE_DEFINITIONS, run_rules

ROOT = Path(__file__).resolve().parents[1]


def test_rule_catalog_covers_every_emission_site_with_matching_metadata() -> None:
    assert tuple(RULE_CATALOG) == tuple(
        definition.rule_id for definition in RULE_DEFINITIONS
    )
    assert len(RULE_CATALOG) == 21
    assert REPORTING_RULE_IDS == frozenset(RULE_CATALOG)
    assert all(
        definition.summary and definition.remediation
        for definition in RULE_DEFINITIONS
    )

    tree = ast.parse(
        (ROOT / "src/agentverify/rules.py").read_text(encoding="utf-8")
    )
    emitted: set[str] = set()
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "make_finding"
        ):
            continue
        rule_id, severity, confidence = (
            node.args[index].value for index in (2, 3, 4)
        )
        result_kind = node.args[7].value if len(node.args) > 7 else "finding"
        definition = RULE_CATALOG[rule_id]
        assert (
            result_kind,
            severity,
            confidence,
        ) == (
            definition.result_kind,
            definition.severity,
            definition.confidence,
        )
        emitted.add(rule_id)
    assert emitted == set(RULE_CATALOG)


def _audit_ir(
    *,
    scope: str = "production",
    edge_line: int = 7,
    durability: str = "durable-relational-database",
    actor_attribution: str = "unresolved-nullable-and-unset",
) -> RepositoryIR:
    evidence = Evidence("agent.py", 7, "await execute_action()")
    ir = RepositoryIR("fixture")
    ir.add_component(
        Component(
            "capability",
            "external-action",
            evidence,
            {"scope": scope},
        )
    )
    ir.add_relationship(
        Relationship(
            "capability",
            "external-action",
            "governed-by",
            "control",
            "durable-action-record",
            Evidence("agent.py", edge_line, "await execute_action()"),
            {
                "scope": scope,
                "durability": durability,
                "actor_attribution": actor_attribution,
            },
        )
    )
    run_rules(ir)
    return ir


def test_audit_actor_gap_requires_exact_production_durable_record() -> None:
    ir = _audit_ir()

    finding = next(item for item in ir.findings if item.rule_id == "AV-AUDIT001")
    assert finding.evidence == Evidence("agent.py", 7, "await execute_action()")
    assert finding.result_kind == "review"
    assert finding.severity == "medium"
    assert finding.confidence == "high"


def test_audit_actor_gap_rejects_unproven_rule_states() -> None:
    candidates = (
        _audit_ir(scope="example"),
        _audit_ir(edge_line=8),
        _audit_ir(durability="in-memory"),
        _audit_ir(actor_attribution="attributable-user-and-session"),
    )

    assert all(
        not any(finding.rule_id == "AV-AUDIT001" for finding in ir.findings)
        for ir in candidates
    )

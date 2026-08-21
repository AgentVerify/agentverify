from __future__ import annotations

from agentverify.ir import Component, Evidence, Relationship, RepositoryIR
from agentverify.rules import run_rules


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

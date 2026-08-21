from __future__ import annotations

import pytest

from agentverify.policy import PolicyError, normalize_policy


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"schema_version": True, "gates": [{"id": "gate", "max_count": 0}]}, "schema_version"),
        (
            {
                "schema_version": 1,
                "gates": [{"id": "gate", "min_severity": [], "max_count": 0}],
            },
            "min_severity",
        ),
        (
            {"schema_version": 1, "gates": [{"id": "gate", "rules": [""], "max_count": 0}]},
            "rules",
        ),
        (
            {
                "schema_version": 1,
                "gates": [{"id": "same", "max_count": 0}, {"id": "same", "max_count": 1}],
            },
            "duplicate gate id",
        ),
        ({"schema_version": 1, "gates": []}, "non-empty array"),
    ],
)
def test_malformed_policies_are_rejected_as_policy_errors(payload: object, message: str) -> None:
    with pytest.raises(PolicyError, match=message):
        normalize_policy(payload)


def test_policy_normalization_trims_identifiers_and_applies_defaults() -> None:
    assert normalize_policy(
        {
            "schema_version": 1,
            "name": " production ",
            "gates": [{"id": " high ", "rules": [" AV-EXEC001 "], "max_count": 0}],
        }
    ) == {
        "schema_version": 1,
        "name": "production",
        "gates": [
            {
                "id": "high",
                "rules": ["AV-EXEC001"],
                "result_kinds": ["finding"],
                "min_severity": "high",
                "max_count": 0,
            }
        ],
    }

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentverify.policy import PolicyError, load_policy, normalize_policy


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
                "gates": [{"id": "gate", "rules": ["AV-EXECC001"], "max_count": 0}],
            },
            "rules contains unsupported values: AV-EXECC001",
        ),
        (
            {
                "schema_version": 1,
                "gates": [{"id": "gate", "rules": ["AV-AI001"], "max_count": 0}],
            },
            "rules contains unsupported values: AV-AI001",
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


def test_policy_can_contain_only_local_policy_references() -> None:
    assert normalize_policy(
        {"schema_version": 1, "name": " repository ", "extends": ["org.json"]}
    ) == {
        "schema_version": 1,
        "name": "repository",
        "extends": ["org.json"],
        "gates": [],
    }


def test_policy_composition_is_depth_first_and_retains_source_digests(tmp_path: Path) -> None:
    policies = tmp_path / "policies"
    policies.mkdir()
    (policies / "org.json").write_text(
        '{"schema_version":1,"name":"org","gates":[{"id":"org-high","max_count":0}]}',
        encoding="utf-8",
    )
    (policies / "team.json").write_text(
        '{"schema_version":1,"name":"team","extends":["org.json"],'
        '"gates":[{"id":"team-reviews","result_kinds":["review"],"max_count":2}]}',
        encoding="utf-8",
    )
    root = policies / "repository.json"
    root.write_text(
        '{"schema_version":1,"name":"repository","extends":["team.json"],'
        '"gates":[{"id":"repository-shell","rules":["AV-EXEC001"],"max_count":0}]}',
        encoding="utf-8",
    )

    policy, root_digest = load_policy(root)

    assert policy["name"] == "repository"
    assert [gate["id"] for gate in policy["gates"]] == [
        "org-high",
        "team-reviews",
        "repository-shell",
    ]
    assert [source["source"] for source in policy["_sources"]] == [
        "org.json",
        "team.json",
        "repository.json",
    ]
    assert all(len(source["sha256"]) == 64 for source in policy["_sources"])
    assert root_digest == policy["_sources"][-1]["sha256"]
    assert [gate["_policy_source"] for gate in policy["gates"]] == [
        "org.json",
        "team.json",
        "repository.json",
    ]


def test_policy_composition_rejects_cycles_and_duplicate_gate_ids(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(
        '{"schema_version":1,"extends":["second.json"]}', encoding="utf-8"
    )
    second.write_text(
        '{"schema_version":1,"extends":["first.json"]}', encoding="utf-8"
    )
    with pytest.raises(PolicyError, match="composition cycle"):
        load_policy(first)

    second.write_text(
        '{"schema_version":1,"gates":[{"id":"same","max_count":1}]}', encoding="utf-8"
    )
    first.write_text(
        '{"schema_version":1,"extends":["second.json"],'
        '"gates":[{"id":"same","max_count":0}]}',
        encoding="utf-8",
    )
    with pytest.raises(PolicyError, match=r"duplicate gate id same: second\.json and first\.json"):
        load_policy(first)


def test_policy_composition_loads_a_shared_base_once(tmp_path: Path) -> None:
    (tmp_path / "base.json").write_text(
        '{"schema_version":1,"gates":[{"id":"base","max_count":0}]}', encoding="utf-8"
    )
    for name in ("left", "right"):
        (tmp_path / f"{name}.json").write_text(
            '{"schema_version":1,"extends":["base.json"],"gates":['
            f'{{"id":"{name}","max_count":0}}]}}',
            encoding="utf-8",
        )
    root = tmp_path / "root.json"
    root.write_text(
        '{"schema_version":1,"extends":["left.json","right.json"]}', encoding="utf-8"
    )

    policy, _ = load_policy(root)

    assert [gate["id"] for gate in policy["gates"]] == ["base", "left", "right"]
    assert [source["source"] for source in policy["_sources"]] == [
        "base.json",
        "left.json",
        "right.json",
        "root.json",
    ]


def test_policy_composition_has_a_bounded_include_depth(tmp_path: Path) -> None:
    for index in reversed(range(33)):
        payload = (
            {"schema_version": 1, "gates": [{"id": "deep", "max_count": 0}]}
            if index == 32
            else {"schema_version": 1, "extends": [f"policy-{index + 1}.json"]}
        )
        (tmp_path / f"policy-{index}.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PolicyError, match="exceeds 32 levels"):
        load_policy(tmp_path / "policy-0.json")


@pytest.mark.parametrize("reference", ["/absolute/policy.json", "https://example.test/policy.json"])
def test_policy_composition_rejects_nonlocal_references(tmp_path: Path, reference: str) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps({"schema_version": 1, "extends": [reference]}),
        encoding="utf-8",
    )

    with pytest.raises(PolicyError, match="relative local paths"):
        load_policy(policy)

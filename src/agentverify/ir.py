"""Framework-neutral intermediate representation for agent applications."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Evidence:
    path: str
    line: int
    excerpt: str


@dataclass(frozen=True)
class Component:
    kind: str
    name: str
    evidence: Evidence
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Relationship:
    source_kind: str
    source_name: str
    relation: str
    target_kind: str
    target_name: str
    evidence: Evidence
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    confidence: str
    message: str
    evidence: Evidence
    remediation: str
    fingerprint: str
    result_kind: str = "finding"
    ir_path: tuple[str, ...] = ()
    analysis: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Suppression:
    rule_id: str
    reason: str
    finding: Evidence
    directive: Evidence


@dataclass
class RepositoryIR:
    root: str
    scan_scope: str = "repository"
    path_filters: list[str] = field(default_factory=list)
    files_scanned: int = 0
    config_files_scanned: int = 0
    suppressed_findings: int = 0
    components: list[Component] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    suppressions: list[Suppression] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add_component(self, component: Component) -> None:
        key = (component.kind, component.name, component.evidence.path, component.evidence.line)
        if key not in {
            (item.kind, item.name, item.evidence.path, item.evidence.line)
            for item in self.components
        }:
            self.components.append(component)

    def add_relationship(self, relationship: Relationship) -> None:
        key = (
            relationship.source_kind,
            relationship.source_name,
            relationship.relation,
            relationship.target_kind,
            relationship.target_name,
            relationship.evidence.path,
            relationship.evidence.line,
        )
        if key not in {
            (
                item.source_kind,
                item.source_name,
                item.relation,
                item.target_kind,
                item.target_name,
                item.evidence.path,
                item.evidence.line,
            )
            for item in self.relationships
        }:
            self.relationships.append(relationship)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["root"] = str(Path(self.root).resolve())
        return result

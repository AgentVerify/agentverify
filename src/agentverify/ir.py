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
    symbol_id: str | None = None


@dataclass(frozen=True)
class Relationship:
    source_kind: str
    source_name: str
    relation: str
    target_kind: str
    target_name: str
    evidence: Evidence
    attributes: dict[str, Any] = field(default_factory=dict)
    source_id: str | None = None
    target_id: str | None = None


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
    expires_on: str | None = None
    status: str = "active"


@dataclass
class RepositoryIR:
    root: str
    scan_scope: str = "repository"
    path_filters: list[str] = field(default_factory=list)
    baseline_summary: dict[str, int | None] = field(default_factory=dict)
    policy_summary: dict[str, Any] = field(default_factory=dict)
    files_scanned: int = 0
    config_files_scanned: int = 0
    suppressed_findings: int = 0
    components: list[Component] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    suppressions: list[Suppression] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add_component(self, component: Component) -> None:
        key = (
            component.kind,
            component.name,
            component.evidence.path,
            component.evidence.line,
            component.symbol_id,
        )
        if key not in {
            (item.kind, item.name, item.evidence.path, item.evidence.line, item.symbol_id)
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
            relationship.source_id,
            relationship.target_id,
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
                item.source_id,
                item.target_id,
            )
            for item in self.relationships
        }:
            self.relationships.append(relationship)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["root"] = str(Path(self.root).resolve())
        return result

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RepositoryIR:
        """Rehydrate a RepositoryIR produced by ``to_dict`` or ``render_json``."""

        def evidence(value: dict[str, Any]) -> Evidence:
            return Evidence(
                path=str(value["path"]),
                line=int(value["line"]),
                excerpt=str(value.get("excerpt", "")),
            )

        def optional_string(value: Any) -> str | None:
            return None if value is None else str(value)

        ir = cls(
            root=str(payload["root"]),
            scan_scope=str(payload.get("scan_scope", "repository")),
            path_filters=[str(item) for item in payload.get("path_filters", [])],
            baseline_summary=dict(payload.get("baseline_summary", {})),
            policy_summary=dict(payload.get("policy_summary", {})),
            files_scanned=int(payload.get("files_scanned", 0)),
            config_files_scanned=int(payload.get("config_files_scanned", 0)),
            suppressed_findings=int(payload.get("suppressed_findings", 0)),
            errors=[str(item) for item in payload.get("errors", [])],
        )
        ir.components = [
            Component(
                kind=str(item["kind"]),
                name=str(item["name"]),
                evidence=evidence(item["evidence"]),
                attributes=dict(item.get("attributes", {})),
                symbol_id=optional_string(item.get("symbol_id")),
            )
            for item in payload.get("components", [])
        ]
        ir.relationships = [
            Relationship(
                source_kind=str(item["source_kind"]),
                source_name=str(item["source_name"]),
                relation=str(item["relation"]),
                target_kind=str(item["target_kind"]),
                target_name=str(item["target_name"]),
                evidence=evidence(item["evidence"]),
                attributes=dict(item.get("attributes", {})),
                source_id=optional_string(item.get("source_id")),
                target_id=optional_string(item.get("target_id")),
            )
            for item in payload.get("relationships", [])
        ]
        ir.findings = [
            Finding(
                rule_id=str(item["rule_id"]),
                severity=str(item["severity"]),
                confidence=str(item["confidence"]),
                message=str(item["message"]),
                evidence=evidence(item["evidence"]),
                remediation=str(item["remediation"]),
                fingerprint=str(item["fingerprint"]),
                result_kind=str(item.get("result_kind", "finding")),
                ir_path=tuple(str(value) for value in item.get("ir_path", [])),
                analysis=dict(item.get("analysis", {})),
            )
            for item in payload.get("findings", [])
        ]
        ir.suppressions = [
            Suppression(
                rule_id=str(item["rule_id"]),
                reason=str(item["reason"]),
                finding=evidence(item["finding"]),
                directive=evidence(item["directive"]),
                expires_on=optional_string(item.get("expires_on")),
                status=str(item.get("status", "active")),
            )
            for item in payload.get("suppressions", [])
        ]
        return ir

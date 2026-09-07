from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class QualityMixin:
    """G1 honesty fields shared by core gasto tables."""

    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_inferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_quality: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    evidence_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3), nullable=True)
    data_origin: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_note: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)


class AdminLevel(str, enum.Enum):
    nacional = "nacional"
    departamental = "departamental"
    municipal = "municipal"
    empresarial = "empresarial"


class Entity(QualityMixin, Base):
    __tablename__ = "entity"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    level: Mapped[AdminLevel] = mapped_column(
        Enum(AdminLevel, values_callable=lambda x: [e.value for e in x], native_enum=False),
        nullable=False,
    )
    aliases: Mapped[list[Any]] = mapped_column(JSON, default=list)
    nit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    department: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, default="seed")
    ingestion_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ingestion_run.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    entity_master_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)

    contracts: Mapped[list["Contract"]] = relationship(back_populates="entity")
    budget_lines: Mapped[list["BudgetLine"]] = relationship(back_populates="entity")


class Supplier(QualityMixin, Base):
    __tablename__ = "supplier"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    nit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    aliases: Mapped[list[Any]] = mapped_column(JSON, default=list)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, default="seed")
    ingestion_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ingestion_run.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    supplier_master_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)

    contracts: Mapped[list["Contract"]] = relationship(back_populates="supplier")


class BudgetLine(QualityMixin, Base):
    __tablename__ = "budget_line"
    __table_args__ = (
        Index("ix_budget_line_current", "entity_id", "year", "is_current"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    program_project: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    budget_item: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    initial_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    modified_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    current_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    executed_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    # G6: explicit phase amounts (do not sum as independent totals)
    budget_initial: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    budget_modification: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    budget_current: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    commitment: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    accrual: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    payment: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    budget_phase: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="BOB")
    as_of: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ingestion_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ingestion_run.id"), nullable=True
    )
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    entity: Mapped["Entity"] = relationship(back_populates="budget_lines")


class Contract(QualityMixin, Base):
    __tablename__ = "contract"
    __table_args__ = (
        Index(
            "uq_contract_cuce_source_current",
            "cuce",
            "source_id",
            unique=True,
            postgresql_where=text("is_current IS TRUE AND cuce IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cuce: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"), nullable=False)
    supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("supplier.id"), nullable=True)
    object_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    modality: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="BOB")
    contract_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    documents: Mapped[list[Any]] = mapped_column(JSON, default=list)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ingestion_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ingestion_run.id"), nullable=True
    )
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # G3 completeness
    completeness_level: Mapped[int] = mapped_column(default=0, nullable=False)
    has_reference_price: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_award: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_awarded_amount: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_supplier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_nit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_contract_doc: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_modifications: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reference_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)

    entity: Mapped["Entity"] = relationship(back_populates="contracts")
    supplier: Mapped[Optional["Supplier"]] = relationship(back_populates="contracts")


class AuditReport(QualityMixin, Base):
    __tablename__ = "audit_report"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entity.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    year: Mapped[Optional[int]] = mapped_column(nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    findings_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, default="cge")
    ingestion_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ingestion_run.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    mime: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    minio_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ingestion_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ingestion_run.id"), nullable=True
    )
    raw_artifact_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("raw_artifact.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Discrepancy(QualityMixin, Base):
    __tablename__ = "discrepancy"

    id: Mapped[int] = mapped_column(primary_key=True)
    concept: Mapped[str] = mapped_column(String(256), nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entity.id"), nullable=True)
    amount_a: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    amount_b: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    source_a: Mapped[str] = mapped_column(String(64), nullable=False)
    source_b: Mapped[str] = mapped_column(String(64), nullable=False)
    ref_a: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    ref_b: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Alert(QualityMixin, Base):
    __tablename__ = "alert"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entity.id"), nullable=True)
    contract_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contract.id"), nullable=True)
    supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("supplier.id"), nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, default="rules")
    ingestion_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ingestion_run.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    legitimate_causes: Mapped[Optional[list[Any]]] = mapped_column(JSON, nullable=True)


class IngestionRun(Base):
    __tablename__ = "ingestion_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    records_in: Mapped[int] = mapped_column(default=0)
    records_out: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


# --- G2 Evidence / claims ---


class SourceRegistry(Base):
    __tablename__ = "source_registry"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False, default="portal")
    base_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RawArtifact(Base):
    __tablename__ = "raw_artifact"
    __table_args__ = (Index("ix_raw_artifact_sha256", "sha256"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    url_original: Mapped[str] = mapped_column(String(2048), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mime: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    http_status: Mapped[Optional[int]] = mapped_column(nullable=True)
    etag: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    last_modified: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(nullable=True)
    crawler_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    minio_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    ingestion_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ingestion_run.id"), nullable=True
    )
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class DocumentPage(Base):
    __tablename__ = "document_page"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(nullable=False)
    text_extracted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExtractionRun(Base):
    __tablename__ = "extraction_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    method: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    raw_artifact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("raw_artifact.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Claim(Base):
    __tablename__ = "claim"
    __table_args__ = (Index("ix_claim_entity", "entity_type", "entity_id", "field"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    value_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_num: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[int] = mapped_column(nullable=False)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3), nullable=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("extraction_run.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClaimEvidence(Base):
    __tablename__ = "claim_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"), nullable=False, index=True)
    raw_artifact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("raw_artifact.id"), nullable=True)
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)
    document_page_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document_page.id"), nullable=True)
    quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page: Mapped[Optional[int]] = mapped_column(nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ClaimConflict(Base):
    __tablename__ = "claim_conflict"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[int] = mapped_column(nullable=False)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    claim_ids: Mapped[list[Any]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReconciliationResult(Base):
    __tablename__ = "reconciliation_result"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_conflict_id: Mapped[int] = mapped_column(ForeignKey("claim_conflict.id"), nullable=False)
    canonical_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conflict_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unresolved")
    resolution_method: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- G4 Supplier master ---


class SupplierMaster(Base):
    __tablename__ = "supplier_master"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    nit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, unique=True, index=True)
    legal_form: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    municipality: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    first_seen: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_seen: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SupplierAlias(Base):
    __tablename__ = "supplier_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_master_id: Mapped[int] = mapped_column(ForeignKey("supplier_master.id"), nullable=False)
    alias: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class SupplierIdentifier(Base):
    __tablename__ = "supplier_identifier"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_master_id: Mapped[int] = mapped_column(ForeignKey("supplier_master.id"), nullable=False)
    id_type: Mapped[str] = mapped_column(String(32), nullable=False, default="nit")
    id_value: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class SupplierRelation(Base):
    __tablename__ = "supplier_relation"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_master_id: Mapped[int] = mapped_column(ForeignKey("supplier_master.id"), nullable=False)
    to_master_id: Mapped[int] = mapped_column(ForeignKey("supplier_master.id"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False, default="related")


class SupplierSource(Base):
    __tablename__ = "supplier_source"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_master_id: Mapped[int] = mapped_column(ForeignKey("supplier_master.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    external_ref: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)


class MergeCandidate(Base):
    """Pending fuzzy merge suggestion — never auto-applied."""

    __tablename__ = "merge_candidate"
    __table_args__ = (
        Index("ix_merge_candidate_status", "status"),
        Index("ix_merge_candidate_left", "left_type", "left_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    left_type: Mapped[str] = mapped_column(String(64), nullable=False)
    left_id: Mapped[int] = mapped_column(nullable=False)
    right_id: Mapped[int] = mapped_column(nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- G5 Public entity master ---


class PublicEntityMaster(Base):
    __tablename__ = "public_entity_master"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    level: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    institution_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    municipality: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("public_entity_master.id"), nullable=True)
    predecessor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("public_entity_master.id"), nullable=True
    )
    successor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("public_entity_master.id"), nullable=True
    )
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EntityAlias(Base):
    __tablename__ = "entity_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_master_id: Mapped[int] = mapped_column(ForeignKey("public_entity_master.id"), nullable=False)
    alias: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


# --- G7 Audit findings ---


class AuditFinding(Base):
    __tablename__ = "audit_finding"

    id: Mapped[int] = mapped_column(primary_key=True)
    audit_report_id: Mapped[int] = mapped_column(ForeignKey("audit_report.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entity.id"), nullable=True)
    contract_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contract.id"), nullable=True)
    supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("supplier.id"), nullable=True)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditRecommendation(Base):
    __tablename__ = "audit_recommendation"

    id: Mapped[int] = mapped_column(primary_key=True)
    audit_finding_id: Mapped[int] = mapped_column(ForeignKey("audit_finding.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)


class AuditAmount(Base):
    __tablename__ = "audit_amount"

    id: Mapped[int] = mapped_column(primary_key=True)
    audit_finding_id: Mapped[int] = mapped_column(ForeignKey("audit_finding.id"), nullable=False)
    amount_type: Mapped[str] = mapped_column(String(64), nullable=False, default="observed")
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="BOB")


# --- AURA Incendios (fire ledger) ---


class TerritoryLevel(str, enum.Enum):
    pais = "pais"
    departamento = "departamento"
    municipio = "municipio"


class FireAttribution(str, enum.Enum):
    directo = "directo"
    probable = "probable"
    parcial = "parcial"
    indirecto = "indirecto"
    no_relacionado = "no_relacionado"


class FireCycle(str, enum.Enum):
    prevencion = "prevencion"
    preparacion = "preparacion"
    respuesta = "respuesta"
    recuperacion = "recuperacion"


class LedgerBucket(str, enum.Enum):
    verificable = "verificable"
    parcial = "parcial"
    probable = "probable"
    indirecto = "indirecto"
    no_relacionado = "no_relacionado"
    sintetico = "sintetico"


class LinkStrength(str, enum.Enum):
    CONFIRMADO = "CONFIRMADO"
    FUERTEMENTE_VINCULADO = "FUERTEMENTE_VINCULADO"
    PROBABLE = "PROBABLE"
    POSIBLE = "POSIBLE"
    NO_DETERMINABLE = "NO_DETERMINABLE"


class Territory(Base):
    __tablename__ = "territory"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    level: Mapped[TerritoryLevel] = mapped_column(
        Enum(TerritoryLevel, values_callable=lambda x: [e.value for e in x], native_enum=False),
        nullable=False,
    )
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("territory.id"), nullable=True)
    ine_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parent: Mapped[Optional["Territory"]] = relationship(remote_side="Territory.id")


class FireSeason(Base):
    __tablename__ = "fire_season"
    __table_args__ = (UniqueConstraint("year", name="uq_fire_season_year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(nullable=False, index=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    quality_grade: Mapped[str] = mapped_column(String(8), default="D")  # A–E
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FireEvent(Base):
    __tablename__ = "fire_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, unique=True, index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("fire_season.id"), nullable=False)
    territory_id: Mapped[Optional[int]] = mapped_column(ForeignKey("territory.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3), nullable=True)
    hectares_reported: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    sources: Mapped[list[Any]] = mapped_column(JSON, default=list)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    season: Mapped["FireSeason"] = relationship()
    territory: Mapped[Optional["Territory"]] = relationship()


class FireClassificationRun(Base):
    __tablename__ = "fire_classification_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    method: Mapped[str] = mapped_column(String(64), default="exact_keyword")
    records_in: Mapped[int] = mapped_column(default=0)
    records_out: Mapped[int] = mapped_column(default=0)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class FireExpenditure(Base):
    """Expediente del ledger de gasto en incendios (FIRE-BO-YYYY-NNNNNN)."""

    __tablename__ = "fire_expenditure"
    __table_args__ = (
        UniqueConstraint("code", name="uq_fire_expenditure_code"),
        Index("ix_fire_expenditure_year_attr", "year", "attribution"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    year: Mapped[int] = mapped_column(nullable=False, index=True)
    season_id: Mapped[Optional[int]] = mapped_column(ForeignKey("fire_season.id"), nullable=True)
    fire_event_id: Mapped[Optional[int]] = mapped_column(ForeignKey("fire_event.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    object_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attribution: Mapped[FireAttribution] = mapped_column(
        Enum(FireAttribution, values_callable=lambda x: [e.value for e in x], native_enum=False),
        nullable=False,
    )
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, default=Decimal("0.5"))
    classification_method: Mapped[str] = mapped_column(String(64), nullable=False, default="exact_keyword")
    cycle: Mapped[FireCycle] = mapped_column(
        Enum(FireCycle, values_callable=lambda x: [e.value for e in x], native_enum=False),
        nullable=False,
    )
    paying_entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entity.id"), nullable=True)
    beneficiary_territory_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("territory.id"), nullable=True
    )
    supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("supplier.id"), nullable=True)
    contract_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contract.id"), nullable=True)
    budget_line_id: Mapped[Optional[int]] = mapped_column(ForeignKey("budget_line.id"), nullable=True)
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)
    classification_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("fire_classification_run.id"), nullable=True
    )
    amount_contract: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    amount_attributed: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    amount_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    amount_attributed_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    amount_attributed_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    amount_attributed_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    allocation_method: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    allocation_confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, default=Decimal("0")
    )
    ledger_bucket: Mapped[str] = mapped_column(String(32), nullable=False, default="probable", index=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    recovery_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    link_strength: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="BOB")
    quality_grade: Mapped[str] = mapped_column(String(8), default="D")
    cuce: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, default="seed_fire")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    paying_entity: Mapped[Optional["Entity"]] = relationship()
    beneficiary_territory: Mapped[Optional["Territory"]] = relationship()
    supplier: Mapped[Optional["Supplier"]] = relationship()
    contract: Mapped[Optional["Contract"]] = relationship()


class EmergencyDeclaration(Base):
    __tablename__ = "emergency_declaration"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    decree_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, default="incendio_forestal")
    entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entity.id"), nullable=True)
    territory_id: Mapped[Optional[int]] = mapped_column(ForeignKey("territory.id"), nullable=True)
    promulgated_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    published_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    authority: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, default="gaceta")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OperationalOutput(Base):
    __tablename__ = "operational_output"
    __table_args__ = (Index("ix_operational_output_year", "year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(nullable=False)
    season_id: Mapped[Optional[int]] = mapped_column(ForeignKey("fire_season.id"), nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entity.id"), nullable=True)
    territory_id: Mapped[Optional[int]] = mapped_column(ForeignKey("territory.id"), nullable=True)
    metric_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_label: Mapped[str] = mapped_column(String(256), nullable=False)
    value_numeric: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    value_text: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)
    evidence_page: Mapped[Optional[int]] = mapped_column(nullable=True)
    evidence_quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, default="mindef")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DonationAid(Base):
    __tablename__ = "donation_aid"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(nullable=False, index=True)
    donor_name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="BOB")
    in_kind: Mapped[bool] = mapped_column(Boolean, default=False)
    territory_id: Mapped[Optional[int]] = mapped_column(ForeignKey("territory.id"), nullable=True)
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, default="seed_fire")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ActiveFireDetection(Base):
    """NASA FIRMS / satellite active fire points (results layer, not spending)."""

    __tablename__ = "active_fire_detection"
    __table_args__ = (Index("ix_active_fire_year_dept", "year", "department"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(nullable=False, index=True)
    acq_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    brightness: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    frp: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    satellite: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    municipality: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    territory_id: Mapped[Optional[int]] = mapped_column(ForeignKey("territory.id"), nullable=True)
    cluster_id: Mapped[Optional[int]] = mapped_column(ForeignKey("fire_cluster.id"), nullable=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, default="firms")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FireCluster(Base):
    __tablename__ = "fire_cluster"
    __table_args__ = (Index("ix_fire_cluster_year", "year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(nullable=False)
    fire_event_id: Mapped[Optional[int]] = mapped_column(ForeignKey("fire_event.id"), nullable=True)
    territory_id: Mapped[Optional[int]] = mapped_column(ForeignKey("territory.id"), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    centroid_lat: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    centroid_lon: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    detection_count: Mapped[int] = mapped_column(default=0)
    max_frp: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, default="firms")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BurnedArea(Base):
    __tablename__ = "burned_area"
    __table_args__ = (Index("ix_burned_area_year", "year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(nullable=False)
    fire_event_id: Mapped[Optional[int]] = mapped_column(ForeignKey("fire_event.id"), nullable=True)
    territory_id: Mapped[Optional[int]] = mapped_column(ForeignKey("territory.id"), nullable=True)
    hectares: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(64), nullable=False, default="reported")
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FireCapabilityAsset(Base):
    __tablename__ = "fire_capability_asset"
    __table_args__ = (Index("ix_fire_capability_year_type", "year", "asset_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    ownership: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entity.id"), nullable=True)
    territory_id: Mapped[Optional[int]] = mapped_column(ForeignKey("territory.id"), nullable=True)
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    acquired_via: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    fire_expenditure_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("fire_expenditure.id"), nullable=True
    )
    is_preventive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, default="seed_fire")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FireLink(Base):
    __tablename__ = "fire_link"
    __table_args__ = (
        Index("ix_fire_link_from", "from_type", "from_id"),
        Index("ix_fire_link_to", "to_type", "to_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    from_type: Mapped[str] = mapped_column(String(64), nullable=False)
    from_id: Mapped[int] = mapped_column(nullable=False)
    to_type: Mapped[str] = mapped_column(String(64), nullable=False)
    to_id: Mapped[int] = mapped_column(nullable=False)
    strength: Mapped[str] = mapped_column(String(32), nullable=False, default="POSIBLE")
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

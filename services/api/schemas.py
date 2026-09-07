"""Pydantic response models for the public read API."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthOut(BaseModel):
    status: str
    version: str = "0.8.0"
    proxy: dict[str, Any] = Field(default_factory=dict)


class CategoryOut(BaseModel):
    id: str
    label: str
    contracts: int = 0


class YearAggOut(BaseModel):
    year: int
    contracts: int
    contract_amount: Decimal
    budget_lines: int
    budget_current_total: Decimal
    budget_executed_total: Decimal


class EntityOut(ORMModel):
    id: int
    name: str
    canonical_name: str
    level: str
    department: Optional[str] = None
    source_id: str
    ingestion_run_id: Optional[int] = None
    entity_master_id: Optional[int] = None
    is_synthetic: bool = False
    source_quality: Optional[str] = None


class SupplierOut(ORMModel):
    id: int
    name: str
    canonical_name: str
    nit: Optional[str] = None
    source_id: str
    ingestion_run_id: Optional[int] = None
    supplier_master_id: Optional[int] = None
    is_synthetic: bool = False
    source_quality: Optional[str] = None


class ContractOut(ORMModel):
    id: int
    cuce: Optional[str] = None
    entity_id: int
    supplier_id: Optional[int] = None
    object_description: Optional[str] = None
    modality: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str
    contract_date: Optional[Any] = None
    status: Optional[str] = None
    documents: list[Any] = Field(default_factory=list)
    source_id: str
    ingestion_run_id: Optional[int] = None
    is_current: bool
    is_synthetic: bool = False
    is_official: bool = False
    source_quality: Optional[str] = None
    evidence_status: Optional[str] = None
    confidence_score: Optional[Decimal] = None
    data_origin: Optional[str] = None
    source_note: Optional[str] = None
    completeness_level: int = 0
    has_reference_price: bool = False
    has_award: bool = False
    has_awarded_amount: bool = False
    has_supplier: bool = False
    has_nit: bool = False
    has_contract_doc: bool = False
    reference_price: Optional[Decimal] = None


class BudgetOut(ORMModel):
    id: int
    entity_id: int
    year: int
    program_project: Optional[str] = None
    budget_item: Optional[str] = None
    category: Optional[str] = None
    initial_amount: Optional[Decimal] = None
    modified_amount: Optional[Decimal] = None
    current_amount: Optional[Decimal] = None
    executed_amount: Optional[Decimal] = None
    budget_initial: Optional[Decimal] = None
    budget_modification: Optional[Decimal] = None
    budget_current: Optional[Decimal] = None
    commitment: Optional[Decimal] = None
    accrual: Optional[Decimal] = None
    payment: Optional[Decimal] = None
    budget_phase: Optional[str] = None
    currency: str
    source_id: str
    ingestion_run_id: Optional[int] = None
    is_current: bool
    is_synthetic: bool = False
    source_quality: Optional[str] = None


class AlertOut(ORMModel):
    id: int
    rule_id: str
    severity: str
    title: str
    explanation: str
    entity_id: Optional[int] = None
    contract_id: Optional[int] = None
    supplier_id: Optional[int] = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    source_id: str
    is_synthetic: bool = False
    legitimate_causes: Optional[list[Any]] = None


class AuditOut(ORMModel):
    id: int
    entity_id: Optional[int] = None
    title: str
    year: Optional[int] = None
    url: str
    findings_summary: Optional[str] = None
    source_id: str


class DiscrepancyOut(ORMModel):
    id: int
    concept: str
    entity_id: Optional[int] = None
    amount_a: Optional[Decimal] = None
    amount_b: Optional[Decimal] = None
    source_a: str
    source_b: str
    ref_a: Optional[str] = None
    ref_b: Optional[str] = None
    delta_pct: Optional[float] = None


class SearchHit(BaseModel):
    type: str
    id: int
    title: str
    subtitle: Optional[str] = None
    href: str


class SearchOut(BaseModel):
    q: str
    hits: list[SearchHit] = Field(default_factory=list)


class YearCompareOut(BaseModel):
    year_a: int
    year_b: int
    contracts_a: int
    contracts_b: int
    contracts_delta_pct: Optional[float] = None
    amount_a: Decimal
    amount_b: Decimal
    amount_delta_pct: Optional[float] = None
    budget_current_a: Decimal
    budget_current_b: Decimal
    budget_delta_pct: Optional[float] = None


class ActivityItem(BaseModel):
    kind: str
    title: str
    at: Optional[str] = None
    href: Optional[str] = None
    meta: dict[str, Any] = Field(default_factory=dict)


class DocumentOut(ORMModel):
    id: int
    url: str
    sha256: Optional[str] = None
    mime: Optional[str] = None
    minio_key: Optional[str] = None
    source_id: str
    ingestion_run_id: Optional[int] = None


class IngestionRunOut(ORMModel):
    id: int
    source_id: str
    started_at: Any
    finished_at: Optional[Any] = None
    status: str
    records_in: int
    records_out: int
    error_message: Optional[str] = None
    meta: dict[str, Any] = Field(default_factory=dict)


class SourceOut(BaseModel):
    source_id: str
    last_status: Optional[str] = None
    last_finished_at: Optional[Any] = None
    records_out: Optional[int] = None
    license_note: str = "Ver docs/sources/"


class StatsOut(BaseModel):
    entities: int
    suppliers: int
    contracts: int
    budgets: int
    alerts: int
    audits: int
    discrepancies: int
    documents: int
    total_contract_amount: Decimal
    alerts_by_severity: dict[str, int]


class PageMeta(BaseModel):
    total: int
    limit: int
    offset: int


class CrossSourceSummary(BaseModel):
    contracts_with_cuce: int
    cuces_multi_source: int
    discrepancies_total: int
    discrepancies_cuce: int
    discrepancies_budget_vs_contracts: int
    sources_in_contracts: list[str] = Field(default_factory=list)


class ClaimOut(ORMModel):
    id: int
    field: str
    value_text: Optional[str] = None
    value_num: Optional[Decimal] = None
    entity_type: str
    entity_id: int
    confidence: Optional[Decimal] = None
    source_id: str


class ClaimEvidenceOut(ORMModel):
    id: int
    claim_id: int
    quote: Optional[str] = None
    page: Optional[int] = None
    url: Optional[str] = None
    sha256: Optional[str] = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class CoverageFlagOut(BaseModel):
    flag: str
    count: int
    pct: float


class SicoesCoverageOut(BaseModel):
    sample_size: int
    flags: list[CoverageFlagOut] = Field(default_factory=list)
    gate_pass: bool
    thresholds: dict[str, float] = Field(default_factory=dict)
    known_amount_universe: int = 0
    known_amount_flags: list[CoverageFlagOut] = Field(default_factory=list)
    catalog_note: str = (
        "Muestra reciente SICOES = catálogo de convocatorias; montos vía enrich/OCDS."
    )


class SupplierMasterOut(ORMModel):
    id: int
    canonical_name: str
    nit: Optional[str] = None
    legal_form: Optional[str] = None
    department: Optional[str] = None
    first_seen: Optional[Any] = None
    last_seen: Optional[Any] = None


class EntityMasterOut(ORMModel):
    id: int
    canonical_name: str
    level: Optional[str] = None
    department: Optional[str] = None
    institution_type: Optional[str] = None


class AuditFindingOut(ORMModel):
    id: int
    audit_report_id: int
    title: str
    description: Optional[str] = None
    severity: Optional[str] = None
    entity_id: Optional[int] = None
    contract_id: Optional[int] = None
    supplier_id: Optional[int] = None
    amount: Optional[Decimal] = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class ClaimConflictOut(ORMModel):
    id: int
    entity_type: str
    entity_id: int
    field: str
    claim_ids: list[Any] = Field(default_factory=list)
    status: str


class MergeCandidateOut(ORMModel):
    id: int
    left_type: str
    left_id: int
    right_id: int
    score: Decimal
    status: str


class ProductGateOut(BaseModel):
    version: str = "0.8.0"
    checks: dict[str, bool] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    pass_: bool = Field(alias="pass", default=False)

    model_config = ConfigDict(populate_by_name=True)

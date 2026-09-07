"""Helpers to persist atomic claims + evidence (Plan G2/G8)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from schema.models import Claim, ClaimConflict, ClaimEvidence, RawArtifact, ReconciliationResult


def ensure_raw_artifact(
    session: Session,
    *,
    url: str,
    sha256: str,
    source_id: str,
    minio_key: str | None = None,
    mime: str | None = None,
    http_status: int | None = None,
    size_bytes: int | None = None,
    ingestion_run_id: int | None = None,
    meta: dict | None = None,
) -> RawArtifact:
    """Never overwrite: reuse same sha256+url, else insert new version."""
    existing = session.scalars(
        select(RawArtifact).where(
            RawArtifact.sha256 == sha256,
            RawArtifact.url_original == url,
        )
    ).first()
    if existing:
        return existing
    art = RawArtifact(
        url_original=url,
        sha256=sha256,
        mime=mime,
        http_status=http_status,
        size_bytes=size_bytes,
        minio_key=minio_key,
        source_id=source_id,
        ingestion_run_id=ingestion_run_id,
        meta=meta or {},
    )
    session.add(art)
    session.flush()
    return art


def add_claim(
    session: Session,
    *,
    field: str,
    entity_type: str,
    entity_id: int,
    source_id: str,
    value_text: str | None = None,
    value_num: Decimal | None = None,
    confidence: float | None = None,
    evidence: dict[str, Any] | None = None,
    raw_artifact_id: int | None = None,
    detect_conflict: bool = True,
) -> Claim:
    claim = Claim(
        field=field,
        value_text=value_text,
        value_num=value_num,
        entity_type=entity_type,
        entity_id=entity_id,
        confidence=Decimal(str(confidence)) if confidence is not None else None,
        source_id=source_id,
    )
    session.add(claim)
    session.flush()

    ev = evidence or {}
    session.add(
        ClaimEvidence(
            claim_id=claim.id,
            raw_artifact_id=raw_artifact_id,
            quote=ev.get("quote"),
            page=ev.get("page"),
            url=ev.get("url"),
            sha256=ev.get("sha256"),
            evidence=ev,
        )
    )

    if detect_conflict:
        siblings = list(
            session.scalars(
                select(Claim).where(
                    Claim.entity_type == entity_type,
                    Claim.entity_id == entity_id,
                    Claim.field == field,
                    Claim.id != claim.id,
                )
            ).all()
        )
        conflicting = []
        for s in siblings:
            if value_num is not None and s.value_num is not None and s.value_num != value_num:
                conflicting.append(s.id)
            elif value_text and s.value_text and s.value_text.strip().lower() != value_text.strip().lower():
                conflicting.append(s.id)
        if conflicting:
            ids = conflicting + [claim.id]
            conflict = ClaimConflict(
                entity_type=entity_type,
                entity_id=entity_id,
                field=field,
                claim_ids=ids,
                status="open",
            )
            session.add(conflict)
            session.flush()
            session.add(
                ReconciliationResult(
                    claim_conflict_id=conflict.id,
                    canonical_value=None,
                    conflict_status="unresolved",
                    resolution_method=None,
                    notes="Auto-detected; losing claim retained",
                )
            )
    return claim


def claims_for_contract(session: Session, contract_id: int) -> list[Claim]:
    return list(
        session.scalars(
            select(Claim)
            .where(Claim.entity_type == "contract", Claim.entity_id == contract_id)
            .order_by(Claim.created_at.desc())
        ).all()
    )

"""B4 — backfill raw_artifact for prioritized contracts with docs/URLs."""
from __future__ import annotations

import hashlib
import os
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from common.claims import ensure_raw_artifact
from schema.db import make_engine
from schema.models import Contract
from worker.enrich_sicoes import prioritize_cuces

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
)


def _doc_url_and_sha(doc: Any, contract: Contract) -> tuple[str | None, str | None]:
    if isinstance(doc, str):
        url = doc
        sha = hashlib.sha256(url.encode()).hexdigest()
        return url, sha
    if isinstance(doc, dict):
        url = doc.get("url") or doc.get("source_url")
        if not url and doc.get("minio_key"):
            url = f"minio://{doc['minio_key']}"
        sha = doc.get("sha256") or doc.get("raw_sha256")
        if url and not sha:
            sha = hashlib.sha256(url.encode()).hexdigest()
        return url, sha
    return None, None


def run_backfill(limit: int = 50) -> dict[str, Any]:
    """Ensure raw artifacts for prioritized contracts that have source_url or documents."""
    engine = make_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    created = 0
    skipped = 0
    with SessionLocal() as session:
        cuces = prioritize_cuces(session, limit=max(limit * 3, limit))
        contracts = list(
            session.scalars(
                select(Contract).where(
                    Contract.is_current.is_(True),
                    Contract.cuce.in_(cuces) if cuces else False,
                )
            ).all()
        )
        # Prefer contracts that already carry documents / URLs
        with_docs = [
            c
            for c in contracts
            if (c.documents and len(c.documents) > 0)
            or (c.source_note and "http" in (c.source_note or "").lower())
        ]
        # Also scan staging-like fields in documents list
        targets = (with_docs or contracts)[:limit]
        for contract in targets:
            docs = list(contract.documents or [])
            if not docs:
                # Synthetic placeholder from CUCE listing URL
                url = f"https://www.sicoes.gob.bo/cuce/{contract.cuce or contract.id}"
                sha = hashlib.sha256(url.encode()).hexdigest()
                ensure_raw_artifact(
                    session,
                    url=url,
                    sha256=sha,
                    source_id=contract.source_id or "sicoes",
                    mime="text/html",
                    meta={"cuce": contract.cuce, "backfill": True},
                    ingestion_run_id=contract.ingestion_run_id,
                )
                created += 1
                continue
            linked = False
            for doc in docs:
                url, sha = _doc_url_and_sha(doc, contract)
                if not url or not sha:
                    continue
                ensure_raw_artifact(
                    session,
                    url=url,
                    sha256=sha,
                    source_id=contract.source_id or "sicoes",
                    minio_key=doc.get("minio_key") if isinstance(doc, dict) else None,
                    meta={"cuce": contract.cuce, "backfill": True},
                    ingestion_run_id=contract.ingestion_run_id,
                )
                created += 1
                linked = True
            if not linked:
                skipped += 1
        session.commit()
    return {"ok": True, "created": created, "skipped": skipped, "limit": limit}

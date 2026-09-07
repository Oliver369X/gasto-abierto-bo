"""Documents list and download."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import RATE, get_db, limiter
from api.schemas import DocumentOut
from common.storage import get_store
from schema.models import Document

router = APIRouter()


@router.get("/v1/documents", response_model=list[DocumentOut], tags=["documents"])
@limiter.limit(f"{RATE}/minute")
def list_documents(
    request: Request,
    db: Session = Depends(get_db),
    source_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Document]:
    stmt = select(Document).order_by(Document.id.desc())
    if source_id:
        stmt = stmt.where(Document.source_id == source_id)
    return list(db.scalars(stmt.offset(offset).limit(limit)).all())


@router.get("/v1/documents/{document_id}/download", tags=["documents"])
@limiter.limit(f"{RATE}/minute")
def download_document(request: Request, document_id: int, db: Session = Depends(get_db)):
    row = db.get(Document, document_id)
    if not row:
        raise HTTPException(404, "Document not found")
    if not row.minio_key:
        if row.url and row.url.startswith("http"):
            return RedirectResponse(row.url)
        raise HTTPException(404, "No raw object stored for this document")
    store = get_store()
    url = store.presigned_get(row.minio_key)
    if url:
        return RedirectResponse(url)
    data, ctype = store.get_bytes(row.minio_key)
    if data is None:
        raise HTTPException(503, "Object store unavailable")
    return StreamingResponse(
        iter([data]),
        media_type=ctype or row.mime or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="doc-{document_id}"'},
    )

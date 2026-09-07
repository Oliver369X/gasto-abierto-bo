from __future__ import annotations

import logging
import mimetypes
from datetime import datetime, timezone
from urllib.parse import urlparse

from common.storage import get_store
from schema.models import Document
from sqlalchemy.orm import Session
from worker.adapters.base import Cursor, StagingRecord
from worker.adapters.registry import get_adapter
from worker.alerts import run_alert_rules
from worker.persist import finish_run, persist_staging, start_run

log = logging.getLogger(__name__)


def guess_content_type(uri: str, raw: bytes) -> str:
    path = urlparse(uri).path
    guessed, _ = mimetypes.guess_type(path)
    if guessed:
        return guessed
    if raw[:1] in (b"{", b"["):
        return "application/json"
    if raw.lstrip()[:1] == b"<":
        return "text/html"
    return "application/octet-stream"


def _run_status(item_count: int, item_errors: list[dict], records_out: int) -> tuple[str, str | None]:
    """ok / partial / error — never claim ok if anything failed."""
    if not item_count and not records_out:
        return "error", "no items discovered and no records persisted"
    if item_errors and records_out == 0 and len(item_errors) >= max(1, item_count):
        msg = f"{len(item_errors)}/{item_count or len(item_errors)} items failed"
        return "error", msg
    if item_errors:
        return "partial", f"{len(item_errors)} item(s) failed"
    return "ok", None


def run_ingest(
    session: Session,
    source_id: str,
    *,
    fixture_path: str | None = None,
    max_pages: int | None = None,
    live: bool = False,
    skip_alerts: bool = False,
    skip_storage: bool = False,
) -> dict:
    adapter = get_adapter(source_id)
    payload: dict = {}
    if fixture_path:
        payload["fixture_path"] = fixture_path
    if max_pages is not None:
        payload["max_pages"] = max_pages
    if live:
        payload["live"] = True

    store = get_store()
    run = start_run(
        session,
        source_id,
        meta={"fixture": fixture_path, "live": live, "skip_alerts": skip_alerts},
    )
    items = adapter.discover(Cursor(payload=payload))
    all_records: list[StagingRecord] = []
    docs = 0
    skipped = 0
    item_errors: list[dict] = []

    for idx, item in enumerate(items):
        try:
            raw = adapter.fetch(item)
            ctype = guess_content_type(item.uri, raw)
            key = None
            sha = None
            if not skip_storage:
                key = store.put_bytes(
                    source_id=source_id,
                    key_suffix=f"run-{run.id}/item-{idx}",
                    data=raw,
                    content_type=ctype,
                )
                sha = store.sha256(raw)
                session.add(
                    Document(
                        url=item.uri,
                        sha256=sha,
                        mime=ctype,
                        minio_key=key,
                        source_id=source_id,
                        ingestion_run_id=run.id,
                    )
                )
                docs += 1
            else:
                import hashlib

                sha = hashlib.sha256(raw).hexdigest()
            records = adapter.parse(raw)
            before = len(records)
            cleaned: list[StagingRecord] = []
            for rec in records:
                if rec.record_type == "contract":
                    cuce = (rec.data.get("cuce") or "").strip()
                    entity = (rec.data.get("entity_name") or "").strip()
                    amount = rec.data.get("amount")
                    if not entity and not cuce:
                        skipped += 1
                        continue
                    if amount is None and not cuce:
                        skipped += 1
                        continue
                rec.data.setdefault("source_id", source_id)
                if key:
                    rec.data.setdefault("minio_key", key)
                    rec.data.setdefault("raw_sha256", sha)
                cleaned.append(rec)
            if before and not cleaned:
                log.warning("item %s: all %s records skipped", item.uri, before)
            all_records.extend(cleaned)
        except Exception as exc:  # noqa: BLE001 — soft-fail per item
            log.exception("item %s failed: %s", getattr(item, "uri", idx), exc)
            item_errors.append(
                {
                    "index": idx,
                    "uri": getattr(item, "uri", None),
                    "error": str(exc)[:500],
                }
            )
            continue

    out = persist_staging(session, all_records, source_id=source_id, run=run)
    alerts: list = []
    if not skip_alerts:
        alerts = run_alert_rules(session, run_id=run.id)
    status, err = _run_status(len(items), item_errors, out)
    finish_run(
        session,
        run,
        status=status,
        records_in=len(items),
        records_out=out,
        error=err,
    )
    run.meta = {
        **(run.meta or {}),
        "documents": docs,
        "alerts": len(alerts),
        "skipped_rows": skipped,
        "item_errors": item_errors[:50],
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    session.flush()
    return {
        "source_id": source_id,
        "run_id": run.id,
        "status": status,
        "records": out,
        "documents": docs,
        "alerts": len(alerts),
        "skipped_rows": skipped,
        "item_errors": len(item_errors),
        "minio_enabled": store.enabled and not skip_storage,
    }

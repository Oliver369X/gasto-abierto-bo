"""SICOES CUCE enrichment worker (Plan G3) — requires PROXY_URL for live fetch."""
from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from common.claims import add_claim, ensure_raw_artifact
from common.data_quality import classify_origin
from common.money import parse_money
from schema.models import Contract, Supplier

logger = logging.getLogger(__name__)

RATE_SECONDS = float(os.getenv("SICOES_ENRICH_RPS", "1.0"))
PROXY_URL = os.getenv("PROXY_URL", "").strip()


def compute_completeness(contract: Contract, supplier: Supplier | None = None) -> dict[str, Any]:
    has_ref = bool(contract.reference_price and contract.reference_price > 0)
    has_amt = bool(contract.amount and contract.amount > 0)
    has_sup = bool(contract.supplier_id)
    has_nit = bool(supplier and supplier.nit)
    has_doc = bool(contract.documents)
    has_award = has_amt or has_sup
    level = sum(
        [
            1 if has_ref else 0,
            1 if has_award else 0,
            1 if has_amt else 0,
            1 if has_sup else 0,
            1 if has_nit else 0,
            1 if has_doc else 0,
        ]
    )
    return {
        "has_reference_price": has_ref,
        "has_award": has_award,
        "has_awarded_amount": has_amt,
        "has_supplier": has_sup,
        "has_nit": has_nit,
        "has_contract_doc": has_doc,
        "has_modifications": bool(getattr(contract, "has_modifications", False)),
        "completeness_level": min(level, 5),
    }


def apply_completeness(session: Session, contract: Contract) -> None:
    supplier = session.get(Supplier, contract.supplier_id) if contract.supplier_id else None
    flags = compute_completeness(contract, supplier)
    for k, v in flags.items():
        setattr(contract, k, v)


def enrich_sicoes_cuce(session: Session, cuce: str, *, force: bool = False) -> dict[str, Any]:
    """
    CUCE → ficha SICOES (Playwright+proxy when available) → update contract + claims.
    Soft-fail per CUCE. Without PROXY_URL, only refreshes completeness from DB fields.
    """
    cuce = (cuce or "").strip()
    contract = session.scalars(
        select(Contract).where(Contract.cuce == cuce, Contract.is_current.is_(True))
    ).first()
    if not contract:
        return {"ok": False, "error": "contract_not_found", "cuce": cuce}

    result: dict[str, Any] = {"ok": True, "cuce": cuce, "enriched": False, "mode": "completeness_only"}

    if PROXY_URL:
        try:
            from worker.adapters.sicoes import SicoesAdapter  # type: ignore

            adapter = SicoesAdapter()
            # Soft live fetch if adapter exposes detail method
            detail_fn = getattr(adapter, "fetch_cuce_detail", None)
            if callable(detail_fn):
                time.sleep(max(0.0, 1.0 / RATE_SECONDS))
                detail = detail_fn(cuce)
                if detail:
                    result["mode"] = "live"
                    result["enriched"] = True
                    _apply_detail(session, contract, detail)
        except Exception as exc:  # noqa: BLE001
            logger.warning("enrich soft-fail %s: %s", cuce, exc)
            result["warning"] = str(exc)

    apply_completeness(session, contract)
    q = classify_origin(
        source_id=contract.source_id,
        cuce=contract.cuce,
        source_note=contract.source_note,
    )
    for k, v in q.items():
        if hasattr(contract, k):
            setattr(contract, k, v)
    session.flush()
    result["completeness_level"] = contract.completeness_level
    return result


def _apply_detail(session: Session, contract: Contract, detail: dict[str, Any]) -> None:
    url = detail.get("url") or f"https://www.sicoes.gob.bo/portal/contrataciones/cuce/{contract.cuce}"
    raw_html = (detail.get("html") or "").encode("utf-8", errors="replace")
    sha = hashlib.sha256(raw_html or url.encode()).hexdigest()
    art = ensure_raw_artifact(
        session,
        url=url,
        sha256=sha,
        source_id="sicoes",
        mime="text/html",
        meta={"cuce": contract.cuce},
    )
    note = detail.get("source_note") or "sicoes_live_ficha"
    contract.source_note = note

    if detail.get("reference_price") is not None:
        rp = parse_money(str(detail["reference_price"])) or Decimal(str(detail["reference_price"]))
        contract.reference_price = rp
        add_claim(
            session,
            field="reference_price",
            entity_type="contract",
            entity_id=contract.id,
            source_id="sicoes",
            value_num=rp,
            confidence=0.75,
            evidence={"url": url, "sha256": sha, "quote": str(detail.get("reference_price"))},
            raw_artifact_id=art.id,
        )
    if detail.get("amount") is not None:
        amt = parse_money(str(detail["amount"])) or Decimal(str(detail["amount"]))
        contract.amount = amt
        add_claim(
            session,
            field="amount",
            entity_type="contract",
            entity_id=contract.id,
            source_id="sicoes",
            value_num=amt,
            confidence=0.75,
            evidence={"url": url, "sha256": sha, "quote": str(detail.get("amount"))},
            raw_artifact_id=art.id,
        )
    if detail.get("supplier_name"):
        add_claim(
            session,
            field="supplier_name",
            entity_type="contract",
            entity_id=contract.id,
            source_id="sicoes",
            value_text=str(detail["supplier_name"]),
            confidence=0.7,
            evidence={"url": url, "sha256": sha, "quote": str(detail["supplier_name"])},
            raw_artifact_id=art.id,
        )
    if detail.get("nit"):
        add_claim(
            session,
            field="nit",
            entity_type="contract",
            entity_id=contract.id,
            source_id="sicoes",
            value_text=re.sub(r"\D", "", str(detail["nit"])),
            confidence=0.8,
            evidence={"url": url, "sha256": sha, "quote": str(detail["nit"])},
            raw_artifact_id=art.id,
        )


def prioritize_cuces(session: Session, limit: int = 5000) -> list[str]:
    """Recent years first, then with amount, then rest."""
    rows = session.scalars(
        select(Contract)
        .where(
            Contract.is_current.is_(True),
            Contract.source_id == "sicoes",
            Contract.cuce.is_not(None),
            Contract.is_synthetic.is_(False),
        )
        .order_by(Contract.contract_date.desc().nullslast(), Contract.amount.desc().nullslast())
        .limit(limit)
    ).all()
    return [r.cuce for r in rows if r.cuce]

"""B9 — Redis TTL cache for /v1/stats (key stats:public / stats:all)."""
from __future__ import annotations

import json
import logging
import os
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from common.data_quality import public_budget_filter, public_contract_filter
from schema.models import Alert, AuditReport, BudgetLine, Contract, Discrepancy, Document, Entity, Supplier

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")
STATS_TTL_SECONDS = int(os.getenv("STATS_CACHE_TTL", "60"))


def _redis_client():
    try:
        import redis

        return redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=0.5)
    except Exception as exc:  # noqa: BLE001
        logger.debug("redis unavailable: %s", exc)
        return None


def cache_key(quality: str) -> str:
    return f"stats:{quality}"


def compute_stats(session: Session, *, quality: str = "public") -> dict[str, Any]:
    c_filter = public_contract_filter(Contract) if quality == "public" else Contract.is_current.is_(True)
    b_filter = public_budget_filter(BudgetLine) if quality == "public" else BudgetLine.is_current.is_(True)
    a_filter = Alert.is_synthetic.is_(False) if quality == "public" else True

    total_amt = session.scalar(
        select(func.coalesce(func.sum(Contract.amount), 0)).where(c_filter)
    ) or Decimal("0")
    budget_cur = session.scalar(
        select(func.coalesce(func.sum(BudgetLine.current_amount), 0)).where(b_filter)
    ) or Decimal("0")
    budget_exe = session.scalar(
        select(func.coalesce(func.sum(BudgetLine.executed_amount), 0)).where(b_filter)
    ) or Decimal("0")
    budget_ratio = (
        float(Decimal(budget_exe) / Decimal(budget_cur) * 100)
        if Decimal(budget_cur) > 0
        else None
    )
    severities = dict(
        session.execute(
            select(Alert.severity, func.count()).where(a_filter).group_by(Alert.severity)
        ).all()
    )
    return {
        "entities": session.scalar(
            select(func.count())
            .select_from(Entity)
            .where(Entity.is_synthetic.is_(False) if quality == "public" else True)
        )
        or 0,
        "suppliers": session.scalar(
            select(func.count())
            .select_from(Supplier)
            .where(Supplier.is_synthetic.is_(False) if quality == "public" else True)
        )
        or 0,
        "contracts": session.scalar(select(func.count()).select_from(Contract).where(c_filter)) or 0,
        "budgets": session.scalar(select(func.count()).select_from(BudgetLine).where(b_filter)) or 0,
        "alerts": session.scalar(select(func.count()).select_from(Alert).where(a_filter)) or 0,
        "audits": session.scalar(select(func.count()).select_from(AuditReport)) or 0,
        "discrepancies": session.scalar(select(func.count()).select_from(Discrepancy)) or 0,
        "documents": session.scalar(select(func.count()).select_from(Document)) or 0,
        "total_contract_amount": str(Decimal(total_amt)),
        "budget_current_total": str(Decimal(budget_cur)),
        "budget_executed_total": str(Decimal(budget_exe)),
        "budget_execution_ratio_pct": budget_ratio,
        "alerts_by_severity": {str(k): int(v) for k, v in severities.items()},
    }


def get_cached_stats(quality: str = "public") -> dict[str, Any] | None:
    client = _redis_client()
    if not client:
        return None
    try:
        raw = client.get(cache_key(quality))
        if not raw:
            return None
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.debug("stats cache get failed: %s", exc)
        return None


def set_cached_stats(payload: dict[str, Any], *, quality: str = "public") -> None:
    client = _redis_client()
    if not client:
        return
    try:
        client.setex(cache_key(quality), STATS_TTL_SECONDS, json.dumps(payload, default=str))
    except Exception as exc:  # noqa: BLE001
        logger.debug("stats cache set failed: %s", exc)


def refresh_stats(session: Session, *, quality: str = "public") -> dict[str, Any]:
    """Compute stats and store in Redis under stats:{quality} (TTL 60s)."""
    payload = compute_stats(session, quality=quality)
    set_cached_stats(payload, quality=quality)
    return payload


def get_or_refresh_stats(session: Session, *, quality: str = "public") -> dict[str, Any]:
    cached = get_cached_stats(quality)
    if cached is not None:
        return cached
    return refresh_stats(session, quality=quality)

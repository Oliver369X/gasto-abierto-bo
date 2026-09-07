"""F6: roll up identified fire budgets and contracts."""
from __future__ import annotations

from sqlalchemy import select

from common.fire.rollup import build_rollup
from schema.models import BudgetLine, FireExpenditure
from worker.fire.artifacts import write_json
from worker.fire.context import get_session


def run(session=None, *, write_artifact: bool = True) -> dict:
    own = session is None
    session = session or get_session()
    try:
        expenditures = list(session.scalars(select(FireExpenditure)).all())
        budgets = list(session.scalars(select(BudgetLine).where(BudgetLine.is_current.is_(True))).all())
        fire_budgets = [line for line in budgets if any(
            term in f"{line.program_project or ''} {line.category or ''}".lower()
            for term in ("incendio", "forestal", "videci", "emergencia"))]
        payload = {"status": "ok", "years": build_rollup(expenditures, fire_budgets),
                   "budget_lines_considered": len(fire_budgets),
                   "note": "Anti-doble conteo por CUCE/contrato/código. Pagos: not_published."}
        if write_artifact:
            write_json("f6_budget_cycles.json", payload)
        return payload
    finally:
        if own:
            session.close()

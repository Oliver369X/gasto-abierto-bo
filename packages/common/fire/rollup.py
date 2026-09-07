"""Shared fire budget/contract rollup without double-counting CUCE/contract."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

CYCLES = ("prevencion", "preparacion", "respuesta", "recuperacion")


def _value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value or "")


def _amount(value: Any) -> Decimal:
    return Decimal("0") if value is None else Decimal(str(value))


def build_rollup(expenditures: list[Any], budget_lines: list[Any] | None = None) -> list[dict[str, Any]]:
    """One contracted amount per CUCE/contract/code; budgets counted once via budget_line_id."""
    budget_lines = budget_lines or []
    linked_cycles = {
        row.budget_line_id: _value(row.cycle)
        for row in expenditures
        if getattr(row, "budget_line_id", None)
    }
    years = sorted({r.year for r in expenditures} | {getattr(b, "year", 0) for b in budget_lines} - {0})
    output: list[dict[str, Any]] = []

    for year in years:
        cycles = {c: {"budgeted": Decimal("0"), "contracted": Decimal("0")} for c in CYCLES}
        pools = Decimal("0")
        presupuesto = Decimal("0")
        directo = parcial = probable = contratado_ver = Decimal("0")
        seen_keys: set[str] = set()

        for budget in (b for b in budget_lines if b.year == year):
            amount = _amount(
                getattr(budget, "current_amount", None)
                or getattr(budget, "modified_amount", None)
                or getattr(budget, "initial_amount", None)
            )
            presupuesto += amount
            cycle = linked_cycles.get(budget.id)
            if cycle in cycles:
                cycles[cycle]["budgeted"] += amount

        for row in (r for r in expenditures if r.year == year):
            if getattr(row, "is_synthetic", False) or getattr(row, "ledger_bucket", None) == "sintetico":
                continue
            cuce = (getattr(row, "cuce", None) or "").strip()
            contract_id = getattr(row, "contract_id", None)
            code = getattr(row, "code", None) or f"row-{id(row)}"
            key = (
                f"cuce:{cuce}" if cuce
                else f"contract:{contract_id}" if contract_id
                else f"code:{code}"
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)

            amount = _amount(
                getattr(row, "amount_attributed_base", None)
                or getattr(row, "amount_attributed", None)
                or getattr(row, "amount_contract", None)
            )
            bucket = str(getattr(row, "ledger_bucket", "") or "")
            attribution = _value(getattr(row, "attribution", ""))
            cycle = _value(getattr(row, "cycle", ""))

            if bucket == "no_relacionado":
                pools += _amount(getattr(row, "amount_contract", None))
                continue
            if bucket == "verificable":
                contratado_ver += amount
                if cycle in cycles:
                    cycles[cycle]["contracted"] += amount
            elif cycle in cycles and amount:
                cycles[cycle]["contracted"] += amount

            if attribution == "directo" and bucket == "verificable":
                directo += amount
            elif attribution == "parcial":
                parcial += amount
            elif attribution == "probable" or (attribution == "directo" and bucket != "verificable"):
                probable += amount

        total_contracted = sum(cycles[c]["contracted"] for c in CYCLES)
        prev = cycles["prevencion"]["contracted"] + cycles["preparacion"]["contracted"]
        react = cycles["respuesta"]["contracted"] + cycles["recuperacion"]["contracted"]
        output.append(
            {
                "year": year,
                "presupuesto_identificado": float(presupuesto),
                "contratado_verificable": float(contratado_ver),
                "pagado_verificable": 0.0,
                "payment_data_status": "not_published",
                "directo_verificable": float(directo),
                "parcial": float(parcial),
                "probable": float(probable),
                "pools": float(pools),
                "unique_processes": len(seen_keys),
                "preventive_share": float(prev / total_contracted) if total_contracted else None,
                "reactive_share": float(react / total_contracted) if total_contracted else None,
                "cycles": {
                    c: {
                        "budgeted": float(cycles[c]["budgeted"]),
                        "contracted": float(cycles[c]["contracted"]),
                    }
                    for c in CYCLES
                },
            }
        )
    return output

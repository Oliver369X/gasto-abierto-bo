"""F11: build auditable territorial coverage for priority departments."""
from __future__ import annotations

from sqlalchemy import select

from schema.models import EmergencyDeclaration, FireExpenditure, OperationalOutput, Territory
from worker.fire.artifacts import write_json
from worker.fire.context import get_session

TARGETS = ("santa-cruz", "beni", "pando")


def coverage_level(expenditures: int, operations: int, declarations: int) -> str:
    return ("Sin datos", "Baja", "Media", "Alta")[
        sum(value > 0 for value in (expenditures, operations, declarations))]


def _declaration_year(row: EmergencyDeclaration) -> int | None:
    value = row.promulgated_at or row.published_at
    return value.year if value else None


def run(session=None, *, write_artifact: bool = True) -> dict:
    own = session is None
    session = session or get_session()
    try:
        territories = list(session.scalars(select(Territory)).all())
        departments = {row.slug: row for row in territories if row.slug in TARGETS}
        expenditures = list(session.scalars(select(FireExpenditure).where(
            FireExpenditure.is_synthetic.is_(False))).all())
        operations = list(session.scalars(select(OperationalOutput)).all())
        declarations = list(session.scalars(select(EmergencyDeclaration)).all())
        years = sorted({row.year for row in expenditures} | {row.year for row in operations}
                       | {year for row in declarations if (year := _declaration_year(row))})
        result = []
        for slug in TARGETS:
            department = departments.get(slug)
            if not department:
                result.append({"slug": slug, "department": slug.replace("-", " ").title(),
                               "status": "territory_not_found", "level": "Sin datos", "by_year": []})
                continue
            ids = {department.id} | {row.id for row in territories if row.parent_id == department.id}
            by_year, totals = [], [0, 0, 0]
            for year in years:
                counts = [sum(row.year == year and row.beneficiary_territory_id in ids for row in expenditures),
                          sum(row.year == year and row.territory_id in ids for row in operations),
                          sum(_declaration_year(row) == year and row.territory_id in ids for row in declarations)]
                totals = [left + right for left, right in zip(totals, counts)]
                by_year.append({"year": year, "expenditures": counts[0],
                                "operational_outputs": counts[1], "declarations": counts[2],
                                "level": coverage_level(*counts)})
            result.append({"slug": slug, "department": department.name,
                           "level": coverage_level(*totals),
                           "counts": {"expenditures": totals[0], "operational_outputs": totals[1],
                                      "declarations": totals[2]}, "by_year": by_year})
        payload = {"status": "ok", "method": "level equals represented source families",
                   "territories": result}
        if write_artifact:
            write_json("f11_territorial_coverage.json", payload)
        return payload
    finally:
        if own:
            session.close()

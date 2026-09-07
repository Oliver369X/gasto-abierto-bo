"""Alertas específicas del ledger de incendios forestales (F13)."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from schema.models import Alert, FireExpenditure, OperationalOutput


def _attr(r: FireExpenditure) -> str:
    a = r.attribution
    return a.value if hasattr(a, "value") else str(a)


def _cycle(r: FireExpenditure) -> str:
    c = r.cycle
    return c.value if hasattr(c, "value") else str(c)


def _amt(r: FireExpenditure) -> Decimal:
    if getattr(r, "is_synthetic", False) or getattr(r, "ledger_bucket", None) == "sintetico":
        return Decimal("0")
    return r.amount_attributed or Decimal("0")


def run_fire_alert_rules(session: Session) -> list[Alert]:
    """Replace previous fire_* alerts and materialize new ones."""
    for old in session.scalars(select(Alert).where(Alert.rule_id.like("fire_%"))).all():
        session.delete(old)
    session.flush()

    alerts: list[Alert] = []
    rows = [r for r in session.scalars(select(FireExpenditure)).all() if not getattr(r, "is_synthetic", False)]
    ops = list(session.scalars(select(OperationalOutput)).all())

    # 1) Concentration of fire spend by supplier (per year)
    by_year_sup: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0"))
    by_year_total: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for r in rows:
        if r.supplier_id is None or _amt(r) <= 0:
            continue
        if _attr(r) not in ("directo", "probable", "parcial"):
            continue
        by_year_sup[(r.year, r.supplier_id)] += _amt(r)
        by_year_total[r.year] += _amt(r)

    for (year, supplier_id), amt in by_year_sup.items():
        total = by_year_total.get(year) or Decimal("0")
        if total <= 0:
            continue
        share = amt / total
        if share >= Decimal("0.40"):
            from schema.models import Supplier

            sup = session.get(Supplier, supplier_id)
            name = sup.name if sup else f"#{supplier_id}"
            alerts.append(
                Alert(
                    rule_id="fire_supplier_concentration",
                    severity="high",
                    title=f"Incendios {year}: {name} concentra {share:.0%}",
                    explanation=(
                        f"Hecho: {name} recibe {amt:,.0f} BOB ({share:.0%} del gasto atribuido {year}). "
                        f"Regla: share≥40%. Hipótesis: dependencia de un solo proveedor en respuesta."
                    ),
                    supplier_id=supplier_id,
                    evidence={"year": year, "amount": str(amt), "share": float(share)},
                    source_id="fire_rules",
                )
            )

    # 2) Low prevention share
    for year in sorted({r.year for r in rows}):
        year_rows = [r for r in rows if r.year == year]
        total = sum(_amt(r) for r in year_rows if _attr(r) in ("directo", "probable", "parcial"))
        prev = sum(_amt(r) for r in year_rows if _cycle(r) == "prevencion")
        if total >= Decimal("5000000") and total > 0:
            ratio = prev / total
            if ratio < Decimal("0.10"):
                alerts.append(
                    Alert(
                        rule_id="fire_low_prevention_share",
                        severity="medium",
                        title=f"Incendios {year}: prevención solo {ratio:.0%} del gasto",
                        explanation=(
                            f"Hecho: prevención {prev:,.0f} / total atribuido {total:,.0f} BOB. "
                            f"Regla: ratio<10% con total≥5M. Hipótesis: dominio de reacción extraordinaria."
                        ),
                        evidence={"year": year, "preventive_ratio": float(ratio), "total": str(total)},
                        source_id="fire_rules",
                    )
                )

    # 3) Quality D/E heavy year
    for year in sorted({r.year for r in rows}):
        year_rows = [r for r in rows if r.year == year]
        d_grade = sum(1 for r in year_rows if (r.quality_grade or "").upper() in ("D", "E"))
        if year_rows and d_grade / len(year_rows) >= 0.5:
            alerts.append(
                Alert(
                    rule_id="fire_low_data_quality",
                    severity="low",
                    title=f"Incendios {year}: {d_grade}/{len(year_rows)} expedientes calidad D/E",
                    explanation=(
                        f"Hecho: {d_grade} de {len(year_rows)} con grado D/E. "
                        f"Regla: ≥50% baja calidad. Hipótesis: cobertura documental incompleta."
                    ),
                    evidence={"year": year, "low_quality": d_grade, "total": len(year_rows)},
                    source_id="fire_rules",
                )
            )

    # 4) Aircraft / aeronave without operational link
    for r in rows:
        title = (r.title or "") + " " + (r.object_description or "")
        if not any(k in title.lower() for k in ("aeronave", "helicóptero", "helicoptero", "aviación", "aviacion")):
            continue
        strength = (r.link_strength or "").upper()
        if strength in ("CONFIRMADO", "FUERTEMENTE_VINCULADO"):
            continue
        year_ops = [o for o in ops if o.year == r.year]
        if not year_ops:
            alerts.append(
                Alert(
                    rule_id="fire_aircraft_without_ops",
                    severity="high",
                    title=f"{r.code}: aeronave sin operaciones documentadas",
                    explanation=(
                        f"Hecho: expediente {r.code} tipifica aeronave/helicóptero y no hay "
                        f"OperationalOutput del año {r.year} ni link_strength fuerte. "
                        f"Regla: fire_aircraft_without_ops. Hipótesis: pago/alquiler sin resultado trazable "
                        f"o evidencia ops aún no publicada."
                    ),
                    evidence={"code": r.code, "year": r.year, "link_strength": r.link_strength},
                    source_id="fire_rules",
                )
            )

    # 5) Fire spend without territory
    for r in rows:
        if _attr(r) not in ("directo", "probable", "parcial"):
            continue
        if r.beneficiary_territory_id is None and _amt(r) > 0:
            alerts.append(
                Alert(
                    rule_id="fire_spend_without_territory",
                    severity="medium",
                    title=f"{r.code}: gasto fire sin territorio beneficiario",
                    explanation=(
                        f"Hecho: {r.code} tiene monto atribuido y territory_id nulo. "
                        f"Regla: fire_spend_without_territory. Hipótesis: compra nacional sin desagregar "
                        f"o dato faltante en fuente."
                    ),
                    evidence={"code": r.code, "amount": str(_amt(r))},
                    source_id="fire_rules",
                )
            )

    # 6) Announcement / RPC mention without CUCE
    for r in rows:
        ev = r.evidence or {}
        if r.cuce:
            continue
        if ev.get("announced_without_contract") or (r.recovery_status or "") in (
            "not_publicly_recoverable",
            "not_published",
        ):
            title_l = (r.title or "").lower()
            if any(k in title_l for k in ("aeronave", "helicóptero", "helicoptero", "incendio")):
                alerts.append(
                    Alert(
                        rule_id="fire_announcement_without_cuce",
                        severity="high",
                        title=f"{r.code}: anuncio/ops sin CUCE público",
                        explanation=(
                            f"Hecho: {r.code} sin CUCE; recovery_status={r.recovery_status}. "
                            f"Regla: fire_announcement_without_cuce. Hipótesis: proceso no publicado "
                            f"en espejo SICOES o contratación aún no adjudicada."
                        ),
                        evidence={"code": r.code, "recovery_status": r.recovery_status},
                        source_id="fire_rules",
                    )
                )

    # 7) Post-emergency closure spike (contracts dated after season end without note)
    for r in rows:
        ev = r.evidence or {}
        if ev.get("post_emergency_window") and _amt(r) > 0:
            alerts.append(
                Alert(
                    rule_id="fire_post_emergency_spend",
                    severity="medium",
                    title=f"{r.code}: gasto post-cierre de emergencia",
                    explanation=(
                        f"Hecho: evidencia marca post_emergency_window. "
                        f"Regla: fire_post_emergency_spend. Hipótesis: liquidación tardía legítima "
                        f"o contratación fuera de ventana de declaratoria."
                    ),
                    evidence={"code": r.code, "evidence": ev},
                    source_id="fire_rules",
                )
            )

    # 8) Fragmentation — many small same-object contracts same year/entity
    by_key: dict[tuple[int, int | None, str], list[FireExpenditure]] = defaultdict(list)
    for r in rows:
        if _amt(r) <= 0:
            continue
        key_title = (r.title or "")[:80].lower()
        by_key[(r.year, r.paying_entity_id, key_title)].append(r)
    for (year, entity_id, title), group in by_key.items():
        if len(group) >= 4 and sum(_amt(x) for x in group) > 0:
            alerts.append(
                Alert(
                    rule_id="fire_fragmentation",
                    severity="medium",
                    title=f"Incendios {year}: {len(group)} contratos fragmentados (mismo objeto)",
                    explanation=(
                        f"Hecho: {len(group)} expedientes con título similar y misma entidad. "
                        f"Regla: ≥4 fragmentos. Hipótesis: fraccionamiento o compras repetidas."
                    ),
                    evidence={
                        "year": year,
                        "entity_id": entity_id,
                        "codes": [g.code for g in group],
                        "title": title,
                    },
                    source_id="fire_rules",
                )
            )

    # 9) Atypical unit price vs peers (same year, same cycle, amount outlier)
    by_year_cycle: dict[tuple[int, str], list[FireExpenditure]] = defaultdict(list)
    for r in rows:
        if _amt(r) > 0:
            by_year_cycle[(r.year, _cycle(r))].append(r)
    for (year, cycle), group in by_year_cycle.items():
        if len(group) < 5:
            continue
        amounts = sorted(_amt(r) for r in group)
        median = amounts[len(amounts) // 2]
        if median <= 0:
            continue
        for r in group:
            if _amt(r) >= median * Decimal("10"):
                alerts.append(
                    Alert(
                        rule_id="fire_atypical_price",
                        severity="medium",
                        title=f"{r.code}: monto { _amt(r):,.0f} ≫ mediana {median:,.0f} ({cycle})",
                        explanation=(
                            f"Hecho: monto ≥10× mediana del ciclo {cycle} en {year}. "
                            f"Regla: fire_atypical_price. Hipótesis: tipología distinta (aeronave) "
                            f"o error/atipicidad a revisar."
                        ),
                        evidence={
                            "code": r.code,
                            "amount": str(_amt(r)),
                            "median": str(median),
                            "cycle": cycle,
                        },
                        source_id="fire_rules",
                    )
                )

    # 10) Directo without document_id / evidence
    for r in rows:
        if _attr(r) != "directo":
            continue
        if r.document_id is None and not (r.evidence or {}).get("page") and not r.cuce:
            alerts.append(
                Alert(
                    rule_id="fire_direct_without_evidence",
                    severity="high",
                    title=f"{r.code}: directo sin documento/CUCE",
                    explanation=(
                        f"Hecho: attribution=directo sin document_id ni CUCE. "
                        f"Regla: fire_direct_without_evidence. Hipótesis: clasificación prematura."
                    ),
                    evidence={"code": r.code},
                    source_id="fire_rules",
                )
            )

    # 11) Pool emergencia labeled as fire (no_relacionado with large contract)
    for r in rows:
        if getattr(r, "ledger_bucket", None) == "no_relacionado" and (r.amount_contract or 0) > 10_000_000:
            alerts.append(
                Alert(
                    rule_id="fire_large_pool_excluded",
                    severity="low",
                    title=f"{r.code}: pool grande excluido del headline fire",
                    explanation=(
                        f"Hecho: contrato {r.amount_contract} BOB en bucket no_relacionado. "
                        f"Regla: informar exclusión. Hipótesis: multi-evento (inundación+incendio) "
                        f"sin desagregar — correcto no sumarlo al headline."
                    ),
                    evidence={"code": r.code, "amount_contract": str(r.amount_contract)},
                    source_id="fire_rules",
                )
            )

    for a in alerts:
        session.add(a)
    session.flush()
    return alerts

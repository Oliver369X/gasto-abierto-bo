"""Unit gates for AURA Incendios phases F6–F12."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from common.fire.capability import classify_asset
from common.fire.linking import infer_strength
from common.fire.rollup import build_rollup
from worker.fire.phases.f07_declarations import declaration_year
from worker.fire.phases.f08_firms import cluster_detections
from worker.fire.phases.f09_events import confidence_for_sources
from worker.fire.phases.f10_capability import capability_from_title
from worker.fire.phases.f11_territorial import coverage_level
from worker.fire.phases.f05_sicoes_backfill import run_enrich


def row(**values):
    return SimpleNamespace(**values)


def test_f6_does_not_double_count_linked_budget_line_and_excludes_synthetic():
    budget = row(
        id=7,
        year=2024,
        current_amount=Decimal("100"),
        modified_amount=None,
        initial_amount=None,
    )
    expenditure = row(
        year=2024,
        cycle="respuesta",
        attribution="directo",
        ledger_bucket="verificable",
        is_synthetic=False,
        budget_line_id=7,
        amount_contract=Decimal("80"),
        amount_attributed=Decimal("80"),
    )
    synthetic = row(
        year=2024,
        cycle="respuesta",
        attribution="directo",
        ledger_bucket="sintetico",
        is_synthetic=True,
        budget_line_id=None,
        amount_contract=Decimal("999"),
        amount_attributed=Decimal("999"),
    )

    result = build_rollup([expenditure, synthetic], [budget])

    assert result[0]["presupuesto_identificado"] == 100.0
    assert result[0]["contratado_verificable"] == 80.0
    assert result[0]["cycles"]["respuesta"]["budgeted"] == 100.0
    assert result[0]["cycles"]["respuesta"]["contracted"] == 80.0


def test_f7_uses_declaration_date_year():
    assert declaration_year(row(promulgated_at=date(2024, 9, 7), published_at=None)) == 2024


def test_f8_clusters_real_detections_but_ignores_samples():
    detections = [
        row(id=1, latitude=Decimal("-16.50"), longitude=Decimal("-63.20"), source_id="firms"),
        row(id=2, latitude=Decimal("-16.52"), longitude=Decimal("-63.22"), source_id="firms"),
        row(id=3, latitude=Decimal("-16.51"), longitude=Decimal("-63.21"), source_id="sample"),
    ]
    groups = cluster_detections(detections, grid_size=Decimal("0.1"))
    assert [d.id for d in groups[0]] == [1, 2]


def test_f9_confidence_requires_two_sources_for_high_label():
    assert confidence_for_sources(1) == ("single_source", Decimal("0.500"))
    assert confidence_for_sources(2) == ("multi_source", Decimal("0.800"))


def test_f10_recognizes_only_confirmed_capability_terms():
    assert capability_from_title("Servicio de alquiler de aeronave para incendios") == (
        "aeronave",
        "rented",
        "alquiler_emergencia",
    )
    assert capability_from_title("Compra de útiles de oficina") is None
    assert classify_asset("alquiler de helicóptero")["asset_type"] == "aeronave"


def test_f11_coverage_level_is_count_based():
    assert coverage_level(0, 0, 0) == "Sin datos"
    assert coverage_level(1, 0, 0) == "Baja"
    assert coverage_level(1, 1, 0) == "Media"
    assert coverage_level(1, 1, 1) == "Alta"


def test_f12_never_claims_confirmed_without_direct_evidence():
    assert infer_strength(same_year=True, event_linked=True, explicit_reference=False) == "PROBABLE"
    assert infer_strength(same_year=True, event_linked=True, explicit_reference=True) == "CONFIRMADO"


def test_f5_enrich_soft_blocks_without_proxy(monkeypatch):
    monkeypatch.delenv("PROXY_URL", raising=False)
    assert run_enrich(object(), write_artifact=False) == {
        "status": "blocked_no_proxy",
        "enriched": 0,
        "note": "PROXY_URL required for live SICOES enrich (REQUIRE_PROXY_FOR_LIVE=1).",
    }

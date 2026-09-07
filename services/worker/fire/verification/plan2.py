"""End-to-end verification of AURA Incendios Plan 2."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select

from common.fire.ledger import amount_for_public_kpi
from schema.models import ActiveFireDetection, FireCluster, FireEvent, FireExpenditure, FireLink
from worker.fire.context import database_url, get_session

ROOT = Path(__file__).resolve().parents[4]
_IN_DOCKER = Path("/.dockerenv").exists()
API_BASE = (
    os.getenv("API_BASE")
    or os.getenv("API_INTERNAL_URL")
    or ("http://api:8000" if _IN_DOCKER else "http://localhost:8010")
).rstrip("/")
WEB_BASE = os.getenv(
    "WEB_BASE", "http://web:3000" if _IN_DOCKER else "http://localhost:3010"
).rstrip("/")


class GateReport:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.oks: list[str] = []

    def ok(self, message: str) -> None:
        self.oks.append(message)
        print(f"  OK  {message}")

    def fail(self, message: str) -> None:
        self.failures.append(message)
        print(f"FAIL  {message}")

    def get_json(self, path: str):
        try:
            with urllib.request.urlopen(f"{API_BASE}{path}", timeout=30) as response:
                if response.status != 200:
                    self.fail(f"GET {path} status={response.status}")
                    return None
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            self.fail(f"GET {path} error: {exc}")
            return None

    def check_api(self) -> None:
        print("\n== API ==")
        health = self.get_json("/v1/health")
        self.ok("health status=ok") if health and health.get("status") == "ok" else self.fail("health not ok")
        ledger = self.get_json("/v1/fire/ledger?year=2024")
        if ledger:
            direct = Decimal(str(ledger.get("amount_direct_verifiable", "0")))
            self.ok("ledger amount_direct_verifiable == 870000") if direct == Decimal("870000") else self.fail(f"ledger directo={direct}")
            self.ok("ledger has disclaimer") if ledger.get("disclaimer") else self.fail("ledger disclaimer missing")
        coverage = self.get_json("/v1/fire/coverage")
        if coverage:
            offline = (coverage.get("expenditures_by_source") or {}).get("sicoes_offline", 0)
            self.ok(f"coverage sicoes_offline={offline}") if offline >= 100 else self.fail(f"coverage sicoes_offline too low: {offline}")
            clusters = coverage.get("fire_clusters", 0)
            self.ok(f"coverage clusters={clusters}") if clusters >= 1 else self.fail("coverage clusters < 1")
        geojson = self.get_json("/v1/fire/coverage.geojson?year=2024")
        features = geojson.get("features", []) if geojson else []
        self.ok("coverage geojson features=3") if len(features) == 3 else self.fail(
            f"coverage geojson features={len(features)}"
        )
        if features:
            props = features[0].get("properties") or {}
            self.ok("geojson has level") if props.get("level") in {"Alta", "Media", "Baja", "Sin datos"} else self.fail(
                "geojson missing level"
            )
        caps = self.get_json("/v1/fire/capabilities/summary?year=2024")
        self.ok("capabilities summary") if caps and "preventive_assets" in caps else self.fail(
            "capabilities summary missing"
        )
        for path, label in (("/v1/fire/cycles?year=2024", "cycles"),
                            ("/v1/fire/payers?year=2024&limit=5", "payers"),
                            ("/v1/fire/events?year=2024", "events")):
            value = self.get_json(path)
            self.ok(f"{label} non-empty") if value else self.fail(f"{label} empty")

    def check_db(self) -> None:
        print("\n== DB ==")
        session = get_session()
        try:
            rows = list(session.scalars(select(FireExpenditure)).all())
            verifiable = sum(amount_for_public_kpi(row) for row in rows if row.year == 2024)
            offline = sum(row.source_id == "sicoes_offline" for row in rows)
            self.ok(f"db verificable 2024={verifiable}") if verifiable == Decimal("870000") else self.fail(f"db verificable 2024={verifiable}")
            self.ok(f"db sicoes_offline={offline}") if offline >= 100 else self.fail(f"db sicoes_offline={offline}")
            counts = {model.__tablename__: session.scalar(select(func.count()).select_from(model)) or 0
                      for model in (FireCluster, FireEvent, FireLink)}
            self.ok(f"db counts={counts}")
            samples = session.scalar(select(func.count()).select_from(ActiveFireDetection).where(
                ActiveFireDetection.source_id.ilike("%sample%"))) or 0
            self.ok("db FIRMS samples purged") if samples == 0 else self.fail(f"db still has {samples} sample detections")
            aero_ids = [row.id for row in rows if "AERO" in row.code]
            links = (
                session.scalar(select(func.count()).select_from(FireLink).where(
                    FireLink.from_type == "fire_expenditure",
                    FireLink.from_id.in_(aero_ids))) or 0
                if aero_ids else 0
            )
            self.ok(f"db aero links={links}") if 0 < links < 200 else self.fail(f"db aero links unexpected={links}")
        except Exception as exc:
            self.fail(f"db check error: {exc}")
        finally:
            session.close()

    def check_artifacts(self) -> None:
        print("\n== Artifacts ==")
        required = ["f2_aeronaves_2024.json", "f5_sicoes_fire_backfill.json",
                    "f6_budget_cycles.json", "f7_declarations.json", "f8_firms_status.json",
                    "f9_events.json", "f12_links.json", "corpus_v1/manifest.json",
                    "corpus_v1/mindef_structured.json"]
        for relative in required:
            path = ROOT / "data" / "extracted" / relative
            self.ok(relative) if path.exists() and path.stat().st_size > 20 else self.fail(f"missing/empty {relative}")

        f2 = ROOT / "data" / "extracted" / "f2_aeronaves_2024.json"
        if f2.exists():
            dossiers = (json.loads(f2.read_text(encoding="utf-8")).get("dossiers") or [])
            self.ok(f"f2 dossiers={len(dossiers)}") if len(dossiers) == 4 else self.fail(f"f2 dossiers={len(dossiers)}")
            invented = [
                d for d in dossiers
                if "invent" in json.dumps(d.get("fields") or {}, ensure_ascii=False).lower()
            ]
            self.ok("f2 no invented providers") if not invented else self.fail("f2 invented field content")

        f7 = ROOT / "data" / "extracted" / "f7_declarations.json"
        if f7.exists():
            years = json.loads(f7.read_text(encoding="utf-8")).get("years") or []
            self.ok(f"f7 years={len(years)}") if len(years) == 7 else self.fail(f"f7 years={len(years)}")
            bad = [y for y in years if y.get("status") not in {"found", "none_found"}]
            self.ok("f7 year statuses") if not bad else self.fail(f"f7 bad statuses={bad}")

        f8 = ROOT / "data" / "extracted" / "f8_firms_status.json"
        if f8.exists():
            live = json.loads(f8.read_text(encoding="utf-8")).get("live_fetch")
            allowed = {
                "fetched", "blocked_missing_MAP_KEY", "key_present_fetch_disabled",
                "key_present_but_fetch_failed",
            }
            self.ok(f"f8 live_fetch={live}") if live in allowed else self.fail(f"f8 live_fetch unexpected={live}")

        enrich = ROOT / "data" / "extracted" / "f05_enrich_cuce.json"
        if enrich.exists():
            body = json.loads(enrich.read_text(encoding="utf-8"))
            ok_enrich = body.get("status") == "blocked_no_proxy" or int(body.get("enriched") or 0) >= 1
            self.ok(f"enrich status={body.get('status')}") if ok_enrich else self.fail(f"enrich unexpected={body}")
        else:
            self.fail("missing f05_enrich_cuce.json")

        for soft in ("f03_sernap_text.json", "f03_sernap_ocr.json", "f04_reclassify.json"):
            path = ROOT / "data" / "extracted" / soft
            if path.exists() and path.stat().st_size > 10:
                self.ok(f"soft {soft}")

    def check_web(self) -> None:
        print("\n== Web ==")
        for path in ("/", "/incendios", "/incendios?year=2024", "/incendios/mapa?year=2024"):
            try:
                with urllib.request.urlopen(f"{WEB_BASE}{path}", timeout=45) as response:
                    body = response.read().decode("utf-8", errors="ignore")
                    if response.status != 200:
                        self.fail(f"web {path} status={response.status}")
                        continue
                    self.ok(f"web {path} status=200")
                    if path.startswith("/incendios") and "mapa" not in path:
                        self.ok("web incendios mentions Capacidad") if "Capacidad" in body else self.fail(
                            "web incendios missing Capacidad"
                        )
                    if "mapa" in path:
                        has_map = any(token in body.lower() for token in ("svg", "maplibre", "leaflet", "cobertura"))
                        self.ok("web mapa has map markup") if has_map else self.fail("web mapa missing map markup")
            except Exception as exc:
                self.fail(f"web {path} error: {exc}")


def main() -> int:
    report = GateReport()
    print(f"API_BASE={API_BASE}")
    print(f"DATABASE_URL={database_url().split('@')[-1]}")
    report.check_api()
    report.check_db()
    report.check_artifacts()
    report.check_web()
    print(f"\n== SUMMARY ==\npassed={len(report.oks)} failed={len(report.failures)}")
    if report.failures:
        for failure in report.failures:
            print(f"  - {failure}")
        return 1
    print("ALL GATES PASSED")
    return 0

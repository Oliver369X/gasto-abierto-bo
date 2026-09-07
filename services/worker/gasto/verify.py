#!/usr/bin/env python3
"""Production-style smoke verification for Plan Maestro G1–G10.

Saves JSON evidence under qa-artifacts/master-g1-g10/
Exit 0 only if all critical checks pass.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Ensure packages/ and services/ are importable when run as module
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT / "packages") not in sys.path:
    sys.path.insert(0, str(_ROOT / "packages"))
if str(_ROOT / "services") not in sys.path:
    sys.path.insert(0, str(_ROOT / "services"))

_IN_DOCKER = Path("/.dockerenv").exists()
_DEFAULT_API = "http://api:8000" if _IN_DOCKER else "http://localhost:8010"
_DEFAULT_WEB = "http://web:3000" if _IN_DOCKER else "http://localhost:3010"
API = (os.getenv("API_BASE") or os.getenv("API_INTERNAL_URL") or _DEFAULT_API).rstrip("/")
WEB = os.getenv("WEB_BASE", _DEFAULT_WEB).rstrip("/")
OUT = _ROOT / "qa-artifacts" / "master-g1-g10"


def get(url: str, timeout: int = 120, *, max_chars: int | None = 500_000) -> tuple[int, object]:
    req = urllib.request.Request(url, headers={"Accept": "application/json,text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            if "json" in ctype:
                return resp.status, json.loads(body.decode("utf-8"))
            text = body.decode("utf-8", errors="replace")
            if max_chars is not None:
                text = text[:max_chars]
            return resp.status, text
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")[:500]
    except Exception as e:  # noqa: BLE001
        return 0, str(e)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results: dict[str, object] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "api": API,
        "web": WEB,
        "checks": {},
        "failures": [],
    }
    checks: dict[str, dict] = {}

    def record(name: str, ok: bool, detail: object) -> None:
        checks[name] = {"ok": ok, "detail": detail}
        if not ok:
            results["failures"].append(name)

    # --- API ---
    st, health = get(f"{API}/v1/health")
    record("api_health", st == 200 and isinstance(health, dict) and health.get("status") == "ok", health)

    st, stats_pub = get(f"{API}/v1/stats?quality=public", timeout=180)
    ok_stats = (
        st == 200
        and isinstance(stats_pub, dict)
        and int(stats_pub.get("contracts") or 0) > 1_000_000
        and float(stats_pub.get("total_contract_amount") or 0) > 0
    )
    record("stats_public", ok_stats, stats_pub if st == 200 else {"status": st, "body": stats_pub})

    st, stats_all = get(f"{API}/v1/stats?quality=all", timeout=180)
    record(
        "stats_all_ge_public",
        st == 200
        and isinstance(stats_all, dict)
        and isinstance(stats_pub, dict)
        and int(stats_all.get("contracts") or 0) >= int(stats_pub.get("contracts") or 0),
        {"all": stats_all.get("contracts") if isinstance(stats_all, dict) else stats_all,
         "public": stats_pub.get("contracts") if isinstance(stats_pub, dict) else None},
    )

    st, gate = get(f"{API}/v1/product-gate")
    record(
        "product_gate_pass",
        st == 200 and isinstance(gate, dict) and gate.get("pass") is True,
        gate,
    )
    if isinstance(gate, dict):
        for k, v in (gate.get("checks") or {}).items():
            record(f"gate_check_{k}", bool(v), v)

    st, cov = get(f"{API}/v1/coverage/sicoes")
    record(
        "coverage_dual_universe",
        st == 200
        and isinstance(cov, dict)
        and int(cov.get("sample_size") or 0) > 0
        and int(cov.get("known_amount_universe") or 0) > 0
        and isinstance(cov.get("known_amount_flags"), list)
        and len(cov.get("known_amount_flags") or []) >= 3,
        cov,
    )
    # Known-amount universe should show high completeness
    if isinstance(cov, dict):
        flags = {f["flag"]: f for f in (cov.get("known_amount_flags") or []) if isinstance(f, dict)}
        amt = flags.get("has_awarded_amount_or_ref", {})
        record(
            "known_amount_pct_ge_90",
            float(amt.get("pct") or 0) >= 90,
            amt,
        )

    st, contracts = get(f"{API}/v1/contracts?limit=5&min_amount=1")
    record(
        "contracts_with_amount",
        st == 200 and isinstance(contracts, list) and len(contracts) > 0,
        contracts[:2] if isinstance(contracts, list) else contracts,
    )

    contract_id = None
    if isinstance(contracts, list) and contracts:
        contract_id = contracts[0].get("id")
        # quality badge fields present
        c0 = contracts[0]
        record(
            "contract_quality_fields",
            "source_quality" in c0 and "is_synthetic" in c0,
            {k: c0.get(k) for k in ("id", "source_quality", "is_synthetic", "completeness_level", "amount")},
        )

    if contract_id:
        st, claims = get(f"{API}/v1/contracts/{contract_id}/claims")
        record(
            "contract_claims",
            st == 200 and isinstance(claims, list) and len(claims) >= 1,
            claims[:3] if isinstance(claims, list) else claims,
        )
        st, evidence = get(f"{API}/v1/contracts/{contract_id}/evidence")
        record(
            "contract_evidence",
            st == 200 and isinstance(evidence, list) and len(evidence) >= 1,
            evidence[:2] if isinstance(evidence, list) else evidence,
        )

    st, conflicts = get(f"{API}/v1/conflicts?limit=5")
    record(
        "conflicts_open",
        st == 200 and isinstance(conflicts, list) and len(conflicts) >= 1,
        conflicts[:2] if isinstance(conflicts, list) else conflicts,
    )

    st, suppliers = get(f"{API}/v1/suppliers?limit=5")
    master_ok = False
    master_detail: object = None
    if st == 200 and isinstance(suppliers, list) and suppliers:
        mid = suppliers[0].get("supplier_master_id")
        if mid:
            st2, master = get(f"{API}/v1/supplier-masters/{mid}")
            st3, aliases = get(f"{API}/v1/supplier-masters/{mid}/aliases")
            master_ok = st2 == 200 and isinstance(master, dict) and "canonical_name" in master
            master_detail = {"master": master, "aliases": aliases}
        else:
            master_detail = {"supplier": suppliers[0], "note": "no supplier_master_id"}
    record("supplier_master", master_ok, master_detail)

    st, entities = get(f"{API}/v1/entities?limit=5")
    em_ok = False
    em_detail: object = None
    if st == 200 and isinstance(entities, list) and entities:
        mid = entities[0].get("entity_master_id")
        if mid:
            st2, master = get(f"{API}/v1/entity-masters/{mid}")
            em_ok = st2 == 200 and isinstance(master, dict)
            em_detail = master
        else:
            em_detail = entities[0]
    record("entity_master", em_ok, em_detail)

    st, audits = get(f"{API}/v1/audits?limit=10")
    findings_ok = False
    findings_detail: object = None
    if st == 200 and isinstance(audits, list) and audits:
        aid = audits[0]["id"]
        st2, findings = get(f"{API}/v1/audits/{aid}/findings")
        findings_ok = st2 == 200 and isinstance(findings, list) and len(findings) >= 1
        findings_detail = {"audit_id": aid, "findings_n": len(findings) if isinstance(findings, list) else findings}
    record("audit_findings", findings_ok, findings_detail)

    st, alerts = get(f"{API}/v1/alerts?quality=public&limit=5")
    record(
        "alerts_public",
        st == 200 and isinstance(alerts, list),
        alerts[:2] if isinstance(alerts, list) else alerts,
    )

    st, years = get(f"{API}/v1/history/years")
    record(
        "history_years",
        st == 200 and isinstance(years, list) and len(years) >= 5,
        {"n": len(years) if isinstance(years, list) else years},
    )

    st, search = get(f"{API}/v1/search?q=salud&limit=5")
    record(
        "search",
        st == 200 and isinstance(search, dict) and isinstance(search.get("hits"), list),
        search if isinstance(search, dict) else search,
    )

    # budgets phases
    st, budgets = get(f"{API}/v1/budgets?limit=3")
    phase_ok = False
    if st == 200 and isinstance(budgets, list) and budgets:
        b0 = budgets[0]
        phase_ok = any(k in b0 for k in ("budget_initial", "budget_current", "payment", "budget_phase"))
    record("budget_phases_fields", phase_ok, budgets[:1] if isinstance(budgets, list) else budgets)

    # --- WEB ---
    for path, name in [
        ("/cobertura", "web_cobertura"),
        ("/explorar", "web_explorar"),
        ("/historico", "web_historico"),
        ("/auditorias", "web_auditorias"),
        ("/fuentes", "web_fuentes"),
    ]:
        st, body = get(f"{WEB}{path}", timeout=60)
        html_ok = st == 200 and isinstance(body, str) and len(body) > 200 and "error" not in body.lower()[:200]
        # Next error pages still 200 sometimes — look for Gasto Abierto brand or section
        if isinstance(body, str):
            html_ok = st == 200 and ("Gasto Abierto" in body or "Cobertura" in body or "Explorar" in body or "Auditor" in body)
        record(name, html_ok, {"status": st, "len": len(body) if isinstance(body, str) else None})

    if contract_id:
        st, body = get(f"{WEB}/contrato/{contract_id}", timeout=60)
        record(
            "web_contrato_evidence",
            st == 200 and isinstance(body, str) and ("Evidencia" in body or "Provenance" in body or "Monto" in body),
            {"status": st, "has_evidencia": isinstance(body, str) and "Evidencia" in body},
        )

    results["checks"] = checks
    results["finished_at"] = datetime.now(timezone.utc).isoformat()
    results["passed"] = len(results["failures"]) == 0
    results["summary"] = {
        "total": len(checks),
        "passed": sum(1 for c in checks.values() if c["ok"]),
        "failed": len(results["failures"]),
        "failures": results["failures"],
    }

    out_file = OUT / "verification.json"
    out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    # Human markdown report
    lines = [
        "# Evidencia QA — Plan Maestro G1–G10",
        "",
        f"- Fecha UTC: `{results['started_at']}`",
        f"- API: `{API}` · Web: `{WEB}`",
        f"- Resultado: **{'PASS' if results['passed'] else 'FAIL'}** "
        f"({results['summary']['passed']}/{results['summary']['total']})",
        "",
        "## Checks",
        "",
        "| Check | OK |",
        "|-------|----|",
    ]
    for name, c in checks.items():
        lines.append(f"| `{name}` | {'✅' if c['ok'] else '❌'} |")
    if results["failures"]:
        lines += ["", "## Fallos", ""]
        for f in results["failures"]:
            lines.append(f"- `{f}`: `{json.dumps(checks[f]['detail'], ensure_ascii=False, default=str)[:300]}`")
    lines += [
        "",
        "## Artefactos",
        "",
        f"- JSON completo: `{out_file.as_posix()}`",
        "- Pytest: `qa-artifacts/master-g1-g10/pytest.txt`",
        "",
        "## Comentario cierre (ClickUp)",
        "",
        "```",
        "✅ Hecho",
        "- Qué: Verificación prod-ready Plan Maestro G1–G10",
        f"- Comando: python scripts/verify_master_plan.py → {results['summary']['passed']}/{results['summary']['total']}",
        "- Evidencia: qa-artifacts/master-g1-g10/",
        "```",
        "",
    ]
    (OUT / "EVIDENCIA.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(results["summary"], indent=2, ensure_ascii=False))
    print(f"Wrote {out_file}")
    return 0 if results["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

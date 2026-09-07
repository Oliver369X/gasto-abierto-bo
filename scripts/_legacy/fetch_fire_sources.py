#!/usr/bin/env python3
"""Download public official documents for AURA Incendios (respectful crawler)."""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
UA = "GastoAbiertoBO/0.6 (+research; respectful crawler)"

URLS = {
    "mindef/rpc_final_2024.pdf": (
        "https://www.mindef.gob.bo/wp-content/uploads/2026/01/"
        "12032025_INFORME_RPCFinal_2024_V15.pdf"
    ),
    "mindef/rendicion_index.html": (
        "https://www.mindef.gob.bo/index.php/rendicion-publica-de-cuentas/"
    ),
    "mindef/presupuesto_index.html": (
        "https://www.mindef.gob.bo/index.php/presupuesto-de-las-estrategias-intitucionales/"
    ),
    "mindef/contratos_index.html": "https://www.mindef.gob.bo/index.php/contratos/",
    "abt/ejecucion_index.html": (
        "https://www.abt.gob.bo/index.php/institucion/plan-estrategico/"
        "programado-ejecutado-y-resultados"
    ),
    "abt/presupuesto_index.html": (
        "https://www.abt.gob.bo/index.php/transparencia/informacion-financiera/"
        "presupuesto-institucional"
    ),
    "abt/adquisiciones_index.html": (
        "https://www.abt.gob.bo/index.php/transparencia/informacion-financiera/"
        "adquisiciones-de-bienes-y-servicios"
    ),
    "sernap/datos_index.html": "https://www.sernap.gob.bo/index.php/datos/",
    "sernap/rendicion_index.html": (
        "https://www.sernap.gob.bo/index.php/rendicion-publica-de-cuentas/"
    ),
    "gaceta_scz/decretos_index.html": (
        "https://gacetaoficial.santacruz.gob.bo/decretosdepartamentales"
    ),
    "cge/auditorias_index.html": (
        "https://www.contraloria.gob.bo/informes-de-auditorias-nuevo/"
    ),
}


def main() -> None:
    client = httpx.Client(
        headers={"User-Agent": UA},
        follow_redirects=True,
        timeout=120.0,
    )
    for rel, url in URLS.items():
        dest = RAW / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            r = client.get(url)
            dest.write_bytes(r.content)
            sha = hashlib.sha256(r.content).hexdigest()[:16]
            ctype = (r.headers.get("content-type") or "?")[:50]
            print(f"OK {rel} status={r.status_code} bytes={len(r.content)} sha={sha} {ctype}")
        except Exception as e:
            print(f"FAIL {rel}: {type(e).__name__}: {e}")
        time.sleep(1.2)  # respectful rate
    client.close()


if __name__ == "__main__":
    main()

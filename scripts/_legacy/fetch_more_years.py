#!/usr/bin/env python3
"""Fetch additional multi-year fire policy / contingency PDFs."""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
UA = "GastoAbiertoBO/0.7 (+multi-year research)"

URLS = {
    "mindef/plan_nacional_contingencias_incendios_2022.pdf": (
        "https://www.mindef.gob.bo/sites/default/files/"
        "1.%20PLAN%20NACIONAL%20DE%20CONTINGENCIAS%20ANTE%20INCENDIOS%20FORESTALES%202022.pdf"
    ),
    "mindef/rpc_inicial_2022.pdf": (
        "https://www.mindef.gob.bo/wp-content/uploads/2026/01/"
        "RENDICION-DE-CUENTAS-INICIAL-2022.pdf"
    ),
    "planificacion/plan_prevencion_if_2026.pdf": (
        "https://www.planificacion.gob.bo/uploads/Plan_prevencion_IF_2026.pdf"
    ),
    # OCHA / ReliefWeb situation reports often cite official figures
    "ocha/bolivia_sitrep2_incendios_2024.pdf": (
        "https://reliefweb.int/attachments/c8f0e0e0-placeholder"  # will try alternates
    ),
}


def try_download(client: httpx.Client, rel: str, url: str) -> None:
    dest = RAW / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 5000:
        print(f"SKIP {rel}")
        return
    try:
        r = client.get(url)
        if r.status_code != 200 or len(r.content) < 5000 or b"%PDF" not in r.content[:20]:
            print(f"FAIL {rel} status={r.status_code} bytes={len(r.content)}")
            if dest.exists():
                dest.unlink()
            return
        dest.write_bytes(r.content)
        sha = hashlib.sha256(r.content).hexdigest()[:12]
        print(f"OK {rel} bytes={len(r.content)} sha={sha}")
    except Exception as e:
        print(f"ERR {rel}: {type(e).__name__}: {e}")


def main() -> None:
    # Skip broken placeholder
    urls = {k: v for k, v in URLS.items() if "placeholder" not in v}
    # ReliefWeb / OCHA HTML may have PDF — try known report pages via httpx later
    extra = {
        "mindef/plan_contingencias_alt.pdf": (
            "https://www.mindef.gob.bo/sites/default/files/"
            "1. PLAN NACIONAL DE CONTINGENCIAS ANTE INCENDIOS FORESTALES 2022.pdf"
        ),
    }
    client = httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=180)
    for rel, url in {**urls, **extra}.items():
        try_download(client, rel, url)
        time.sleep(1.0)

    # Probe MINDEF for older years via common naming
    probes = [
        ("mindef/rpc_final_2021.pdf", "https://www.mindef.gob.bo/wp-content/uploads/2026/01/Final_2021.pdf"),
        ("mindef/rpc_final_2020.pdf", "https://www.mindef.gob.bo/wp-content/uploads/2026/01/Final_2020.pdf"),
        ("mindef/rpc_final_2019.pdf", "https://www.mindef.gob.bo/wp-content/uploads/2026/01/Final_2019.pdf"),
        ("mindef/rpc_informe_2021.pdf", "https://www.mindef.gob.bo/wp-content/uploads/2026/01/informe21.pdf"),
        ("mindef/rpc_informe_2020.pdf", "https://www.mindef.gob.bo/wp-content/uploads/2026/01/informe20.pdf"),
        ("sernap/rpc_final_2022.pdf", "https://www.sernap.gob.bo/wp-content/uploads/2025/08/RPCSERNAP_FINAL_2022.pdf"),
        ("sernap/rpc_inicial_2023.pdf", "https://www.sernap.gob.bo/wp-content/uploads/2025/08/RPCSERNAP_INCIAL_2023.pdf"),
        ("sernap/rpc_final_2021.pdf", "https://www.sernap.gob.bo/wp-content/uploads/2025/08/PresentacionRendicionCuentasFinal2021-1.pdf"),
        ("sernap/rpc_final_2020.pdf", "https://www.sernap.gob.bo/wp-content/uploads/2025/08/acta-de-rendicion-publica-de-cuentas-del-sernap-final-gestion-2020.pdf"),
    ]
    for rel, url in probes:
        try_download(client, rel, url)
        time.sleep(1.0)
    client.close()


if __name__ == "__main__":
    main()

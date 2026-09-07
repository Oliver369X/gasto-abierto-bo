#!/usr/bin/env python3
"""Download linked official PDFs discovered from index pages."""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
UA = "GastoAbiertoBO/0.6 (+research; respectful crawler)"

PDFS = {
    # MINDEF RPC multi-year
    "mindef/rpc_inicial_2024.pdf": "https://www.mindef.gob.bo/wp-content/uploads/2026/01/Inicial_2024.pdf",
    "mindef/rpc_final_2023.pdf": "https://www.mindef.gob.bo/wp-content/uploads/2026/01/Final_2023.pdf",
    "mindef/rpc_informe_2023.pdf": "https://www.mindef.gob.bo/wp-content/uploads/2026/01/informe23.pdf",
    "mindef/rpc_inicial_2025.pdf": "https://www.mindef.gob.bo/wp-content/uploads/2025/05/09042025_INFORME_RPCInicial_2025_V4.pdf",
    "mindef/rpc_final_2025.pdf": "https://www.mindef.gob.bo/wp-content/uploads/2026/04/INFORME_RPCFinal_2025-V07.pdf",
    "mindef/rpc_final_2022.pdf": "https://www.mindef.gob.bo/wp-content/uploads/2026/01/RENDICION-DE-CUENTAS-FINAL-2022.pdf",
    "mindef/ejecucion_presup_da_2025.pdf": "https://www.mindef.gob.bo/wp-content/uploads/2026/01/EJECUCION-PRESUPUESTARIA-POR-D.A.-2025.pdf",
    "mindef/ejecucion_presup_grupo_2025.pdf": "https://www.mindef.gob.bo/wp-content/uploads/2026/01/EJECUCION-PRESUPUESATRIA-PRO-GRUPO-DE-GASTO-2025.pdf",
    # ABT
    "abt/plan_accion_gestion_fuego.pdf": "https://www.abt.gob.bo/images/2023/07/planacciongestionfuego.pdf",
    # SERNAP
    "sernap/rpc_final_2024.pdf": "https://www.sernap.gob.bo/wp-content/uploads/2025/08/rpcf2024.pdf",
    "sernap/rpc_inicial_2025.pdf": "https://www.sernap.gob.bo/wp-content/uploads/2025/08/rpci2025.pdf",
    "sernap/rpc_final_2023.pdf": "https://www.sernap.gob.bo/wp-content/uploads/2025/08/rpcf2023_uc.pdf",
    "sernap/fuego_activo_aps_2025-09-15.pdf": "https://www.sernap.gob.bo/wp-content/uploads/2025/09/FUEGO-ACTIVO-EN-APs-AL-15.09.2025.pdf",
}


def main() -> None:
    client = httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=180.0)
    for rel, url in PDFS.items():
        dest = RAW / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.stat().st_size > 10_000:
            sha = hashlib.sha256(dest.read_bytes()).hexdigest()[:16]
            print(f"SKIP {rel} exists bytes={dest.stat().st_size} sha={sha}")
            continue
        try:
            r = client.get(url)
            dest.write_bytes(r.content)
            sha = hashlib.sha256(r.content).hexdigest()[:16]
            ctype = (r.headers.get("content-type") or "?")[:40]
            print(f"OK {rel} status={r.status_code} bytes={len(r.content)} sha={sha} {ctype}")
        except Exception as e:
            print(f"FAIL {rel}: {type(e).__name__}: {e}")
        time.sleep(1.5)
    client.close()


if __name__ == "__main__":
    main()

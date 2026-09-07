"""Unified open-data fetcher for tests/fixtures/real/.

Public CKAN / OCP downloads — no LIVE_SCRAPE gate.
"""
from __future__ import annotations

import csv
import io
import json
import re
import tarfile
import zipfile
from pathlib import Path
from typing import Iterable

import httpx

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "tests" / "fixtures" / "real"
UA = "GastoAbiertoBO/0.8 (+research; open-data mirror)"

# Union of known URLs from former download_real_sources + fetch_real_sources
CKAN_RESOURCES: list[tuple[str, str, str]] = [
    (
        "agetic",
        "sicoes_ocp_2019.csv",
        "https://datos.gob.bo/dataset/c0d87e59-2cd7-412f-b431-75454d383659/resource/4526c3bc-3d6a-45b5-ade9-db0942db39b0/download/sicoes_ocp_2019.csv",
    ),
    (
        "agetic",
        "sicoes_ocp_2019_ocds_releases.csv",
        "https://datos.gob.bo/dataset/c0d87e59-2cd7-412f-b431-75454d383659/resource/be665deb-828f-41a0-a104-c34817cd9def/download/sicoes_ocp_2019_ocds-releases-2.csv",
    ),
]

OCP_CANDIDATES = [
    "https://data.open-contracting.org/media/bolivia-agetic/all.jsonl.gz",
    "https://data.open-contracting.org/media/bolivia/agetic/all.jsonl.gz",
    "https://data.open-contracting.org/media/publications/20/all.jsonl.gz",
    "https://data.open-contracting.org/en/publication/20/download/jsonl/all",
    "https://data.open-contracting.org/en/publication/20/download/csv/all",
]

KNOWN_PACKAGE_IDS = ["contrataciones-agetic-2019-estandar-ocp"]


def list_urls() -> list[str]:
    urls = [u for _, _, u in CKAN_RESOURCES]
    urls.extend(OCP_CANDIDATES)
    return list(dict.fromkeys(urls))


def _client() -> httpx.Client:
    return httpx.Client(timeout=120, follow_redirects=True, headers={"User-Agent": UA})


def _download(c: httpx.Client, url: str, dest: Path, *, force: bool) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 100 and not force:
        return True
    print(f"GET {url}")
    try:
        with c.stream("GET", url) as r:
            if r.status_code >= 400:
                print(f"  skip HTTP {r.status_code}")
                return False
            tmp = dest.with_suffix(dest.suffix + ".part")
            with tmp.open("wb") as f:
                for chunk in r.iter_bytes(1 << 16):
                    f.write(chunk)
            tmp.replace(dest)
        print(f"  -> {dest} ({dest.stat().st_size} bytes)")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL {exc}")
        return False


def normalize_sicoes_csv(raw: bytes, out_csv: Path) -> int:
    text = raw.decode("utf-8-sig", errors="replace")
    sample = text[:4096]
    delim = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    if not reader.fieldnames:
        return 0

    def pick(row: dict, *cands: str) -> str:
        lower = {k.lower().strip(): v for k, v in row.items() if k}
        for c in cands:
            for k, v in lower.items():
                if c in k and v:
                    return str(v).strip()
        return ""

    rows_out = []
    for row in reader:
        cuce = pick(row, "cuce", "ocid", "idproceso", "id_proceso", "codigo", "release")
        entity = pick(row, "entidad", "buyer", "institucion", "organismo", "entity")
        supplier = pick(row, "proveedor", "supplier", "adjudicatario", "empresa")
        desc = pick(row, "objeto", "description", "titulo", "title", "descripcion")
        amount = pick(row, "monto", "amount", "valor", "precio", "value")
        modality = pick(row, "modalidad", "modality", "procedimiento")
        date = pick(row, "fecha", "date", "awarddate", "contractdate", "publicado")
        status = pick(row, "estado", "status")
        if not cuce and not entity:
            continue
        rows_out.append(
            {
                "cuce": cuce or None,
                "entity": entity or "Entidad desconocida",
                "supplier": supplier or None,
                "description": desc or None,
                "amount": amount or None,
                "modality": modality or None,
                "date": date or None,
                "status": status or None,
                "source_note": "datos.gob.bo/agetic",
            }
        )
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "cuce",
                "entity",
                "supplier",
                "description",
                "amount",
                "modality",
                "date",
                "status",
                "source_note",
            ],
        )
        w.writeheader()
        w.writerows(rows_out)
    return len(rows_out)


def fetch_packages(dest: Path | None = None, *, force: bool = False) -> list[Path]:
    """Download known packages + OCP candidates into dest. Returns written paths."""
    out = dest or DEFAULT_OUT
    out.mkdir(parents=True, exist_ok=True)
    wrote: list[Path] = []
    meta: dict = {"downloads": [], "normalized_rows": 0}
    with _client() as c:
        for source, fname, url in CKAN_RESOURCES:
            path = out / source / fname
            ok = _download(c, url, path, force=force)
            meta["downloads"].append({"url": url, "ok": ok, "path": str(path)})
            if ok:
                wrote.append(path)
                if fname.endswith(".csv"):
                    norm = out / "agetic" / f"normalized_{fname}"
                    n = normalize_sicoes_csv(path.read_bytes(), norm)
                    meta["normalized_rows"] += n
                    if n:
                        wrote.append(norm)

        for u in OCP_CANDIDATES:
            fname = re.sub(r"[^\w.\-]+", "_", u.split("/")[-1] or "ocp.bin")[:100]
            if not Path(fname).suffix:
                fname += ".bin"
            path = out / "ocp_agetic" / fname
            ok = _download(c, u, path, force=force)
            meta["downloads"].append({"url": u, "ok": ok, "path": str(path)})
            if ok:
                wrote.append(path)

    (out / "download_manifest.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return wrote


def fetch_packages_list_only() -> Iterable[str]:
    return list_urls()

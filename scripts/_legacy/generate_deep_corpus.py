#!/usr/bin/env python3
"""Generate deep multi-year, multi-source fixtures for offline production-like data.

Produces overlapping CUCEs across AGETIC/SICOES, rich presupuesto series,
and CGE audit listings — so cross-source contrast works without live scrape.

  python scripts/generate_deep_corpus.py
"""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
RNG = random.Random(42)

ENTITIES = [
    ("Ministerio de Educación", "nacional", "La Paz"),
    ("Ministerio de Salud", "nacional", "La Paz"),
    ("Ministerio de Obras Públicas", "nacional", "La Paz"),
    ("Ministerio de Defensa", "nacional", "La Paz"),
    ("GAD Santa Cruz", "departamental", "Santa Cruz"),
    ("GAD La Paz", "departamental", "La Paz"),
    ("GAD Cochabamba", "departamental", "Cochabamba"),
    ("GAM Santa Cruz de la Sierra", "municipal", "Santa Cruz"),
    ("GAM La Paz", "municipal", "La Paz"),
    ("GAM Cochabamba", "municipal", "Cochabamba"),
    ("GAM El Alto", "municipal", "La Paz"),
    ("YPFB", "empresa_publica", "La Paz"),
]

SUPPLIERS = [
    "Constructora Andes S.R.L.",
    "Servicios Integrales SA",
    "Insumos Médicos Bolivia SA",
    "Vialidad Sur SRL",
    "Tecnología Andina S.R.L.",
    "Editorial Escolar BO",
    "AeroServicios BO",
    "Bomberos Contract Ltda.",
]

MODALITIES = [
    "Licitación Pública",
    "Contratación Menor",
    "Adjudicación Directa",
    "ANPE",
]

OBJECTS = [
    "Construcción de aulas",
    "Equipamiento hospitalario",
    "Pavimentación vial",
    "Servicio de limpieza",
    "Consultoría POA",
    "Ambulancias",
    "Textos escolares",
    "Alcantarillado",
    "Alquiler de aeronaves",
    "Equipos contra incendios",
    "Señalización vial",
    "Laboratorios informáticos",
    "Reactivos laboratorio",
    "Remodelación mercado",
    "Mantenimiento rutas",
]


def _cuce(year: int, seq: int) -> str:
    # Distinct prefix so deep corpus never collides with bootstrap OCDS-* seeds
    return f"GA-DEEP-{year}-{seq:04d}"


def write_agetic_deep() -> int:
    path = FIX / "agetic" / "deep" / "contracts_2019_2025_deep.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    seq = 1
    for year in range(2019, 2026):
        for _ in range(18):  # ~126 contracts
            ent, _level, dept = RNG.choice(ENTITIES)
            obj = RNG.choice(OBJECTS)
            amount = round(RNG.uniform(80_000, 9_500_000), 2)
            rows.append(
                {
                    "cuce": _cuce(year, seq),
                    "entity": ent,
                    "supplier": RNG.choice(SUPPLIERS),
                    "description": f"{obj} {year}",
                    "amount": f"{amount:.2f}",
                    "modality": RNG.choice(MODALITIES),
                    "date": f"{year}-{RNG.randint(1,12):02d}-{RNG.randint(1,28):02d}",
                    "status": "complete",
                    "year": year,
                    "department": dept,
                }
            )
            seq += 1
    with path.open("w", encoding="utf-8", newline="") as f:
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
                "year",
                "department",
            ],
        )
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def write_sicoes_overlap(agetic_rows: int) -> int:
    """SICOES mirror of a subset with deliberate amount drift for discrepancies."""
    agetic_path = FIX / "agetic" / "deep" / "contracts_2019_2025_deep.csv"
    out_dir = FIX / "sicoes" / "deep"
    out_dir.mkdir(parents=True, exist_ok=True)
    with agetic_path.open(encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))
    # ~35% overlap with ±5–20% amount delta
    sample = [r for i, r in enumerate(all_rows) if i % 3 == 0]
    pages: list[list[dict]] = [sample[i : i + 25] for i in range(0, len(sample), 25)]
    total = 0
    for page_idx, page in enumerate(pages, start=1):
        path = out_dir / f"contracts_page_{page_idx:02d}.csv"
        out_rows = []
        for r in page:
            base = float(r["amount"])
            factor = 1.0 + RNG.uniform(-0.05, 0.22)
            out_rows.append(
                {
                    "cuce": r["cuce"],
                    "entity": r["entity"],
                    "supplier": r["supplier"],
                    "description": f"{r['description']} (SICOES)",
                    "amount": f"{base * factor:.2f}",
                    "modality": r["modality"],
                    "date": r["date"],
                    "status": r["status"],
                    "department": r.get("department", ""),
                }
            )
        with path.open("w", encoding="utf-8", newline="") as f:
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
                    "department",
                ],
            )
            w.writeheader()
            w.writerows(out_rows)
        total += len(out_rows)
        # Also HTML page for parser path coverage
        html = out_dir / f"procesos_page_{page_idx:02d}.html"
        html.write_text(_html_table(out_rows), encoding="utf-8")
    return total


def _html_table(rows: list[dict]) -> str:
    body = []
    for r in rows:
        body.append(
            "<tr>"
            f"<td>{r['cuce']}</td><td>{r['cuce']}</td><td>{r['entity']}</td>"
            f"<td>{r['modality']}</td><td>{r['description']}</td>"
            f"<td>{r['date']}</td><td>{r['supplier']}</td><td>{r['amount']}</td>"
            f"<td>{r['status']}</td>"
            "</tr>"
        )
    return (
        "<html><body><table class='resultados'>"
        "<tr><th>#</th><th>CUCE</th><th>Entidad</th><th>Modalidad</th>"
        "<th>Objeto</th><th>Fecha</th><th>Proveedor</th><th>Monto</th><th>Estado</th></tr>"
        + "".join(body)
        + "</table></body></html>"
    )


def write_presupuesto_deep() -> int:
    path = FIX / "presupuesto_abierto" / "deep" / "history_entities_2019_2025.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    series = []
    for year in range(2019, 2026):
        for ent, level, dept in ENTITIES:
            vigente = RNG.uniform(5_000_000, 120_000_000)
            inicial = vigente * RNG.uniform(0.85, 1.0)
            ejec = vigente * RNG.uniform(0.35, 0.95)
            series.append(
                {
                    "entidad": ent,
                    "nivel": level,
                    "departamento": dept,
                    "gestion": year,
                    "presupuesto_inicial": f"{inicial:.2f}",
                    "presupuesto_vigente": f"{vigente:.2f}",
                    "ejecucion": f"{ejec:.2f}",
                }
            )
    path.write_text(
        json.dumps({"series": series}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(series)


def write_cge_deep() -> int:
    path = FIX / "cge" / "deep" / "informes_2019_2025.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    links = []
    n = 0
    for year in range(2019, 2026):
        for i, (ent, _, _) in enumerate(ENTITIES[:8], start=1):
            n += 1
            title = f"Informe de auditoría {ent} gestión {year} N° {i}"
            href = f"https://www.contraloria.gob.bo/informes/{year}/{n:04d}.pdf"
            links.append(f'<a href="{href}">{title}</a>')
    path.write_text(
        "<html><body><h1>Informes públicos</h1>" + "\n".join(links) + "</body></html>",
        encoding="utf-8",
    )
    return n


def main() -> None:
    n_a = write_agetic_deep()
    n_s = write_sicoes_overlap(n_a)
    n_p = write_presupuesto_deep()
    n_c = write_cge_deep()
    print(
        json.dumps(
            {
                "agetic_contracts": n_a,
                "sicoes_overlap": n_s,
                "presupuesto_rows": n_p,
                "cge_audits": n_c,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

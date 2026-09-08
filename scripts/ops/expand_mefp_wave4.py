#!/usr/bin/env python3
"""Merge Wave 4 MEFP ubicaciones into packages/common/data/mefp_ubicaciones.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "packages" / "common" / "data" / "mefp_ubicaciones.json"

# Curated municipalities toward official 352 (Wave 4: 60 → 115+).
WAVE4_MUNICIPAL = [
    ("Laja", "La Paz", ["Laja", "gam laja"]),
    ("Pucarani", "La Paz", ["Pucarani", "pucarani", "gam pucarani"]),
    ("Guaqui", "La Paz", ["Guaqui", "guaqui"]),
    ("Chulumani", "La Paz", ["Chulumani", "chulumani", "gam chulumani"]),
    ("Copacabana", "La Paz", ["Copacabana", "copacabana"]),
    ("Desaguadero", "La Paz", ["Desaguadero", "desaguadero"]),
    ("Palca", "La Paz", ["Palca", "palca"]),
    ("Achacachi", "La Paz", ["Achacachi", "achacachi", "gam achacachi"]),
    ("Sorata", "La Paz", ["Sorata", "sorata"]),
    ("Vallegrande", "Santa Cruz", ["Vallegrande", "vallegrande", "gam vallegrande"]),
    ("Samaipata", "Santa Cruz", ["Samaipata", "samaipata"]),
    ("Charagua", "Santa Cruz", ["Charagua", "charagua", "gam charagua"]),
    ("Puerto Quijarro", "Santa Cruz", ["Puerto Quijarro", "puerto quijarro"]),
    ("San Carlos", "Santa Cruz", ["San Carlos", "san carlos", "gam san carlos"]),
    ("El Torno", "Santa Cruz", ["El Torno", "el torno", "gam el torno"]),
    ("Portachuelo", "Santa Cruz", ["Portachuelo", "portachuelo"]),
    ("Pailón", "Santa Cruz", ["Pailón", "pailon", "pailón"]),
    ("Comarapa", "Santa Cruz", ["Comarapa", "comarapa"]),
    ("Saipina", "Santa Cruz", ["Saipina", "saipina"]),
    ("Mineros", "Santa Cruz", ["Mineros", "mineros", "gam mineros"]),
    ("Aiquile", "Cochabamba", ["Aiquile", "aiquile"]),
    ("Tapacarí", "Cochabamba", ["Tapacarí", "tapacari", "tapacarí"]),
    ("Cliza", "Cochabamba", ["Cliza", "cliza", "gam cliza"]),
    ("Sipe Sipe", "Cochabamba", ["Sipe Sipe", "sipe sipe"]),
    ("Villa Tunari", "Cochabamba", ["Villa Tunari", "villa tunari"]),
    ("Tarata", "Cochabamba", ["Tarata", "tarata"]),
    ("Arbieto", "Cochabamba", ["Arbieto", "arbieto"]),
    ("Capinota", "Cochabamba", ["Capinota", "capinota"]),
    ("Poopó", "Oruro", ["Poopó", "poopo", "poopó"]),
    ("Carangas", "Oruro", ["Carangas", "carangas"]),
    ("Huayllamarca", "Oruro", ["Huayllamarca", "huayllamarca"]),
    ("Eucaliptus", "Oruro", ["Eucaliptus", "eucaliptus"]),
    ("Toledo", "Oruro", ["Toledo", "toledo", "gam toledo"]),
    ("Tupiza", "Potosí", ["Tupiza", "tupiza", "gam tupiza"]),
    ("Colcha K", "Potosí", ["Colcha K", "colcha k", "colcha"]),
    ("San Pedro de Quemes", "Potosí", ["San Pedro de Quemes", "san pedro de quemes"]),
    ("Cotagaita", "Potosí", ["Cotagaita", "cotagaita"]),
    ("Uncía", "Potosí", ["Uncía", "uncia", "uncía"]),
    ("Llallagua", "Potosí", ["Llallagua", "llallagua"]),
    ("Tarabuco", "Chuquisaca", ["Tarabuco", "tarabuco", "gam tarabuco"]),
    ("Villa Serrano", "Chuquisaca", ["Villa Serrano", "villa serrano"]),
    ("Padilla", "Chuquisaca", ["Padilla", "padilla"]),
    ("Nor Cinti", "Chuquisaca", ["Nor Cinti", "nor cinti"]),
    ("Zudáñez", "Chuquisaca", ["Zudáñez", "zudanez", "zudáñez"]),
    ("Yamparáez", "Chuquisaca", ["Yamparáez", "yamparaez"]),
    ("Erquis", "Tarija", ["Erquis", "erquis"]),
    ("Padcaya", "Tarija", ["Padcaya", "padcaya"]),
    ("Caraparí", "Tarija", ["Caraparí", "carapari", "caraparí"]),
    ("Rurrenabaiba", "Beni", ["Rurrenabaiba", "rurrenabaiba", "rurre"]),
    ("Reyes", "Beni", ["Reyes", "reyes", "gam reyes"]),
    ("Santa Ana del Yacuma", "Beni", ["Santa Ana del Yacuma", "santa ana del yacuma"]),
    ("Baures", "Beni", ["Baures", "baures"]),
    ("San Andrés", "Beni", ["San Andrés", "san andres", "san andrés"]),
    ("San Lorenzo", "Pando", ["San Lorenzo", "san lorenzo", "gam san lorenzo"]),
    ("Filadelfia", "Pando", ["Filadelfia", "filadelfia"]),
    ("Bolpebra", "Pando", ["Bolpebra", "bolpebra"]),
    ("Nuevo Manoa", "Pando", ["Nuevo Manoa", "nuevo manoa"]),
    ("San Borja", "Beni", []),  # dedupe guard below
]


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    existing = {u["name"].lower() for u in data["ubicaciones"]}
    start = max(int(u["code"][1:]) for u in data["ubicaciones"] if u["code"].startswith("M")) + 1
    added = 0
    code = start
    for name, dept, aliases in WAVE4_MUNICIPAL:
        if name.lower() in existing:
            continue
        base_aliases = list(dict.fromkeys([name, *aliases]))
        data["ubicaciones"].append(
            {
                "code": f"M{code:03d}",
                "name": name,
                "department": dept,
                "level": "municipal",
                "aliases": base_aliases,
            }
        )
        existing.add(name.lower())
        code += 1
        added += 1

    data["version"] = "2025-wave4-incremental"
    data["count"] = len(data["ubicaciones"])
    data["note"] = (
        f"Wave 4 incremental set ({data['count']} ubicaciones). "
        "Merge official MEFP GeoPackage export to reach 352."
    )
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Added {added} municipios; total={data['count']}")


if __name__ == "__main__":
    main()

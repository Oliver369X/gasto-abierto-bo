#!/usr/bin/env python3
"""Merge Wave 5 MEFP ubicaciones into packages/common/data/mefp_ubicaciones.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "packages" / "common" / "data" / "mefp_ubicaciones.json"

# Curated municipios toward official 352 (Wave 5: 117 → ~160).
WAVE5_MUNICIPAL = [
    ("Coripata", "La Paz", ["Coripata", "coripata", "gam coripata"]),
    ("Irupana", "La Paz", ["Irupana", "irupana"]),
    ("Combaya", "La Paz", ["Combaya", "combaya"]),
    ("Mecapaca", "La Paz", ["Mecapaca", "mecapaca"]),
    ("Batallas", "La Paz", ["Batallas", "batallas"]),
    ("Santiago de Machaca", "La Paz", ["Santiago de Machaca", "santiago de machaca"]),
    ("Curva", "La Paz", ["Curva", "curva"]),
    ("Palos Blancos", "La Paz", ["Palos Blancos", "palos blancos"]),
    ("San Javier", "Santa Cruz", ["San Javier", "san javier", "gam san javier"]),
    ("San Miguel de Velasco", "Santa Cruz", ["San Miguel de Velasco", "san miguel de velasco"]),
    ("Gutierrez", "Santa Cruz", ["Gutierrez", "gutierrez", "gam gutierrez"]),
    ("Saavedra", "Santa Cruz", ["Saavedra", "saavedra"]),
    ("Cabezas", "Santa Cruz", ["Cabezas", "cabezas"]),
    ("Lagunillas", "Santa Cruz", ["Lagunillas", "lagunillas"]),
    ("Huacaya", "Santa Cruz", ["Huacaya", "huacaya"]),
    ("Boyuibe", "Santa Cruz", ["Boyuibe", "boyuibe"]),
    ("San Antonio de Lomerío", "Santa Cruz", ["San Antonio de Lomerío", "san antonio de lomerio"]),
    ("Tacopaya", "Cochabamba", ["Tacopaya", "tacopaya"]),
    ("Omereque", "Cochabamba", ["Omereque", "omereque"]),
    ("Pojo", "Cochabamba", ["Pojo", "pojo"]),
    ("Villa Rivero", "Cochabamba", ["Villa Rivero", "villa rivero"]),
    ("Alalay", "Cochabamba", ["Alalay", "alalay"]),
    ("Pasorapa", "Cochabamba", ["Pasorapa", "pasorapa"]),
    ("Independencia", "Cochabamba", ["Independencia", "independencia"]),
    ("Machacamarca", "Oruro", ["Machacamarca", "machacamarca"]),
    ("Challacollo", "Oruro", ["Challacollo", "challacollo"]),
    ("Pazña", "Oruro", ["Pazña", "pazna", "pazña"]),
    ("Colquechaca", "Potosí", ["Colquechaca", "colquechaca"]),
    ("Betanzos", "Potosí", ["Betanzos", "betanzos"]),
    ("Ocurí", "Potosí", ["Ocurí", "ocuri", "ocurí"]),
    ("Pocoata", "Potosí", ["Pocoata", "pocoata"]),
    ("Sacaca", "Potosí", ["Sacaca", "sacaca"]),
    ("Presto", "Chuquisaca", ["Presto", "presto"]),
    ("Icla", "Chuquisaca", ["Icla", "icla"]),
    ("Tomina", "Chuquisaca", ["Tomina", "tomina"]),
    ("Sopachuy", "Chuquisaca", ["Sopachuy", "sopachuy"]),
    ("Entre Ríos", "Tarija", ["Entre Ríos", "entre rios", "entre ríos"]),
    ("Uriondo", "Tarija", ["Uriondo", "uriondo"]),
    ("El Puente", "Tarija", ["El Puente", "el puente"]),
    ("Yuncleras", "Tarija", ["Yuncleras", "yuncleras"]),
    ("Exaltación", "Beni", ["Exaltación", "exaltacion", "exaltación"]),
    ("Loreto", "Beni", ["Loreto", "loreto", "gam loreto"]),
    ("San Ramón", "Beni", ["San Ramón", "san ramon", "san ramón"]),
    ("Huacaraje", "Beni", ["Huacaraje", "huacaraje"]),
    ("Nueva Esperanza", "Pando", ["Nueva Esperanza", "nueva esperanza"]),
    ("Ingavi", "La Paz", ["Ingavi", "ingavi"]),
    ("Luribay", "La Paz", ["Luribay", "luribay"]),
    ("Sapahaqui", "La Paz", ["Sapahaqui", "sapahaqui"]),
    ("Cairoma", "La Paz", ["Cairoma", "cairoma"]),
]


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    existing = {u["name"].lower() for u in data["ubicaciones"]}
    m_codes = [u for u in data["ubicaciones"] if u["code"].startswith("M")]
    start = max(int(u["code"][1:]) for u in m_codes) + 1 if m_codes else 1
    added = 0
    code = start
    for name, dept, aliases in WAVE5_MUNICIPAL:
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

    data["version"] = "2025-wave5-incremental"
    data["count"] = len(data["ubicaciones"])
    data["note"] = (
        f"Wave 5 incremental set ({data['count']} ubicaciones). "
        "Merge official MEFP GeoPackage export to reach 352 — see docs/sources/mefp_ubicaciones.md."
    )
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Added {added} municipios; total={data['count']}")


if __name__ == "__main__":
    main()

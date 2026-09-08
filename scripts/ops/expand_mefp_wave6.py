#!/usr/bin/env python3
"""Merge Wave 6 MEFP ubicaciones into packages/common/data/mefp_ubicaciones.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "packages" / "common" / "data" / "mefp_ubicaciones.json"

# Curated municipios toward official 352 (Wave 6: 166 → 200+).
WAVE6_MUNICIPAL = [
    ("Ancoraimes", "La Paz", ["Ancoraimes", "ancoraimes", "gam ancoraimes"]),
    ("Apolo", "La Paz", ["Apolo", "apolo"]),
    ("Calamarca", "La Paz", ["Calamarca", "calamarca"]),
    ("Catacora", "La Paz", ["Catacora", "catacora"]),
    ("Charaña", "La Paz", ["Charaña", "charana", "charaña"]),
    ("Ixiamas", "La Paz", ["Ixiamas", "ixiamas"]),
    ("Tipuani", "La Paz", ["Tipuani", "tipuani"]),
    ("Umala", "La Paz", ["Umala", "umala"]),
    ("Waldo Ballivián", "La Paz", ["Waldo Ballivián", "waldo ballivian", "waldo ballivián"]),
    ("Teoponte", "La Paz", ["Teoponte", "teoponte"]),
    ("Okinawa", "Santa Cruz", ["Okinawa", "okinawa"]),
    ("Puerto Busch", "Santa Cruz", ["Puerto Busch", "puerto busch"]),
    ("El Carmen Rivero Tórrez", "Santa Cruz", ["El Carmen Rivero Tórrez", "el carmen rivero torrez"]),
    ("Cuatro Cañadas", "Santa Cruz", ["Cuatro Cañadas", "cuatro canadas", "cuatro cañadas"]),
    ("San Pedro", "Santa Cruz", ["San Pedro", "san pedro", "gam san pedro"]),
    ("San Rafael de Velasco", "Santa Cruz", ["San Rafael de Velasco", "san rafael de velasco"]),
    ("San Antonio de Parapetí", "Santa Cruz", ["San Antonio de Parapetí", "san antonio de parapeti"]),
    ("Postrervalle", "Santa Cruz", ["Postrervalle", "postrervalle"]),
    ("Colomi", "Cochabamba", ["Colomi", "colomi"]),
    ("Morochata", "Cochabamba", ["Morochata", "morochata"]),
    ("Chimoré", "Cochabamba", ["Chimoré", "chimore", "chimoré"]),
    ("Totora", "Cochabamba", ["Totora", "totora"]),
    ("Caripuyo", "Oruro", ["Caripuyo", "caripuyo"]),
    ("Chipaya", "Oruro", ["Chipaya", "chipaya"]),
    ("Corque", "Oruro", ["Corque", "corque"]),
    ("General Saavedra", "Oruro", ["General Saavedra", "general saavedra"]),
    ("Nor Carangas", "Oruro", ["Nor Carangas", "nor carangas"]),
    ("Pampa Aullagas", "Oruro", ["Pampa Aullagas", "pampa aullagas"]),
    ("Quillacas", "Oruro", ["Quillacas", "quillacas"]),
    ("Sabaya", "Oruro", ["Sabaya", "sabaya"]),
    ("Santiago de Huari", "Oruro", ["Santiago de Huari", "santiago de huari"]),
    ("Atocha", "Potosí", ["Atocha", "atocha"]),
    ("Chayanta", "Potosí", ["Chayanta", "chayanta"]),
    ("Colchani", "Potosí", ["Colchani", "colchani"]),
    ("Llica", "Potosí", ["Llica", "llica"]),
    ("Nor Chichas", "Potosí", ["Nor Chichas", "nor chichas"]),
    ("San Pablo de Lípez", "Potosí", ["San Pablo de Lípez", "san pablo de lopez", "san pablo de lípez"]),
    ("Vitichi", "Potosí", ["Vitichi", "vitichi"]),
    ("Alcalá", "Chuquisaca", ["Alcalá", "alcala", "alcalá"]),
    ("Culpina", "Chuquisaca", ["Culpina", "culpina"]),
    ("Huacareta", "Chuquisaca", ["Huacareta", "huacareta"]),
    ("Macharetí", "Chuquisaca", ["Macharetí", "machareti", "macharetí"]),
    ("Mojocoya", "Chuquisaca", ["Mojocoya", "mojocoya"]),
    ("Poroma", "Chuquisaca", ["Poroma", "poroma"]),
    ("Ravelo", "Chuquisaca", ["Ravelo", "ravelo"]),
    ("San Lucas", "Chuquisaca", ["San Lucas", "san lucas"]),
    ("Vocas", "Chuquisaca", ["Vocas", "vocas"]),
    ("Avilés", "Tarija", ["Avilés", "aviles", "avilés"]),
    ("Barrancas", "Tarija", ["Barrancas", "barrancas"]),
    ("Emborozu", "Tarija", ["Emborozu", "emborozu"]),
    ("La Tablada", "Tarija", ["La Tablada", "la tablada"]),
    ("Cachuela Esperanza", "Beni", ["Cachuela Esperanza", "cachuela esperanza"]),
    ("Río Verde", "Beni", ["Río Verde", "rio verde", "río verde"]),
    ("San Joaquín", "Beni", ["San Joaquín", "san joaquin", "san joaquín"]),
    ("San Nicolás", "Beni", ["San Nicolás", "san nicolas", "san nicolás"]),
    ("Santa Rosa del Yacuma", "Beni", ["Santa Rosa del Yacuma", "santa rosa del yacuma"]),
    ("Evangelista", "Pando", ["Evangelista", "evangelista"]),
    ("Santa Rosa de Abuna", "Pando", ["Santa Rosa de Abuna", "santa rosa de abuna"]),
]


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    existing = {u["name"].lower() for u in data["ubicaciones"]}
    m_codes = [u for u in data["ubicaciones"] if u["code"].startswith("M")]
    start = max(int(u["code"][1:]) for u in m_codes) + 1 if m_codes else 1
    added = 0
    code = start
    for name, dept, aliases in WAVE6_MUNICIPAL:
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

    data["version"] = "2025-wave6-incremental"
    data["count"] = len(data["ubicaciones"])
    data["note"] = (
        f"Wave 6 incremental set ({data['count']} ubicaciones). "
        "Merge official MEFP GeoPackage export to reach 352 — see docs/sources/mefp_ubicaciones.md."
    )
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Added {added} municipios; total={data['count']}")


if __name__ == "__main__":
    main()

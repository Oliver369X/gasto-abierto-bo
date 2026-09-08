#!/usr/bin/env python3
"""Merge Wave 7 MEFP ubicaciones into packages/common/data/mefp_ubicaciones.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "packages" / "common" / "data" / "mefp_ubicaciones.json"

# Curated municipios toward official 352 (Wave 7: 224 → 280+).
WAVE7_MUNICIPAL = [
    ("La Asunta", "La Paz", ["La Asunta", "la asunta", "gam la asunta"]),
    ("San Buenaventura", "La Paz", ["San Buenaventura", "san buenaventura"]),
    (
        "General José Manuel Pando",
        "La Paz",
        ["General José Manuel Pando", "general jose manuel pando", "gam pando"],
    ),
    ("Puerto Acosta", "La Paz", ["Puerto Acosta", "puerto acosta"]),
    ("Santiago de Huata", "La Paz", ["Santiago de Huata", "santiago de huata"]),
    ("Tacacoma", "La Paz", ["Tacacoma", "tacacoma"]),
    ("Guanay", "La Paz", ["Guanay", "guanay"]),
    ("Mapiri", "La Paz", ["Mapiri", "mapiri"]),
    ("Yaco", "La Paz", ["Yaco", "yaco"]),
    ("Nazacara de Pacajes", "La Paz", ["Nazacara de Pacajes", "nazacara de pacajes", "nazacara"]),
    ("Corocoro", "La Paz", ["Corocoro", "corocoro"]),
    ("Caquiaviri", "La Paz", ["Caquiaviri", "caquiaviri"]),
    ("Colquencha", "La Paz", ["Colquencha", "colquencha"]),
    ("Jesús de Machaca", "La Paz", ["Jesús de Machaca", "jesus de machaca"]),
    ("Pelechuco", "La Paz", ["Pelechuco", "pelechuco"]),
    ("Quiabaya", "La Paz", ["Quiabaya", "quiabaya"]),
    ("Sica Sica", "La Paz", ["Sica Sica", "sica sica"]),
    ("Wari", "La Paz", ["Wari", "wari"]),
    ("Chacarilla", "La Paz", ["Chacarilla", "chacarilla"]),
    ("Collana", "La Paz", ["Collana", "collana"]),
    ("La Guardia", "Santa Cruz", ["La Guardia", "la guardia", "gam la guardia"]),
    ("Paurito", "Santa Cruz", ["Paurito", "paurito"]),
    ("Rosario de Yacuma", "Beni", ["Rosario de Yacuma", "rosario de yacuma"]),
    ("Sacabamba", "Cochabamba", ["Sacabamba", "sacabamba"]),
    ("Shinahota", "Cochabamba", ["Shinahota", "shinahota"]),
    ("Tiraque", "Cochabamba", ["Tiraque", "tiraque"]),
    ("Vacas", "Cochabamba", ["Vacas", "vacas"]),
    ("Pocona", "Cochabamba", ["Pocona", "pocona"]),
    ("Anzaldo", "Cochabamba", ["Anzaldo", "anzaldo"]),
    ("Arque", "Cochabamba", ["Arque", "arque"]),
    ("Bolívar", "Cochabamba", ["Bolívar", "bolivar", "bolívar"]),
    ("Arani", "Cochabamba", ["Arani", "arani"]),
    ("Ayopaya", "Cochabamba", ["Ayopaya", "ayopaya"]),
    ("España", "Cochabamba", ["España", "espana", "españa"]),
    ("La Rivera", "Oruro", ["La Rivera", "la rivera"]),
    (
        "Pantaleón Dalence",
        "Oruro",
        ["Pantaleón Dalence", "pantaleon dalence", "pantaleón dalence"],
    ),
    (
        "Sebastián Pagador",
        "Oruro",
        ["Sebastián Pagador", "sebastian pagador", "sebastián pagador"],
    ),
    ("Turco", "Oruro", ["Turco", "turco"]),
    ("Urmiri", "Oruro", ["Urmiri", "urmiri"]),
    ("El Choro", "Oruro", ["El Choro", "el choro"]),
    ("Esse Ejau", "Oruro", ["Esse Ejau", "esse ejau"]),
    ("San Pedro de Totora", "Oruro", ["San Pedro de Totora", "san pedro de totora"]),
    ("Ladislao Cabrera", "Oruro", ["Ladislao Cabrera", "ladislao cabrera"]),
    ("San Pedro de Macha", "Potosí", ["San Pedro de Macha", "san pedro de macha"]),
    ("Tinguipaya", "Potosí", ["Tinguipaya", "tinguipaya"]),
    ("Yocalla", "Potosí", ["Yocalla", "yocalla"]),
    ("Puna", "Potosí", ["Puna", "puna"]),
    ("Tomave", "Potosí", ["Tomave", "tomave"]),
    (
        "San Pedro de Buena Vista",
        "Potosí",
        ["San Pedro de Buena Vista", "san pedro de buena vista"],
    ),
    ("San Agustín", "Potosí", ["San Agustín", "san agustin", "san agustín"]),
    (
        "Villa Vaca Guzmán",
        "Chuquisaca",
        ["Villa Vaca Guzmán", "villa vaca guzman", "villa vaca guzmán"],
    ),
    ("El Villar", "Chuquisaca", ["El Villar", "el villar"]),
    ("Las Carreras", "Chuquisaca", ["Las Carreras", "las carreras"]),
    ("San Ignacio", "Beni", ["San Ignacio", "san ignacio", "gam san ignacio"]),
    ("Santa Rosa", "Beni", ["Santa Rosa", "santa rosa", "gam santa rosa"]),
    (
        "Puerto Gonzalo Moreno",
        "Pando",
        ["Puerto Gonzalo Moreno", "puerto gonzalo moreno"],
    ),
]


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    existing = {u["name"].lower() for u in data["ubicaciones"]}
    m_codes = [u for u in data["ubicaciones"] if u["code"].startswith("M")]
    start = max(int(u["code"][1:]) for u in m_codes) + 1 if m_codes else 1
    added = 0
    code = start
    for name, dept, aliases in WAVE7_MUNICIPAL:
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

    total = len(data["ubicaciones"])
    gap = int(data.get("target_total") or 352) - total
    data["version"] = "2025-wave7-incremental"
    data["count"] = total
    data["note"] = (
        f"Wave 7 incremental set ({total} ubicaciones; gap {gap} to GeoPackage 352). "
        "Merge official MEFP GeoPackage export for remaining municipios — "
        "see docs/sources/mefp_ubicaciones.md."
    )
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Added {added} municipios; total={total}; gap_to_352={gap}")


if __name__ == "__main__":
    main()

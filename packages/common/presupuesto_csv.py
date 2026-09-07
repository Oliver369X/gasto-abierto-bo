"""Parse official Presupuesto Abierto CSV/Parquet exports.

Column mapping is tolerant — the MEFP export has ~200 columns; we pick the
first matching alias per field.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any, Iterator

from common.money import parse_money

# Aliases observed in MEFP exports and fixture JSON
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "entity_name": (
        "entidad",
        "institucion",
        "institución",
        "nombre_entidad",
        "entity",
        "organismo",
    ),
    "level": ("nivel", "nivel_administrativo", "tipo_entidad"),
    "year": ("gestion", "gestión", "year", "anio", "año", "ejercicio"),
    "program_project": (
        "programa",
        "proyecto",
        "programa_proyecto",
        "programa y proyecto",
        "denominacion_programa",
    ),
    "budget_item": (
        "partida",
        "partida_presupuestaria",
        "codigo_partida",
        "clasificador",
    ),
    "object": ("objeto", "objeto_gasto", "objeto del gasto", "descripcion_objeto"),
    "department": ("departamento", "department", "ubicacion_geografica", "geografico"),
    "municipality": ("municipio", "municipality", "provincia"),
    "initial_amount": (
        "presupuesto_inicial",
        "inicial",
        "monto_inicial",
        "ppto_inicial",
    ),
    "modified_amount": (
        "presupuesto_modificado",
        "modificado",
        "monto_modificado",
    ),
    "current_amount": (
        "presupuesto_vigente",
        "vigente",
        "monto_vigente",
        "ppto_vigente",
    ),
    "executed_amount": ("ejecucion", "ejecución", "ejecutado", "monto_ejecutado"),
    "commitment": ("compromiso", "commitment"),
    "accrual": ("devengado", "accrual"),
    "payment": ("pagado", "payment", "pago"),
    "sector": ("sector", "sector_economico", "actividad"),
    "funding_source": ("fuente", "fuente_financiamiento", "origen_recursos"),
}


def _norm_header(name: str) -> str:
    return (
        name.strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )


def build_header_map(fieldnames: list[str] | None) -> dict[str, str]:
    """Map canonical field -> actual CSV column name."""
    if not fieldnames:
        return {}
    lower = {_norm_header(h): h for h in fieldnames if h}
    out: dict[str, str] = {}
    for canonical, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            key = _norm_header(alias)
            if key in lower:
                out[canonical] = lower[key]
                break
            for lk, orig in lower.items():
                if key in lk or lk in key:
                    out[canonical] = orig
                    break
            if canonical in out:
                break
    return out


def _pick(row: dict[str, str], header_map: dict[str, str], field: str) -> str:
    col = header_map.get(field)
    if not col:
        return ""
    val = row.get(col, "")
    return str(val).strip() if val is not None else ""


def row_to_budget_dict(row: dict[str, str], header_map: dict[str, str]) -> dict[str, Any] | None:
    entity = _pick(row, header_map, "entity_name")
    if not entity:
        return None
    year_raw = _pick(row, header_map, "year")
    try:
        year = int(float(year_raw)) if year_raw else 2025
    except ValueError:
        year = 2025
    program = _pick(row, header_map, "program_project") or _pick(row, header_map, "object")
    return {
        "entity_name": entity,
        "level": _pick(row, header_map, "level") or "nacional",
        "year": year,
        "program_project": program or None,
        "budget_item": _pick(row, header_map, "budget_item") or None,
        "department": _pick(row, header_map, "department") or None,
        "initial_amount": str(parse_money(_pick(row, header_map, "initial_amount")) or ""),
        "modified_amount": str(parse_money(_pick(row, header_map, "modified_amount")) or ""),
        "current_amount": str(parse_money(_pick(row, header_map, "current_amount")) or ""),
        "executed_amount": str(parse_money(_pick(row, header_map, "executed_amount")) or ""),
        "commitment": str(parse_money(_pick(row, header_map, "commitment")) or ""),
        "accrual": str(parse_money(_pick(row, header_map, "accrual")) or ""),
        "payment": str(
            parse_money(
                _pick(row, header_map, "payment")
                or _pick(row, header_map, "executed_amount")
            )
            or ""
        ),
        "budget_phase": "mapped",
        "source_id": "presupuesto_abierto",
        "source_note": "presupuesto_abierto_csv",
    }


def detect_delimiter(sample: str) -> str:
    if sample.count(";") > sample.count(","):
        return ";"
    if sample.count("|") > sample.count(","):
        return "|"
    return ","


def parse_csv_bytes(raw: bytes) -> list[dict[str, Any]]:
    text = raw.decode("utf-8-sig", errors="replace")
    delim = detect_delimiter(text[:4096])
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    header_map = build_header_map(list(reader.fieldnames or []))
    if "entity_name" not in header_map:
        return []
    out: list[dict[str, Any]] = []
    for row in reader:
        mapped = row_to_budget_dict(row, header_map)
        if mapped:
            out.append(mapped)
    return out


def parse_parquet_bytes(raw: bytes) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as pq  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "Parquet requiere pyarrow: pip install 'gasto-abierto-bo[parquet]'"
        ) from exc
    table = pq.read_table(io.BytesIO(raw))
    rows = table.to_pylist()
    if not rows:
        return []
    fieldnames = [str(k) for k in rows[0].keys()]
    header_map = build_header_map(fieldnames)
    if "entity_name" not in header_map:
        return []
    out: list[dict[str, Any]] = []
    for pyrow in rows:
        str_row = {str(k): "" if v is None else str(v) for k, v in pyrow.items()}
        mapped = row_to_budget_dict(str_row, header_map)
        if mapped:
            out.append(mapped)
    return out


def parse_file_bytes(raw: bytes, *, filename: str = "") -> list[dict[str, Any]]:
    name = filename.lower()
    if name.endswith(".parquet"):
        return parse_parquet_bytes(raw)
    if raw[:4] == b"PAR1":
        return parse_parquet_bytes(raw)
    if raw[:1] in (b"{", b"["):
        return []  # JSON handled by adapter
    return parse_csv_bytes(raw)


def iter_csv_rows(path: Path) -> Iterator[dict[str, Any]]:
    raw = path.read_bytes()
    yield from parse_csv_bytes(raw)

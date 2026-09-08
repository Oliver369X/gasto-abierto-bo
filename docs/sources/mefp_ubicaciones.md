# MEFP ubicaciones (clasificador geográfico)

El clasificador en `packages/common/mefp_geo.py` usa `packages/common/data/mefp_ubicaciones.json`, incrementado manualmente hacia el catálogo oficial de **352 ubicaciones** del Presupuesto Abierto (MEFP).

## Estado actual

- Archivo: `mefp_ubicaciones.json` (`count`, `target_total: 352`)
- Wave 6: **224** ubicaciones; Wave 7: **280** ubicaciones (gap **72** al catálogo GeoPackage)
- Tests exigen `count >= 280`
- Scripts incrementales: `scripts/ops/expand_mefp_wave4.py` … `expand_mefp_wave7.py`

## Brecha restante hacia 352

| Métrica | Valor |
|---------|-------|
| En repo (Wave 7) | 280 ubicaciones (9 departamentales + 271 municipales) |
| Objetivo MEFP | 352 |
| **Gap** | **72** ubicaciones sin merge manual curado |

Los 72 faltantes requieren el export oficial (GeoPackage/CSV) del portal Presupuesto Abierto — no se inventan nombres en repo para evitar falsos positivos en clasificación.

## Fuente oficial para completar 352

**Próximo paso recomendado (merge automatizable):**

1. Portal Presupuesto Abierto — descargas geográficas  
   **URL:** https://abierto.economiayfinanzas.gob.bo/presupuesto/descargas  
   Buscar export **GeoPackage** o **CSV** de *ubicaciones* / *geografía presupuestaria* (catálogo institucional MEFP, 352 filas).

2. Alternativa vía API/dataset CKAN del mismo portal (si el GPKG no está enlazado):
   - Listar recursos: `python -m scripts.cli gasto fetch-presupuesto --list-only`
   - O inspeccionar `https://abierto.economiayfinanzas.gob.bo/api/3/action/package_search?q=ubicacion`

3. Merge al JSON del repo:
   - Campos esperados por entrada: `code`, `name`, `department`, `level` (`departamental`|`municipal`), `aliases[]`
   - Normalizar nombres con la misma lógica que `_norm()` en `mefp_geo.py`
   - Ejecutar `pytest tests/test_mefp_geo.py -q` y actualizar `count` / `version`

4. **No usar** Excel en Google Drive ni fuentes no públicas (política del proyecto).

## Validación

```bash
pytest tests/test_mefp_geo.py -q
python -c "from common.mefp_geo import ubicacion_count, target_ubicacion_count; print(ubicacion_count(), '/', target_ubicacion_count())"
```

## Referencias

- `docs/sources/presupuesto_abierto.md` — ingest presupuesto
- `AUDIT.md` — correlación geográfica P1

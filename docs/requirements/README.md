# Requisitos de referencia (no commitear el .xlsx)

Colocá aquí materiales de referencia para trazabilidad de requisitos:

```
docs/requirements/auditoria-drive-MASTER-v9.3.xlsx
```

**No subir el workbook a git** — puede contener datos sensibles o borradores internos.

## Análisis automático

```bash
pip install openpyxl   # o: pip install -e ".[workbook]"
python scripts/analyze_audit_workbook.py
```

El script lista hojas, encabezados y sugiere mapeos a:

- `entity`, `budget_line`, `contract`, `supplier`, `discrepancy`, `alert`
- KPIs: ratio ejecución, agregados, histórico, cobertura
- Joins sugeridos: institución × gestión × geografía × CUCE

## Fuente de datos oficial (prioridad)

Los campos del workbook deben implementarse contra **descargas oficiales** de Presupuesto Abierto (`abierto.economiayfinanzas.gob.bo/descargas`), no ingestando el Excel como fuente primaria.

Ver `docs/sources/presupuesto_abierto.md` y `python -m scripts.cli gasto fetch-presupuesto`.

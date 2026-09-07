# Plan Maestro G1–G10 — DoD local

## Comandos

```bash
# Migraciones
docker compose exec api alembic -c packages/schema/alembic.ini upgrade head
# o desde host con DATABASE_URL

# Tests calidad
cd gasto-abierto-bo
pytest tests/test_data_quality_g1.py tests/test_product_gate_g10.py -q

# Evidencia API
curl -s "http://localhost:8010/v1/stats?quality=public" | jq .
curl -s "http://localhost:8010/v1/stats?quality=all" | jq .
curl -s "http://localhost:8010/v1/coverage/sicoes" | jq .
curl -s "http://localhost:8010/v1/product-gate" | jq .
```

## UI

- `/explorar` — badge de calidad
- `/contrato/[id]` — sección Evidencia
- `/cobertura` — flags SICOES + gate G10
- `/historico` — nota ausencia ≠ cero
- `/proveedor/[id]` — master + alias cuando hay NIT

## ClickUp cierre

```
✅ Hecho
- Qué: Plan Maestro G1–G10 (calidad, evidencia, masters, fases, alertas honestas)
- Comando: pytest tests/test_data_quality_g1.py tests/test_product_gate_g10.py
- Evidencia: curl stats/coverage/product-gate + UI /cobertura
- Commit/PR: (pendiente pedido fundador)
```

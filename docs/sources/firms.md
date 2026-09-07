# Fuente: NASA FIRMS

| Campo | Valor |
|-------|-------|
| `source_id` | `firms` |
| Adapter | `services/worker/adapters/firms.py` |
| Uso | Capa de **resultados** (fuego activo), no gasto |
| URL | https://firms.modaps.eosdis.nasa.gov/ |

## Extracción MVP

Fixture `tests/fixtures/firms/bolivia_2024_sample.json` → `active_fire_detection` + agregados `fire_operational`.

Live: requiere `MAP_KEY` de Earthdata — no inventar endpoints. Preferir API/archivo CSV sobre scraping UI.

## Advertencia

**Un foco de calor ≠ una hectárea quemada.** Separar siempre de burned area / perímetros.

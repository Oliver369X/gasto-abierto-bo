# Fuente: ABT (Autoridad de Bosques y Tierra)

| Campo | Valor |
|-------|-------|
| `source_id` | `abt` |
| Adapter | `services/worker/adapters/abt.py` |
| Uso | Ejecución presupuestaria / prevención y fiscalización forestal |
| Acceso | Portales de transparencia públicos |

## URLs

- Programado/ejecutado: https://www.abt.gob.bo/index.php/institucion/plan-estrategico/programado-ejecutado-y-resultados
- Presupuesto institucional: https://www.abt.gob.bo/index.php/transparencia/informacion-financiera/presupuesto-institucional
- Adquisiciones: https://www.abt.gob.bo/index.php/transparencia/informacion-financiera/adquisiciones-de-bienes-y-servicios

## Extracción MVP

1. Fixture JSON `tests/fixtures/abt/ejecucion_2024.json`
2. Parse → `budget` StagingRecord; clasificador fuego → `fire_expenditure_candidate` si aplica
3. Años fixture: 2023–2024 (serie 2018–2024 en backlog)

## Inventario completo

Ver `docs/sources/fire-inventory.md`.

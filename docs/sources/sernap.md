# Fuente: SERNAP

| Campo | Valor |
|-------|-------|
| `source_id` | `sernap` |
| Adapter | `services/worker/adapters/sernap.py` |
| Uso | Focos en áreas protegidas + gasto/brigadas con evidencia |
| URLs | https://www.sernap.gob.bo/index.php/datos/ · rendiciones · presupuesto |

## Extracción MVP

Fixture `tests/fixtures/sernap/incendios_ap.json`:

- `fire_operational` (focos AP, eventos sofocados)
- `fire_expenditure_candidate` (equipamiento brigadas)
- `budget` (programas monitoreo/prevención)

No atribuir presupuesto total SERNAP a incendios sin evidencia de programa/contrato.

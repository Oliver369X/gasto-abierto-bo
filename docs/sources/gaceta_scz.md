# Fuente: Gaceta Oficial Santa Cruz

| Campo | Valor |
|-------|-------|
| `source_id` | `gaceta_scz` |
| Adapter | `services/worker/adapters/gaceta_scz.py` |
| Uso | Declaratorias de emergencia/desastre (filtro incendios) |
| URL | https://gacetaoficial.santacruz.gob.bo/decretosdepartamentales |

## Extracción MVP

Fixture `tests/fixtures/gaceta_scz/decretos_incendio.json` → `emergency_declaration`.

Incluye control negativo (`inundacion`) para no mezclar con el ledger de incendios.

## Flujo

```
Decreto emergencia incendio → fecha + territorio
  → buscar expedientes SICOES/ledger en ventana temporal
  → API GET /v1/fire/declarations/{id}
```

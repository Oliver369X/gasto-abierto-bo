# Roadmap

## Fase 1 — MVP (este repo)

Presupuesto Abierto, SICOES, AGETIC, Contraloría (informes), GAD/GAM Santa Cruz, API, UI, alertas explicables.

## Fase 1b — AURA Incendios (vertical)

Ledger verificable de gasto en incendios forestales: schema `fire_*`, adapters `mindef`/`abt`/`gaceta_scz`/`sernap`/`firms`, clasificador determinista, API `/v1/fire/*` (ledger, history, compare, satellite, declarations), UI `/incendios` multi-año, seed 2022–2025, alertas `fire_*`. Inventario: `docs/sources/fire-inventory.md`.

## Fase 2 — Departamentos clave

- Gobernaciones La Paz, Cochabamba
- SISIN solo si hay acceso público documentado
- Elasticsearch para búsqueda full-text
- Airflow para orquestación de DAGs
- FIRMS live (MAP_KEY) + mapa interactivo; gacetas nacionales; CUCEs reales SICOES

## Fase 3 — Empresas públicas

- YPFB, ENDE, ENTEL portales de contratación
- Más reglas de alerta + vínculos auditoría↔contrato

## Fase 4 — Cobertura nacional

- Más municipios, gacetas (OCR), endurecimiento prod
- Kafka streaming si el volumen lo justifica
- Gobernanza y compliance documentados

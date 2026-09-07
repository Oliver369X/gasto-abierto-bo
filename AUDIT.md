# Auditoría — Gasto Abierto Bolivia

**Fecha:** 2026-09-07  
**Alcance:** plataforma ciudadana de gasto público (Presupuesto Abierto, SICOES, datos.gob.bo, Contraloría, portales SCZ)  
**Objetivo:** elevar calidad de UI y datos hasta una plataforma completa de gasto abierto gubernamental.

---

## Resumen ejecutivo

El repositorio es un **MVP maduro** con arquitectura sólida (adaptadores, SCD2, provenance, cruce CUCE, vertical AURA Incendios). Los principales gaps para una plataforma de referencia son:

1. **Presupuesto Abierto** depende de fixtures JSON pequeños; el modo live apunta al HTML del portal (sin filas útiles) en lugar de descargas oficiales CSV/Parquet.
2. **UI** concentra demasiada lógica en páginas monolíticas, sin gráficos ni componentes reutilizables; el home no destaca presupuesto.
3. **Correlaciones** presupuesto↔contratos existen en backend (`cross_source`, discrepancias) pero no hay exploración ciudadana por institución/objeto/año/geografía.
4. **CI** no compila el frontend ni ejecuta tests de calidad/fire por defecto.
5. **Mensajes API** mezclados inglés/español.

---

## P0 — Bloqueantes para plataforma completa

| # | Hallazgo | Impacto | Archivos |
|---|----------|---------|----------|
| P0-1 | Adaptador Presupuesto Abierto no consume descargas oficiales CSV/Parquet de [abierto.economiayfinanzas.gob.bo/descargas](https://abierto.economiayfinanzas.gob.bo/descargas); live devuelve HTML vacío | Datos presupuestarios incompletos vs. fuente oficial (~8M filas) | `services/worker/adapters/presupuesto_abierto.py`, `docs/sources/presupuesto_abierto.md`, `packages/common/fetch_open_data.py` |
| P0-2 | Sin pipeline documentado para refrescar datos gubernamentales Presupuesto Abierto (solo JSON fixture ~10 entidades) | Imposible mantener plataforma actualizada sin intervención manual | `scripts/cli/gasto.py`, `services/worker/gasto/ingest_cli.py`, `tests/fixtures/presupuesto_abierto/` |
| P0-3 | Home y navegación no exponen presupuesto ni correlaciones institución/objeto/año/geografía | UX percibida como “solo contratos”, no plataforma fiscal integral | `services/web/app/page.tsx`, `services/web/app/layout.tsx` |
| P0-4 | Mensajes HTTP 404/500 de la API en inglés | Inconsistente con UI Spanish-first | `services/api/routers/*.py`, `services/api/fire.py` |

---

## P1 — Alta prioridad (calidad producto)

| # | Hallazgo | Impacto | Archivos |
|---|----------|---------|----------|
| P1-1 | Sin endpoint de agregación presupuestaria por dimensión (entidad, departamento, año, categoría) | No hay análisis transversal ciudadano | `services/api/routers/entities.py`, `services/api/schemas.py` |
| P1-2 | Página metodología muestra `rule_id` en inglés crudo | Confuso para ciudadanía | `services/web/app/metodologia/page.tsx`, `services/web/lib/labels.ts` |
| P1-3 | Stats del home omiten líneas presupuestarias y montos vigentes/ejecutados | Dashboard incompleto | `services/web/app/page.tsx`, `services/api/schemas.py`, `services/worker/gasto/stats_snapshot.py` |
| P1-4 | SICOES live depende de Playwright + HTML frágil | Rotura frecuente ante cambios del portal | `services/worker/adapters/sicoes.py`, `services/worker/adapters/sicoes_fetch.py` |
| P1-5 | CI ejecuta subconjunto mínimo de tests; sin `next build` | Regresiones UI/syntax no detectadas | `.github/workflows/ci.yml`, `services/web/package.json` |
| P1-6 | Página `/historico` sin ratio ejecución presupuesto ni enlace a Presupuesto Abierto | Análisis fiscal superficial | `services/web/app/historico/page.tsx` |
| P1-7 | Entidad no enlaza presupuesto con contratos por año/gestión | Correlación entidad-año no visible | `services/web/app/entidad/[id]/page.tsx` |

---

## P2 — Mejoras estructurales (siguiente iteración)

| # | Hallazgo | Impacto | Archivos |
|---|----------|---------|----------|
| P2-1 | `incendios/page.tsx` ~800 líneas monolíticas | Mantenibilidad y rendimiento | `services/web/app/incendios/page.tsx` |
| P2-2 | Un solo componente compartido (`Pager.tsx`); tablas/filtros duplicados | Deuda UI | `services/web/app/components/` |
| P2-3 | Sin librería de gráficos (Recharts, etc.) | Visualización limitada a tablas | `services/web/package.json` |
| P2-4 | Scripts legacy masivos aún presentes | Riesgo de bypass de gates | `scripts/_legacy/` |
| P2-5 | Cron worker re-ingesta fixtures, no datos live | Datos stale en despliegues sin seed manual | `services/worker/main.py` |
| P2-6 | Nightly workflow deshabilitado salvo `workflow_dispatch` | Sin monitorización live automática | `.github/workflows/nightly.yml` |
| P2-7 | Credenciales dev hardcodeadas en compose | Riesgo si se despliega sin rotar | `docker-compose.yml`, `.env.example` |
| P2-8 | Sin i18n framework (Quechua/Aymara futuro) | Escalabilidad lingüística | `services/web/lib/labels.ts` |
| P2-9 | Mapa incendios con proyección SVG aproximada | Precisión geográfica limitada | `services/web/app/incendios/mapa/FireCoverageMap.tsx` |
| P2-10 | Parquet requiere dependencia opcional `pyarrow` | Documentar en ops | `pyproject.toml`, `docs/ops.md` |

---

## Fortalezas existentes

- Adaptadores con contrato `discover → fetch → parse` y tests offline (`tests/contract/`).
- SCD2 + provenance (`source_id`, `ingestion_run_id`) en contratos y presupuesto.
- Cruce CUCE y discrepancias presupuesto vs contratos (`packages/common/cross_source.py`, `services/worker/reconcile.py`).
- Política ética de scraping con proxy obligatorio (`docs/legal/data-policy.md`, `packages/common/http_client.py`).
- UI mayormente en español con `lang="es"` y locale `es-BO`.
- Vertical AURA Incendios con libro mayor verificable y gates G10.

---

## Implementado en este PR (P0/P1)

| Ítem | Cambio |
|------|--------|
| P0-1, P0-2 | Descarga oficial configurable + parseo CSV/Parquet en adaptador; CLI `gasto fetch-presupuesto` |
| P0-3 | Página `/presupuesto` con agregados por institución/departamento/año/categoría |
| P0-4 | Mensajes 404 API en español (routers principales) |
| P1-1 | `GET /v1/budgets/aggregate` |
| P1-2 | Etiquetas españolas para reglas de alerta en metodología |
| P1-3 | Home muestra líneas presupuestarias y totales vigente/ejecutado |
| P1-6 | Histórico con ratio de ejecución y fuente Presupuesto Abierto |
| README | Instrucciones locales + refresco de datos gubernamentales |

---

## Trabajo restante (post-PR)

1. Integrar URLs concretas de descarga cuando el portal publique endpoints estables (copiar desde `/descargas`).
2. Añadir `next build` y tests fire/quality a CI.
3. Refactorizar componentes UI compartidos y gráficos de serie temporal.
4. Retirar `scripts/_legacy/` tras migración completa al CLI.
5. Endurecer secretos de producción y rotación documentada.
6. Enriquecer correlación geográfica con clasificador territorial del Presupuesto Abierto (352 ubicaciones).

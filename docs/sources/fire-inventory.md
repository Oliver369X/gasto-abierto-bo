# Inventario técnico — AURA Incendios

Formato de ingeniería para scrapers/ETL. Prioridad: P0 crítica · P1 alta · P2 media.

| URL exacta | Entidad | Dato disponible | Años | Formato | API/XHR | Scraping | OCR | Prioridad | Frecuencia | Dificultad | Identificadores | Estrategia ETL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| https://www.sicoes.gob.bo/ | SICOES | Procesos, adjudicaciones, proveedores, montos, documentos | ~2010+ | HTML dinámico | Investigar XHR (DevTools); no hay API pública documentada | Playwright fallback | PDF adjuntos | P0 | Semanal temporada / mensual | Alta | CUCE, NIT | Reproducir consulta HTTP; filtro diccionario fuego; adjuntos → MinIO |
| https://www.mindef.gob.bo/index.php/rendicion-publica-de-cuentas/ | MINDEF | RPC inicial/final, operaciones VIDECI | 2022–2026 | HTML + PDF | No | HTML índice → PDF | Solo si sin texto | P0 | Anual | Media | gestión, página | Fixture→pdfplumber; clasificar párrafos incendio |
| https://www.mindef.gob.bo/wp-content/uploads/2026/01/12032025_INFORME_RPCFinal_2024_V15.pdf | MINDEF | RPC Final 2024 (aeronaves, bomberos, litros) | 2024 | PDF | Descarga directa | HTTP GET | Fallback | P0 | Única | Baja–media | hash SHA-256 | Parse métricas + candidatos; **no** atribuir pool emergencia/desastre completo |
| https://www.mindef.gob.bo/index.php/presupuesto-de-las-estrategias-intitucionales/ | MINDEF | Presupuesto/ejecución institucional | 2025–2026 visibles | PDF/HTML | No | HTML | Posible | P0 | Anual | Media | gestión | Cruzar con SICOES/RPC |
| https://www.mindef.gob.bo/index.php/contratos/ | MINDEF | Listado contratos | Parcial | HTML | No | HTML | — | P1 | Mensual | Baja | nº contrato | Complemento; SICOES es fuente central |
| https://abierto.economiayfinanzas.gob.bo/ | MEFP Presupuesto Abierto | Inicial, vigente, ejecutado por entidad/programa | Multi-año | SPA | XHR a descubrir | Playwright si hace falta | — | P0 | Mensual | Alta | entidad, gestión | Preferir JSON interno a clics |
| https://www.abt.gob.bo/index.php/institucion/plan-estrategico/programado-ejecutado-y-resultados | ABT | Ejecución presupuestaria | 2018–2024 | HTML/PDF | No | HTML + PDF | Fallback | P0 | Anual | Media | gestión, partida | Adapter `abt`; clasificar partidas prevención/fiscalización |
| https://www.abt.gob.bo/index.php/transparencia/informacion-financiera/presupuesto-institucional | ABT | Presupuestos históricos | ~2014–2022 | PDF | No | HTML índice | Posible | P1 | Anual | Media | gestión | Serie histórica capa 2 |
| https://www.abt.gob.bo/index.php/transparencia/informacion-financiera/adquisiciones-de-bienes-y-servicios | ABT | Adquisiciones | ~2016–2025 | PDF/HTML | No | HTML | Posible | P1 | Anual | Media | gestión | Cruzar SICOES |
| https://www.abt.gob.bo/index.php/transparencia/informacion-gestion/informes-anuales | ABT | Informes anuales / deforestación | ~2010+ | PDF | No | HTML | Posible | P1 | Anual | Media | año | Contexto resultados, no dinero directo |
| https://www.sernap.gob.bo/index.php/presupuesto-de-las-estrategias-intitucionales/ | SERNAP | Presupuesto | Varios | PDF/HTML | No | HTML | Posible | P1 | Anual | Media | gestión | Solo con evidencia de programa incendio |
| https://www.sernap.gob.bo/index.php/rendicion-publica-de-cuentas/ | SERNAP | Rendiciones | 2017, 2019–2025 | PDF | No | HTML | Posible | P1 | Anual | Media | gestión | Igual criterio evidencia |
| https://www.sernap.gob.bo/index.php/datos/ | SERNAP | Focos de calor / fuego activo AP | Reciente | HTML/PDF | No | HTML | — | P1 | Semanal temporada | Baja–media | área protegida | Resultados territoriales |
| https://gacetaoficial.santacruz.gob.bo/decretosdepartamentales | GAD SCZ | Decretos emergencia | Histórico | HTML + PDF | No | Paginación | Posible | P1 | Semanal | Media | nº decreto, fecha | NLP tipo evento → ventana SICOES |
| https://www.gacetaoficialdebolivia.gob.bo/ | Gaceta nacional | DS emergencia, transferencias | Histórico | HTML/PDF | Por verificar | Crawler propio | Posible | P1 | Semanal | Alta | nº norma | Timeout observado; investigar endpoints |
| https://www.contraloria.gob.bo/informes-de-auditorias-nuevo/ | CGE | Auditorías | Multi-año | HTML | Adapter `cge` MVP | HTML | — | P1 | Mensual | Media | título, año | Vincular a expediente por keywords/CUCE |
| https://datos.gob.bo/ | AGETIC | Datasets abiertos | Variable | CKAN API/CSV | Sí (CKAN) | Evitar si hay API | — | P1 | Mensual | Baja–media | package_id | Preferir API; 403 en portada → endpoints específicos |
| https://firms.modaps.eosdis.nasa.gov/ | NASA FIRMS | Fuego activo MODIS/VIIRS | Histórico | API/archivo | Sí | No scrapear UI | — | P2 (Fase 2) | Diario temporada | Media | lat/lon, fecha | Resultados espaciales; foco ≠ hectárea quemada |
| Portales 9 gobernaciones | GADs | Presupuesto, COED, UGR | Variable | Mixto | Raro | Crawler por portal | Frecuente | P2 | Anual | Muy alta | entidad, gestión | Fase 3 |
| GAM municipios afectados | GAMs | Combustible, brigadas, emergencia | Variable | Mixto | Raro | Distribuido | Frecuente | P2 | Anual | Muy alta | municipio | Tras declaratorias |

## Jerarquía de extracción (obligatoria)

1. API oficial → 2. CSV/JSON/XLSX → 3. XHR interno → 4. HTML → 5. Playwright → 6. PDF texto → 7. Tablas PDF → 8. OCR → 9. Visión/LLM → 10. Revisión humana

## Caso piloto MVP

`CASO FIRE-BO-2024-000001…000004` — 4 alquileres de aeronaves MINDEF 2024. Montos en seed son **calidad D** (fixtures) hasta CUCEs reales vía SICOES live.

## Adapter IDs en este repo

| source_id | Estado MVP |
|-----------|------------|
| `mindef` | Fixture RPC 2024 + parse JSON/PDF |
| `abt` | Fixture ejecución |
| `sicoes` | Extensión fire fixtures aeronaves |
| `presupuesto_abierto` | Reuso + clasificador |
| `gaceta_scz` / `firms` | Fase 1.5 / 2 |

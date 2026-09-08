# Presupuesto Abierto

| Campo | Valor |
|-------|-------|
| URL | https://abierto.economiayfinanzas.gob.bo/ |
| Descargas | https://abierto.economiayfinanzas.gob.bo/descargas |
| Formato | CSV, Parquet, GeoPackage (oficial) |
| Rate | ≤ 1 req/s (descargas directas) |
| Adapter | `presupuesto_abierto` |

## Estrategia (preferida)

1. **Descargas oficiales** CSV/Parquet desde `/descargas` — no scraping del portal SPA.
2. Si `PRESUPUESTO_ABIERTO_DOWNLOAD_URLS` está vacío, el CLI **descubre URLs** desde la página oficial (Parquet «Para desarrolladores» + enlaces directos).
3. CLI: `python -m scripts.cli gasto fetch-presupuesto` → `tests/fixtures/real/presupuesto_abierto/` (o copia fixtures locales si la red falla).
4. Ingesta: `python -m scripts.cli gasto ingest --source presupuesto_abierto --sync` (usa fixtures empaquetados si no hay URLs).
5. Fallback histórico: JSON en `tests/fixtures/presupuesto_abierto/` y datasets CKAN vía adapter `agetic`.

### Refrescar datos

```bash
# Ver URLs descubiertas (sin proxy; solo listado)
python -m scripts.cli gasto fetch-presupuesto --list-only

# Descargar offline (copia fixtures locales si falla la red)
python -m scripts.cli gasto fetch-presupuesto

# Descargar en vivo (requiere LIVE_SCRAPE=1 + PROXY_URL)
LIVE_SCRAPE=1 PROXY_URL=http://host.docker.internal:7890 \
  python -m scripts.cli gasto fetch-presupuesto

# Opcional: fijar URLs manualmente
export PRESUPUESTO_ABIERTO_DOWNLOAD_URLS="https://abierto.economiayfinanzas.gob.bo/presupuesto/descargas/gasto/ultimo/gasto.parquet"

# Ingestar al stack Docker
docker compose run --rm --entrypoint python api -m scripts.cli gasto ingest --source presupuesto_abierto --sync
```

Corpus offline empaquetado: `tests/fixtures/presupuesto_abierto/offline_corpus_manifest.json`.

Parquet requiere dependencia opcional: `pip install 'gasto-abierto-bo[parquet]'`.

### Columnas soportadas (aliases)

El export MEFP tiene ~200 columnas. El parser mapea aliases comunes:

| Campo interno | Aliases CSV |
|---------------|-------------|
| entidad | `entidad`, `institucion`, `nombre_entidad` |
| gestión | `gestion`, `year`, `ejercicio` |
| departamento | `departamento`, `ubicacion_geografica`, `geografico` |
| programa | `programa`, `proyecto`, `programa_proyecto` |
| partida | `partida`, `codigo_partida` |
| vigente | `presupuesto_vigente`, `ppto_vigente`, `vigente` |
| ejecutado | `ejecucion`, `pagado`, `devengado` |

### Forma canónica del JSON de fixture

```json
{
  "entidades": [
    {
      "entidad": "Ministerio de Educación",
      "nivel": "nacional",
      "gestion": 2025,
      "departamento": "La Paz",
      "presupuesto_inicial": "50000000",
      "presupuesto_vigente": "51000000",
      "ejecucion": "25000000"
    }
  ]
}
```

### API de correlación

- `GET /v1/budgets/totals` — totales vigente/ejecutado
- `GET /v1/budgets/aggregate?group_by=department|entity|year|category|program`
- `GET /v1/cross-source/summary` — discrepancias presupuesto vs contratos

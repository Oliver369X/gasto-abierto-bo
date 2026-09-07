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
2. Configurar URLs directas en `PRESUPUESTO_ABIERTO_DOWNLOAD_URLS` (comma-separated).
3. CLI: `python -m scripts.cli gasto fetch-presupuesto` → `tests/fixtures/real/presupuesto_abierto/`.
4. Ingesta: `python -m scripts.cli gasto ingest --source presupuesto_abierto --sync` (usa fixtures o descargas).
5. Fallback histórico: JSON en `tests/fixtures/presupuesto_abierto/` y datasets CKAN vía adapter `agetic`.

### Refrescar datos

```bash
# 1. Copiar URLs de archivos .csv/.parquet desde la página de descargas oficial
export PRESUPUESTO_ABIERTO_DOWNLOAD_URLS="https://.../presupuesto.csv,https://.../presupuesto.parquet"

# 2. Descargar (no requiere LIVE_SCRAPE ni proxy)
python -m scripts.cli gasto fetch-presupuesto

# 3. Ingestar al stack Docker
docker compose run --rm --entrypoint python api -m scripts.cli gasto ingest --source presupuesto_abierto --sync
```

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

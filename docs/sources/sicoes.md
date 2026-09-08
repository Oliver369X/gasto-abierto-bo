# SICOES

| Campo | Valor |
|-------|-------|
| URL | https://www.sicoes.gob.bo |
| Listado | https://www.sicoes.gob.bo/contrat/procesos.php |
| Formato | HTML dinámico |
| Rate | ≤ 1 req/s (`SCRAPE_RATE_LIMIT_RPS`) |
| Login | No (consulta pública) |
| Adapter | `sicoes` |

## Ética

Respetar carga del portal. Guardar raw HTML en MinIO. CI usa fixtures, no red.

## Modos: offline vs live

| Variable | Default | Efecto |
|----------|---------|--------|
| `LIVE_SCRAPE` | `0` | `0` = solo fixtures/archivos; `1` = Playwright contra SICOES |
| `REQUIRE_PROXY_FOR_LIVE` | `1` | Con live, exige `PROXY_URL` o `HTTPS_PROXY` |
| `PROXY_URL` | vacío | Proxy HTTP/SOCKS (ej. `http://host.docker.internal:7890`) |
| `SICOES_OFFLINE_FALLBACK` | `1` | Timeout/red/HTML roto → fixture `procesos_sample.html` |
| `SICOES_FIXTURE_FALLBACK` | — | Ruta alternativa al HTML offline |
| `PLAYWRIGHT_TIMEOUT_MS` | `60000` | Timeout por página |
| `PLAYWRIGHT_RETRIES` | `2` | Reintentos Playwright |
| `SICOES_RETRY_BACKOFF_SEC` | `1.5` | Backoff entre reintentos |
| `SICOES_FETCH_MIN_BYTES` | `256` | Rechaza respuestas vacías/cortas antes del parse |
| `SICOES_MAX_PAGES` | `25` | Páginas por año en discover live |
| `SICOES_YEARS` | vacío | Filtro de gestiones (`2019,2020,...`) |

### Live scrape (staging/prod)

```bash
# 1) Configurar proxy en .env (nunca IP residencial directa)
LIVE_SCRAPE=1
REQUIRE_PROXY_FOR_LIVE=1
PROXY_URL=http://host.docker.internal:7890

# 2) Verificar proxy antes de scrape
curl -s "http://127.0.0.1:${API_HOST_PORT:-8010}/v1/health" | jq '.proxy'  # pragma: allowlist secret

# 3) Ingesta live (worker)
docker compose run --rm worker python -m scripts.cli gasto ingest --source sicoes --sync --live
```

Si el portal devuelve mantenimiento, captcha o HTML vacío, el adapter cae al fixture offline cuando `SICOES_OFFLINE_FALLBACK=1`. CI **nunca** activa `LIVE_SCRAPE`.

### Offline (CI / demo)

```bash
pytest tests/test_sicoes_resilience.py -q   # sin red
docker compose run --rm --entrypoint python api \
  -m scripts.cli gasto ingest --source sicoes --sync
# usa tests/fixtures/sicoes/procesos_sample.html
```

## Resiliencia (Wave 4)

| Escenario | Comportamiento |
|-----------|----------------|
| Timeout Playwright | Reintento con backoff → `FetchError` → fixture offline |
| HTML vacío / <256 B | Rechazado en fetch → fallback offline |
| Página mantenimiento / captcha | Detectado en fetch y en `inspect_list_html()` |
| Estructura de tabla cambiada | `SicoesStructureChanged` o fallback según env |
| CUCE ficha live falla | `fetch_cuce_detail` retorna `None` (soft-fail) |

Live fetch lanza `FetchError` tras reintentos; el adapter hace fallback automático cuando está habilitado. CI: `tests/test_sicoes_resilience.py` (siempre verde sin red).

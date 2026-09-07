# AURA Incendios — operación Docker (dev → prod)

Guía operativa para levantar, verificar y re-procesar el ledger de incendios
**solo con Docker**. No requiere venv local.

## Puertos

| Servicio | Host | Interno |
|----------|------|---------|
| API | `http://localhost:8010` | `:8000` |
| Web `/incendios` | `http://localhost:3010` | `:3000` |
| Postgres | `localhost:5434` | `:5432` |
| Redis | `localhost:6380` | `:6379` |
| MinIO | `localhost:9010` / consola `9011` | |

## 1. Arranque limpio

```bash
cd gasto-abierto-bo
cp .env.example .env   # si aún no existe

# Build + up (API migra alembic al boot; BOOT_FULL_SEED=0 por defecto)
docker compose up -d --build postgres redis minio api web

# Esperar healthy
docker compose ps
curl http://localhost:8010/v1/health
```

Credenciales DB por defecto (cambiar en prod):

```
postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto
```

## 2. Pipeline Plan 2 (F1→F13) — re-ejecutable

CLI preferido (lógica en `worker.fire`, no en scripts gordos):

```bash
docker compose run --rm --no-deps \
  -v "${PWD}/packages:/app/packages" \
  -v "${PWD}/scripts:/app/scripts" \
  -v "${PWD}/services:/app/services" \
  -v "${PWD}/data:/app/data" \
  -v "${PWD}/tests:/app/tests" \
  -e DATABASE_URL=postgresql+psycopg://gasto:gasto_dev_change_me@postgres:5432/gasto_abierto \
  --entrypoint sh api -c '
    export PYTHONPATH=/app/packages:/app/services:/app
    python -m scripts.cli fire pipeline --phase all
  '
```

Una fase: `python -m scripts.cli fire pipeline --phase f5`  
Verificar: `python -m scripts.cli fire verify`

Atajo Windows: `powershell -File .\scripts\run_fire_pipeline.ps1`.

OCR SERNAP (Ola 1): la imagen API debe incluir `tesseract-ocr` + `tesseract-ocr-spa` (rebuild). Cap: `SERNAP_OCR_MAX_PAGES=15`.

SICOES enrich live: `PROXY_URL` + opcional enrich en f5; sin proxy → `blocked_no_proxy`.

FIRMS live: `MAP_KEY` + `FETCH_FIRMS_LIVE=1`; sin key → `blocked_missing_MAP_KEY`; key sin flag → `key_present_fetch_disabled` + clusters locales.

GeoJSON: `GET /v1/fire/coverage.geojson?year=2024`

## 3. Verificación obligatoria (DoD)

```bash
# pytest fire
docker compose exec -T api sh -c \
  'export PYTHONPATH=/app/packages:/app/services && \
   pytest tests/test_fire_ledger_f1.py tests/test_fire_classify.py \
          tests/test_fire_classify_golden.py tests/test_fire_rollup.py \
          tests/test_fire_alerts_f13.py tests/test_fire_api.py -q'

# Gate E2E API + DB + artefactos + web
docker compose run --rm --no-deps \
  -v "${PWD}/packages:/app/packages" \
  -v "${PWD}/scripts:/app/scripts" \
  -v "${PWD}/services:/app/services" \
  -v "${PWD}/data:/app/data" \
  -v "${PWD}/docs:/app/docs" \
  -e API_BASE=http://api:8000 \
  -e WEB_BASE=http://web:3000 \
  -e DATABASE_URL=postgresql+psycopg://gasto:gasto_dev_change_me@postgres:5432/gasto_abierto \
  --entrypoint sh api -c \
  'export PYTHONPATH=/app/packages:/app/services:/app && python -m scripts.cli fire verify'
```

Windows: `powershell -File .\scripts\verify_fire_plan2.ps1`

**Gate duro esperado:**

| Check | Valor |
|-------|-------|
| `amount_direct_verifiable` 2024 | `870000` |
| `sicoes_offline` en coverage | ≥ 100 (hoy ~394) |
| FIRMS samples | 0 |
| Clusters | ≥ 1 |
| `verify_fire_plan2.py` | `ALL GATES PASSED` exit 0 |

Desde host:

```powershell
$env:API_BASE='http://localhost:8010'
$env:WEB_BASE='http://localhost:3010'
$env:DATABASE_URL='postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto'
# con deps locales o vía docker compose run como arriba
```

## 4. Endpoints de producto

| Endpoint | Qué responde |
|----------|----------------|
| `GET /v1/fire/ledger?year=2024` | Headline verificable (sin sintéticos) |
| `GET /v1/fire/coverage` | Fuentes + clusters + ola SCZ/Beni/Pando |
| `GET /v1/fire/cycles?year=2024` | Prevención vs respuesta (anti-doble CUCE) |
| `GET /v1/fire/payers?year=2024` | Quién gastó |
| `GET /v1/fire/expenditures/{id}/chain` | Cadena dinero↔ops↔evento |
| `GET /v1/fire/events?year=2024` | Eventos canónicos |

UI: `http://localhost:3010/incendios`  
Modo honesto por defecto; `?ilustrativos=1` muestra sintéticos.

## 5. Variables de entorno relevantes

```env
# .env — nunca commitear secretos reales
BOOT_FULL_SEED=0          # 1 solo si querés seeds pesados al boot (lento)
LIVE_SCRAPE=0
REQUIRE_PROXY_FOR_LIVE=1
PROXY_URL=                # obligatorio si LIVE_SCRAPE=1
MAP_KEY=                  # NASA FIRMS Earthdata
EARTHDATA_MAP_KEY=        # alias
MINIO_ENABLED=1
```

FIRMS live:

```bash
docker compose run --rm --no-deps \
  -e MAP_KEY="$MAP_KEY" \
  -e DATABASE_URL=postgresql+psycopg://gasto:gasto_dev_change_me@postgres:5432/gasto_abierto \
  --entrypoint sh api -c \
  'export PYTHONPATH=/app/packages:/app/services:/app && python -m scripts.cli fire pipeline --phase f8'
```

## 6. Checklist producción (hardening)

1. **Secretos:** `POSTGRES_PASSWORD`, `MINIO_*`, `MAP_KEY` vía secrets manager / env de despliegue — no defaults de demo.
2. **Rebuild tras cambios de código:** el compose **no monta** el código en `api`/`web` (imagen bakeada). Tras edits: `docker compose build api web && docker compose up -d api web`.
3. **Migraciones:** `alembic upgrade head` corre en `services/api/entrypoint.sh`. No correr UPDATEs masivos de `0008` sobre toda la tabla SICOES en boot (ya diferidos).
4. **Backup:** `docker compose exec postgres pg_dump -U gasto gasto_abierto > backup.sql`
5. **No scrapear prod live** sin proxy (`REQUIRE_PROXY_FOR_LIVE=1`).
6. **No mutar datos reales** de un mirror público sin ventana de mantenimiento.
7. **Healthchecks:** API `/v1/health`, web `GET /`.
8. **Verificar siempre** con `python -m scripts.cli fire verify` antes de declarar release.
9. **Disclaimer público:** el ledger **no es el gasto total nacional** en incendios.
10. **Artefactos:** conservar `data/extracted/` y `docs/aura-incendios/gates.md` como evidencia de gate.

## 7. Troubleshooting

| Síntoma | Acción |
|---------|--------|
| API exit 137 / OOM en migrate | Parar API, `alembic upgrade head` vía `docker compose run`, luego up |
| Ledger ≠ 870000 | `python -m scripts.cli fire pipeline --phase f1` |
| Web unhealthy | Esperar build; `docker compose logs web --tail 50` |
| Coverage sin `sicoes_offline` | `python -m scripts.cli fire pipeline --phase f5` |
| Links inflados | `python -m scripts.cli fire pipeline --phase f12` |
| Clusters=0 | `python -m scripts.cli fire pipeline --phase f8` |

## 8. Evidencia de gate

Ver `docs/aura-incendios/gates.md`.  
Última verificación local debe mostrar:

```
ALL GATES PASSED
passed=… failed=0
```

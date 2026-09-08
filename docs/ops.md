# Operación local / MVP

## Puertos (host)

| Servicio | Puerto |
|----------|--------|
| API | 8010 |
| Web | 3010 |
| Postgres | 5434 |
| Redis | 6380 |
| MinIO API | 9010 |
| MinIO console | 9011 |

## Comandos útiles

```bash
cp .env.example .env
docker compose up -d --build
powershell -File scripts/verify_mvp.ps1

# Re-ingestar fixtures (sync)
python scripts/ingest.py --all --sync

# Encolar en worker ARQ
python scripts/ingest.py --source sicoes --enqueue

# Live scrape (opt-in) — REQUIERE PROXY_URL en .env
LIVE_SCRAPE=1 PROXY_URL=http://host.docker.internal:7890 \
  docker compose run --rm worker python scripts/ingest.py --source sicoes --sync --live
```

Ver sección **Proxy / VPN** abajo. Sin proxy, el scrape live falla a propósito.


## Reset de datos demo

```bash
docker compose down -v
docker compose up -d --build
```

## Proxy / VPN (protección de IP)

Live scrapes **no deben salir con tu IP residencial**. El proyecto exige proxy cuando `LIVE_SCRAPE=1`:

```env
LIVE_SCRAPE=1
REQUIRE_PROXY_FOR_LIVE=1
PROXY_URL=http://host.docker.internal:7890
```

1. Levantá tu VPN o proxy local (Clash, V2Ray, WireGuard+HTTP gateway, etc.).
2. Exponé un HTTP/SOCKS proxy en un puerto (ej. 7890).
3. Desde contenedores Docker Desktop usá `host.docker.internal`.
4. Verificá: `GET /v1/health` → `proxy.proxy_configured: true`.

Sin `PROXY_URL`/`HTTPS_PROXY`, cualquier fetch live lanza error a propósito.

Offline fixtures + `seed_history` **no** necesitan proxy.

## Seeds en arranque (opcional)

Por defecto el API solo ejecuta `gasto seed --profile demo` al levantar Docker.

| Variable | Efecto |
|----------|--------|
| `BOOT_FULL_SEED=1` | Además corre `history` + `cross` (histórico multi-año) |
| `BOOT_PUBLISH_SEED=1` | Corre `publish` (product-gate G10 + corpus incendios) — lento |

Recomendado en producción: correr `publish` manualmente tras el primer deploy:

```bash
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile publish
bash scripts/verify_mvp.sh  # incluye S16 product-gate
```

Para re-sembrar incendios sin repetir todo publish:

```bash
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile fire_demo --force
```

## Tests (solo Docker o venv)

```powershell
# Edicion local — deps SOLO en .venv (Python 3.12)
powershell -File .\scripts\setup_venv.ps1
.\.venv\Scripts\Activate.ps1

# Preferido para verificacion de producto — todo dentro de Docker
.\scripts\test_docker.ps1
```

No corras `pip install` contra el Python del sistema. No scrapes live desde el host sin proxy.

## Backup (dev)

```bash
docker compose exec postgres pg_dump -U gasto gasto_abierto > backup.sql
```

MinIO bucket `gasto-raw` contiene HTML/CSV/PDF crudos con `sha256` en tabla `document`.

## AURA Incendios (Plan 2)

Documentación Docker completa (arranque, pipeline F1–F13, verificación DoD, hardening prod):

→ [`docs/aura-incendios/DOCKER.md`](aura-incendios/DOCKER.md)

```powershell
# Verificar que el ledger fire está sano (API+DB+UI+artefactos)
powershell -File .\scripts\verify_fire_plan2.ps1

# Re-correr pipeline completo (lento: SICOES + PDF MINDEF)
powershell -File .\scripts\run_fire_pipeline.ps1
```

Gate duro: `amount_direct_verifiable` 2024 = **Bs 870.000**; script debe imprimir `ALL GATES PASSED`.

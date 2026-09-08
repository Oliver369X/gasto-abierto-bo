# Despliegue en VPS — Gasto Abierto

Guía para staging/producción en un servidor Linux (Docker Compose). Auth, charts y mapa live quedan diferidos (ver `docs/wave4-deferred.md`).

## 1. Prerrequisitos

- Docker Engine + Compose v2
- Dominio(s) con TLS (Caddy, nginx o reverse proxy del proveedor)
- `.env` derivado de [`.env.production.example`](../.env.production.example) — **sin secretos en git**

## 2. Variables críticas (URLs públicas)

| Variable | Desarrollo | VPS / producción |
|----------|------------|------------------|
| `NEXT_PUBLIC_API_URL` | puerto host mapeado (ej. 8010) | `https://api.tudominio.bo` |
| `CORS_ORIGINS` | origen del frontend dev | `https://tudominio.bo` |
| `API_HOST` | `0.0.0.0` | `0.0.0.0` (bind interno) |
| `API_PORT` | `8000` | `8000` (o el puerto interno elegido) |

Tras cambiar `NEXT_PUBLIC_API_URL`, reconstruir web:

```bash
docker compose up -d --build web
```

Opcional: `STRICT_PRODUCTION_ENV=1` hace que api/worker **no arranquen** si `CORS_ORIGINS` o `NEXT_PUBLIC_API_URL` apuntan a loopback.

## 3. Modo bridge (recomendado)

Puerto host → contenedor, igual que desarrollo:

```bash
cp .env.production.example .env
# editar dominios y contraseñas
docker compose up -d --build
```

Reverse proxy (ej. nginx) apunta al puerto host configurado en `.env` (`WEB_HOST_PORT`, `API_HOST_PORT`).

## 4. Modo host network (LIVE box)

Cuando el stack comparte red con el host (VPN/proxy local, sin NAT Docker):

1. En `docker-compose.override.yml` (local al servidor, no commitear):

```yaml
services:
  api:
    network_mode: host
    ports: []  # quitar mapeo bridge
```

2. El entrypoint de la API respeta `API_HOST` y `API_PORT`:

```env
API_HOST=0.0.0.0
API_PORT=8010
```

3. Healthcheck interno usa `API_PORT` (curl al puerto interno del contenedor).

4. Si Postgres/Redis corren en el host, ajustar URLs de conexión con los puertos host del `.env`.  # pragma: allowlist secret

## 5. LIVE_SCRAPE y proxy

Si `LIVE_SCRAPE=1`, **api y worker fallan al arranque** sin `PROXY_URL` (o `HTTPS_PROXY`) cuando `REQUIRE_PROXY_FOR_LIVE=1`.

```env
LIVE_SCRAPE=1
PROXY_URL=http://HOST_PROXY:7890
```

Verificar: `curl -s "$PUBLIC_API_URL/v1/health" | jq .proxy`

## 6. Seeds post-deploy

No habilitar `BOOT_PUBLISH_SEED=1` en producción salvo bootstrap controlado (lento).

```bash
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile publish
make staging-check
bash scripts/verify_mvp.sh
```

## 7. Checklist automatizado

```bash
make staging-check   # health + product-gate + budgets/totals
make go-live-check   # URLs públicas + presupuesto env + product-gate
```

Checklist manual completo: [`staging-go-no-go.md`](staging-go-no-go.md). Go-live: [`go-live.md`](go-live.md).

## 8. Coexistencia con otros stacks

Asignar puertos host distintos en `.env` si otra app ya usa 8000/5432/6379. Ver `docs/ops.md`.

# Wave 4 — alcance y diferido

Documento de cierre de la ola 4 hacia producción.

## Entregado (Wave 4)

| Prioridad | Ítem | Estado |
|-----------|------|--------|
| P1 | MEFP geo 60 → 117 ubicaciones + tests ≥100 | Hecho |
| P1 | Corpus offline presupuesto ampliado + `presupuesto_corpus` seed profile | Hecho |
| P1 | Docs LIVE `PRESUPUESTO_ABIERTO_DOWNLOAD_URLS` + manifest | Hecho |
| P1 | SICOES: validación respuesta vacía, backoff, soft-fail CUCE ficha | Hecho |
| P1 | Docs SICOES LIVE_SCRAPE/PROXY ampliadas | Hecho |
| P2 | Puertos compose configurables (`API_HOST_PORT`, etc.) + notas Opportunity | Hecho |
| P2 | `docs/PRODUCTION/staging-go-no-go.md` | Hecho |
| P2 | product-gate + verify_mvp + fire_demo robustos (CI offline) | Hecho |

## Diferido explícitamente (post Wave 4)

| Ítem | Motivo |
|------|--------|
| **Auth producción** | OIDC/SSO, RBAC — ver `AUDIT.md` |
| **Cliente TypeScript** | SDK tipado API pública |
| **Gráficos / charts** | Dashboard e histórico |
| **Mapa FIRMS live** | Requiere `MAP_KEY` + tiles |
| MEFP 352 ubicaciones completas | Merge export oficial GeoPackage |
| Excel / Google Drive | Política de datos |
| Secretos en repo | Env / vault only |

```bash
pytest tests/test_mefp_geo.py tests/test_fetch_presupuesto.py \
  tests/test_sicoes_resilience.py tests/test_fire_demo_argv.py -q
bash scripts/verify_mvp.sh  # SKIP_DOCKER=1 en CI unit shard
```

# Wave 3 — alcance y diferido

Documento de cierre de la ola 3 de producción. Lo implementado en esta rama vs. lo explícitamente fuera de alcance.

## Entregado (Wave 3)

| Prioridad | Ítem | Estado |
|-----------|------|--------|
| P0/P1 | Clasificador MEFP geo ampliado (27 → 60 ubicaciones) + tests | Hecho |
| P1 | `seed_fire_2024` migrado a `worker.gasto.seeds.fire_demo_impl` | Hecho |
| P1 | Fixtures histórico multi-año alineados presupuesto + contratos | Hecho |
| P1 | Ops documentadas para refresco oficial ~8M filas presupuesto | Hecho |
| P1 | SICOES: timeouts, detección HTML, fallback offline en CI | Hecho |
| P1 | `fire_demo` argv leak corregido (`force` kwarg) | Hecho |

## Diferido explícitamente (post Wave 3)

Estos ítems **no** están en esta rama. No abrir issues silenciosos — son decisiones de producto/infra.

| Ítem | Motivo | Referencia |
|------|--------|------------|
| **Auth producción** | OIDC/SSO, rotación de secretos, políticas RBAC | `AUDIT.md` § secrets |
| **Cliente TypeScript** | SDK tipado para API pública | roadmap Fase 3 |
| **Gráficos / charts** | Recharts/vis en dashboard e histórico | `AUDIT.md` UI refactor |
| **Mapa real (FIRMS live)** | Requiere `MAP_KEY` + tiles; demo usa fixtures | `docs/aura-incendios/gates.md` Ola 5 |
| MEFP 352 ubicaciones completas | Merge export oficial GeoPackage | `mefp_ubicaciones.json` |
| Retiro total `scripts/_legacy/` | Deadline 2026-08-14 tras migraciones restantes | `scripts/_legacy/README.md` |
| Excel / Google Drive | Fuera de alcance por política de datos | — |
| Secretos en repo | Nunca — usar env / vault en deploy | `docs/ops.md` |

**Memoria / volumen:** para el Parquet completo (~8M filas), montar ≥20 GB libres, usar `SEED_BATCH_SIZE` (default 50) y commits por gestión como en el profile `history`. Ajustar `shared_buffers` en la base de datos según RAM del host.

```bash
pytest tests/test_mefp_geo.py tests/test_history_fixture.py \
  tests/test_sicoes_resilience.py tests/test_fire_demo_argv.py -q

docker compose run --rm --entrypoint python api \
  -m scripts.cli gasto seed --profile fire_demo

docker compose run --rm --entrypoint python api \
  -m scripts.cli gasto seed --profile publish
```

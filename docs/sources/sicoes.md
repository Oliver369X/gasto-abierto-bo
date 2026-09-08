# SICOES

| Campo | Valor |
|-------|-------|
| URL | https://www.sicoes.gob.bo |
| Listado | https://www.sicoes.gob.bo/contrat/procesos.php |
| Formato | HTML dinámico |
| Rate | ≤ 1 req/s |
| Login | No (consulta pública) |
| Adapter | `sicoes` |

## Ética

Respetar carga del portal. Guardar raw HTML en MinIO. CI usa fixtures, no red.

## Resiliencia (Wave 3)

| Modo | Comportamiento |
|------|----------------|
| `SICOES_OFFLINE_FALLBACK=1` (default) | Timeout/red o HTML roto → fixture `procesos_sample.html` |
| `SICOES_FIXTURE_FALLBACK` | Ruta alternativa al HTML offline |
| `PLAYWRIGHT_TIMEOUT_MS` / `PLAYWRIGHT_RETRIES` | Control de timeout y reintentos |
| `inspect_list_html()` | Detecta mantenimiento, captcha, tablas ausentes |

Live fetch lanza `FetchError` tras reintentos; el adapter hace fallback automático cuando está habilitado. CI: `tests/test_sicoes_resilience.py` (siempre verde sin red).

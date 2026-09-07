# Fuente: Ministerio de Defensa (MINDEF)

| Campo | Valor |
|-------|-------|
| `source_id` | `mindef` |
| Adapter | `services/worker/adapters/mindef.py` |
| Uso | Vertical AURA Incendios — RPC, operaciones VIDECI |
| Licencia / acceso | Información pública institucional |
| Rate limit | Respetar ≤1 rps si live |

## URLs

- Rendiciones: https://www.mindef.gob.bo/index.php/rendicion-publica-de-cuentas/
- RPC Final 2024 PDF: https://www.mindef.gob.bo/wp-content/uploads/2026/01/12032025_INFORME_RPCFinal_2024_V15.pdf
- Presupuesto: https://www.mindef.gob.bo/index.php/presupuesto-de-las-estrategias-intitucionales/
- Contratos: https://www.mindef.gob.bo/index.php/contratos/

## Extracción MVP

1. Fixture JSON `tests/fixtures/mindef/rpc_2024.json` (offline)
2. Live: HTTP GET PDF → pdfplumber si hay texto; OCR solo fallback
3. Persist: `fire_operational` + `document` (hash)

## Advertencia

El pool «emergencia/desastre» (p. ej. Bs 168 M ejecutados 2024) **no** se atribuye completo a incendios. Ver clasificador `common/fire_classify.py`.

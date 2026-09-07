# Presupuesto Abierto

| Campo | Valor |
|-------|-------|
| URL | https://abierto.economiayfinanzas.gob.bo/ |
| Formato | HTML/JS; capturar XHR/JSON |
| Rate | ≤ 1 req/s |
| Adapter | `presupuesto_abierto` |

## Estrategia

1. Preferir fixtures / dumps JSON de entidades (`tests/fixtures/presupuesto_abierto/`).
2. Live: capturar XHR del portal con Playwright (Network → filtrar `json`/`api`).
3. Endpoints observados históricamente varían; documentar cada captura en esta ficha.
4. Fallback: datasets de presupuesto en datos.gob.bo vía adapter `agetic`.

### Forma canónica del JSON de fixture

```json
{
  "entidades": [
    {
      "entidad": "Ministerio de Educación",
      "nivel": "nacional",
      "gestion": 2025,
      "presupuesto_inicial": "50000000",
      "presupuesto_vigente": "51000000",
      "ejecucion": "25000000"
    }
  ]
}
```

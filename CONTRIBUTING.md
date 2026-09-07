# Cómo contribuir

Gracias por contribuir a **Gasto Abierto Bolivia**.

## Requisitos

- Docker + Docker Compose
- Python 3.12+ (para tests locales)
- Node.js 20+ / pnpm (para el frontend)

## Arranque local

```bash
cp .env.example .env
docker compose up -d --build
./scripts/verify_mvp.sh
```

API: http://localhost:8010/docs — Web: http://localhost:3010

## Cómo añadir un SourceAdapter

1. Crear `services/worker/adapters/<source_id>.py` implementando el protocolo:

```python
class SourceAdapter(Protocol):
    source_id: str
    def discover(self, cursor): ...
    def fetch(self, item) -> bytes: ...
    def parse(self, raw: bytes) -> list: ...
```

2. Añadir fixture HTML/CSV/PDF en `tests/fixtures/<source_id>/`
3. Test de contrato offline en `tests/contract/test_<source_id>.py`
4. Ficha de fuente en `docs/sources/<source_id>.md` (URL, robots, rate limit, campos, licencia)
5. Registrar el adapter en `services/worker/adapters/registry.py`
6. Abrir PR con evidencia de `pytest tests/contract`

## Reglas

- Solo datos **públicos** (ver `docs/legal/data-policy.md`)
- Rate limit ≤ 1 req/s salvo que la ficha indique otro valor
- Tests de parsers **sin red** en CI
- Commits claros (`feat:`, `fix:`, `docs:`)
- No commits de secretos ni `.env`

## Verificación

Definition of Success: `./scripts/verify_mvp.sh` (criterios S1–S12 en README).

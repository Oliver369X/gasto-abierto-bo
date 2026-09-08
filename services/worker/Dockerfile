FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY packages ./packages
COPY services/worker ./services/worker
COPY services/api ./services/api
COPY scripts ./scripts
COPY tests/fixtures ./tests/fixtures
COPY alembic.ini ./

RUN pip install --no-cache-dir -e ".[dev]" \
    && playwright install --with-deps chromium || true

ENV PYTHONPATH=/app/packages:/app/services
ENV DATABASE_URL=postgresql+psycopg://gasto:gasto_dev_change_me@postgres:5432/gasto_abierto
ENV REDIS_URL=redis://redis:6379/0

COPY services/worker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

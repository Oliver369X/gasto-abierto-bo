FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential tesseract-ocr tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY packages ./packages
COPY services/api ./services/api
COPY services/worker ./services/worker
COPY scripts ./scripts
COPY tests ./tests
COPY alembic.ini ./

RUN pip install --no-cache-dir -e ".[dev]"

ENV PYTHONPATH=/app/packages:/app/services
ENV DATABASE_URL=postgresql+psycopg://gasto:gasto_dev_change_me@postgres:5432/gasto_abierto

COPY services/api/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]

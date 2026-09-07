"""Gasto Abierto Bolivia — public read API (app factory + router mounts)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.deps import CORS_ORIGINS, RATE, get_db, limiter
from api.fire import create_fire_router
from api.routers import (
    alerts,
    audits,
    contracts,
    coverage,
    documents,
    entities,
    masters,
    meta,
    quality,
    suppliers,
)

app = FastAPI(
    title="Gasto Abierto Bolivia API",
    version="0.8.0",
    description="API pública de lectura para fiscalización ciudadana del gasto público.",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(create_fire_router(get_db, limiter, RATE))
app.include_router(meta.router)
app.include_router(entities.router)
app.include_router(contracts.router)
app.include_router(suppliers.router)
app.include_router(alerts.router)
app.include_router(audits.router)
app.include_router(documents.router)
app.include_router(quality.router)
app.include_router(coverage.router)
app.include_router(masters.router)

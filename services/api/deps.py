"""Shared FastAPI dependencies: DB session, rate limiter, CORS config."""
from __future__ import annotations

import os
from typing import Generator

from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session, sessionmaker

from schema.db import make_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
)
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3010").split(",")
    if o.strip()
]
RATE = os.getenv("RATE_LIMIT_PER_MINUTE", "120")

limiter = Limiter(key_func=get_remote_address)

_engine = make_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

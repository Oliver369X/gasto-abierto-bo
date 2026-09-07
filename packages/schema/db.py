from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from schema.models import Base


def get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
    )


def make_engine(url: str | None = None):
    return create_engine(url or get_database_url(), pool_pre_ping=True)


def make_session_factory(url: str | None = None):
    engine = make_engine(url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False), engine


def create_all(engine=None):
    eng = engine or make_engine()
    Base.metadata.create_all(eng)
    return eng

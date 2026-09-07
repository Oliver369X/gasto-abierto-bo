"""Fire pipeline session / run helpers."""
from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from schema.db import make_engine
from worker.persist import finish_run, start_run

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto"
)


def database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_session(url: str | None = None) -> Session:
    return sessionmaker(bind=make_engine(url or database_url()))()


def start_fire_run(session: Session, name: str, meta: dict[str, Any] | None = None):
    return start_run(session, name, meta=meta or {})


def finish_fire_run(session: Session, run, *, status: str = "success", records_out: int = 0) -> None:
    finish_run(session, run, status=status, records_out=records_out)

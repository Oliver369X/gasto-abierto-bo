"""Spanish-first HTTP error messages for the public API."""
from __future__ import annotations

from fastapi import HTTPException


def not_found(resource: str, *, detail: str | None = None) -> HTTPException:
    return HTTPException(404, detail or f"{resource} no encontrado/a")


def bad_request(message: str) -> HTTPException:
    return HTTPException(400, message)

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class JobEnvelope(BaseModel):
    """Stable job message — same shape can later go to Kafka."""

    source_id: str
    job_type: str  # discover | fetch | parse | normalize | alerts
    payload: dict[str, Any] = Field(default_factory=dict)
    attempt: int = 0
    idempotency_key: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

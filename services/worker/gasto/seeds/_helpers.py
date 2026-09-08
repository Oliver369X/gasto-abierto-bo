"""Shared helpers for seed profiles — memory-safe defaults and progress logs."""
from __future__ import annotations

import os
import sys
import time
from typing import Callable, TypeVar

T = TypeVar("T")


def seed_skip_storage() -> bool:
    """Skip MinIO raw writes during heavy offline seeds (saves RAM/IO in Docker)."""
    return os.getenv("SEED_SKIP_STORAGE", "1").strip().lower() in ("1", "true", "yes")


def seed_skip_alerts_during_ingest() -> bool:
    return os.getenv("SEED_SKIP_ALERTS_DURING_INGEST", "1").strip().lower() in ("1", "true", "yes")


def seed_batch_size(default: int = 50) -> int:
    raw = os.getenv("SEED_BATCH_SIZE", str(default)).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def seed_log(step: str, message: str = "") -> None:
    ts = time.strftime("%H:%M:%S")
    suffix = f" — {message}" if message else ""
    print(f"[seed {ts}] {step}{suffix}", flush=True)


def run_with_timeout(
    fn: Callable[[], T],
    *,
    label: str,
    timeout_seconds: int | None = None,
) -> T:
    """Optional wall-clock guard for seed steps (Unix only)."""
    raw = os.getenv("SEED_TIMEOUT_SECONDS", "").strip()
    limit = timeout_seconds
    if limit is None and raw.isdigit():
        limit = int(raw)
    if not limit or limit <= 0:
        return fn()

    import signal

    def _on_alarm(_signum: int, _frame: object) -> None:
        raise TimeoutError(f"{label} exceeded {limit}s (SEED_TIMEOUT_SECONDS)")

    prev = signal.signal(signal.SIGALRM, _on_alarm)
    signal.alarm(limit)
    try:
        seed_log(label, f"timeout={limit}s")
        return fn()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, prev)


def chunked(items: list[T], size: int) -> list[list[T]]:
    if size <= 0:
        return [items]
    return [items[i : i + size] for i in range(0, len(items), size)]

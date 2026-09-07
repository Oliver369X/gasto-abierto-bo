from __future__ import annotations

import time
from threading import Lock


class RateLimiter:
    """Simple token-bucket style minimum interval limiter."""

    def __init__(self, requests_per_second: float = 1.0) -> None:
        self.min_interval = 1.0 / max(requests_per_second, 0.01)
        self._last = 0.0
        self._lock = Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delta = now - self._last
            if delta < self.min_interval:
                time.sleep(self.min_interval - delta)
            self._last = time.monotonic()

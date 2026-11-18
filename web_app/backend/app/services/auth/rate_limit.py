"""A minimal in-memory, fixed-window rate limiter.

Single-process and dev-friendly, matching the "development-friendly setup
without compromising production architecture" brief: the interface
(`hit(key)`) is the thing that matters, not this backing store. Behind a
real deployment with multiple workers/instances, replace `_InMemoryStore`
with a shared store (e.g. Redis `INCR` + `EXPIRE`) — see README "Known
limitations".
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str) -> bool:
        """Records one attempt for `key`. Returns False once the window's
        attempt budget is exhausted (caller should reject the request)."""
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            while bucket and now - bucket[0] > self._window_seconds:
                bucket.popleft()
            if len(bucket) >= self._max_attempts:
                return False
            bucket.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

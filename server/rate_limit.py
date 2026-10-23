"""Per-caller rate limiting for state-changing requests.

A token bucket keyed by principal (or client address when anonymous),
applied to POST/PUT/DELETE so a runaway client or a stolen token cannot
exhaust the backend or the model budget.

Two limiters share one interface. `RateLimiter` keeps a token bucket in
this process and protects a single instance. `StoreRateLimiter` keeps a
fixed window per caller in the database (assessment B6), so every
instance of a hosted deployment counts the same requests; the
application picks it whenever the store is shared.
"""

import threading
import time

WRITE_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})


class RateLimiter:
    def __init__(self, limit=120, window_seconds=60, clock=time.monotonic):
        self.limit = max(1, int(limit))
        self.window = max(1, int(window_seconds))
        self._clock = clock
        self._buckets = {}
        self._lock = threading.Lock()

    # Buckets idle for a full window are evicted once the table outgrows
    # this (B6): a scan of many callers no longer grows memory for good.
    MAX_IDLE_BUCKETS = 10000

    def _evict(self, now):
        if len(self._buckets) < self.MAX_IDLE_BUCKETS:
            return
        stale = [k for k, (_, updated) in self._buckets.items()
                 if now - updated >= self.window]
        for k in stale:
            del self._buckets[k]

    def check(self, key):
        """Return (allowed, remaining, retry_after_seconds)."""
        now = self._clock()
        with self._lock:
            self._evict(now)
            tokens, updated = self._buckets.get(key, (float(self.limit), now))
            # Refill continuously rather than in fixed windows, so a
            # caller cannot burst twice across a window boundary.
            tokens = min(
                float(self.limit),
                tokens + (now - updated) * (self.limit / self.window),
            )
            if tokens < 1.0:
                retry_after = max(1, int((1.0 - tokens) * (self.window / self.limit)) + 1)
                self._buckets[key] = (tokens, now)
                return False, 0, retry_after
            tokens -= 1.0
            self._buckets[key] = (tokens, now)
            return True, int(tokens), 0


class StoreRateLimiter:
    """A fixed window per caller, counted in the store.

    `check` costs one atomic read-modify-write; windows older than two
    back are dropped as a caller's new window opens, so the table stays
    the size of the active callers. A store outage lets the request
    through rather than refusing every write while the database is down:
    the request will fail on its own data access if the outage is real.
    """

    def __init__(self, store, limit=120, window_seconds=60, clock=time.time):
        self.store = store
        self.limit = max(1, int(limit))
        self.window = max(1, int(window_seconds))
        self._clock = clock

    def check(self, key):
        now = self._clock()
        window_start = int(now // self.window) * self.window
        try:
            count = self.store.rate_hit(key, window_start, window_start - 2 * self.window)
        except Exception:
            return True, self.limit, 0
        if count > self.limit:
            return False, 0, max(1, int(window_start + self.window - now) + 1)
        return True, self.limit - count, 0


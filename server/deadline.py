"""A wall-clock limit for code this process cannot interrupt.

A custom stage or an agent runtime is Python running in this process
(ADR 0020, ADR 0021). Python cannot stop a thread, so what a deadline
can do is bounded: the call runs on a worker thread, the caller waits at
most `seconds`, and on timeout the caller gets `Timeout` and moves on,
recording the failure, while the abandoned thread finishes on its own
and its result is discarded. That is enough to keep one hung stage from
hanging a run (assessment G10); it is not a sandbox.
"""

import concurrent.futures
import os
from contextvars import copy_context

DEFAULT_STAGE_SECONDS = 120.0
DEFAULT_RUNTIME_SECONDS = 60.0


class Timeout(TimeoutError):
    """The call did not finish within its deadline."""


def seconds_from_env(name, default):
    """A positive number of seconds from the environment, or the default."""
    raw = os.environ.get(name)
    if raw in (None, ""):
        return float(default)
    try:
        value = float(raw)
    except ValueError:
        return float(default)
    return value if value > 0 else float(default)


def call_with_deadline(fn, seconds, *args, **kwargs):
    """Run `fn(*args, **kwargs)` on a worker thread; raise Timeout after
    `seconds`. The function's own exceptions propagate unchanged."""
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    # Carry the actual requester's authorization context into this call.
    # A fresh copy per invocation keeps worker changes out of later requests.
    future = executor.submit(copy_context().run, fn, *args, **kwargs)
    try:
        return future.result(timeout=seconds)
    except concurrent.futures.TimeoutError:
        raise Timeout(f"did not finish within {seconds:g} s") from None
    finally:
        # Never wait for an abandoned call; the thread ends when it ends.
        executor.shutdown(wait=False)

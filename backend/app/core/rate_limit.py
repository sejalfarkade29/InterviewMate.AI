"""Very small in-memory rate limiter for login attempts.

Good enough for a single server process. For multiple servers, move this
to Redis (planned for the final hardening phase).
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, status

_attempts: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(key: str, limit: int = 10, window_seconds: int = 300) -> None:
    now = time.monotonic()
    q = _attempts[key]
    while q and now - q[0] > window_seconds:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please wait a few minutes and try again.",
        )
    q.append(now)


def reset_rate_limits() -> None:
    _attempts.clear()

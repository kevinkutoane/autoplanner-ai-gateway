"""Rate limiting abstraction and in-memory sliding window implementation."""

import asyncio
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import Dict, Tuple

from app.config import settings


class RateLimiter(ABC):
    """Abstract rate limiter interface for quota and request throttling."""

    @abstractmethod
    async def is_allowed(self, client_id: str) -> Tuple[bool, int, int]:
        """Checks if a request from client_id is within allowed rate limits.

        Returns:
            Tuple[bool, int, int]: (allowed, remaining_quota, retry_after_seconds)
        """
        pass


class InMemoryRateLimiter(RateLimiter):
    """In-memory sliding-window rate limiter.

    NOTE: In-memory rate limiting is suitable for local development and single-instance
    staging validation, but is NOT distributed production enforcement when multiple
    Cloud Run instances or auto-scaling replicas are active. Distributed production
    enforcement should bind to a shared distributed store (such as Redis or Cloud Armor).
    """

    def __init__(self, limit_rpm: int = 60, window_seconds: int = 60):
        self._limit_rpm = limit_rpm
        self._window_seconds = window_seconds
        self._requests: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_id: str) -> Tuple[bool, int, int]:
        now = time.time()
        window_start = now - self._window_seconds

        async with self._lock:
            queue = self._requests[client_id]

            # Purge timestamps outside sliding window
            while queue and queue[0] <= window_start:
                queue.popleft()

            current_count = len(queue)
            limit = self._limit_rpm if self._limit_rpm > 0 else settings.RATE_LIMIT_RPM

            if current_count >= limit:
                # Oldest timestamp tells us when the earliest slot frees up
                oldest = queue[0]
                retry_after = max(1, int(oldest + self._window_seconds - now))
                return False, 0, retry_after

            queue.append(now)
            remaining = max(0, limit - (current_count + 1))
            return True, remaining, 0

    async def reset(self) -> None:
        """Clear all in-memory tracking (useful for testing)."""
        async with self._lock:
            self._requests.clear()


# Default singleton instance
_default_rate_limiter: RateLimiter = InMemoryRateLimiter()


def get_rate_limiter() -> RateLimiter:
    return _default_rate_limiter


def set_rate_limiter(limiter: RateLimiter) -> None:
    global _default_rate_limiter
    _default_rate_limiter = limiter

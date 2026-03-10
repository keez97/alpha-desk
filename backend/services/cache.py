"""
Thread-safe TTL cache implementation for AlphaDesk.

Provides in-memory caching with configurable per-key expiry times,
automatic cleanup of expired entries, and cache statistics.
"""

import logging
import threading
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from backend.config import (
    CACHE_TTL_FUNDAMENTALS,
    CACHE_TTL_HISTORY,
    CACHE_TTL_MACRO,
    CACHE_TTL_QUOTE,
    CACHE_TTL_SECTOR,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TTLCache:
    """
    Thread-safe in-memory cache with configurable time-to-live (TTL) per key.

    Automatically expires entries based on their TTL and cleans them up on access.
    Provides statistics on cache performance.
    """

    def __init__(self):
        """Initialize the TTL cache."""
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._hit_count = 0
        self._miss_count = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.

        Returns None if key does not exist or has expired.
        Automatically removes expired entries.
        Logs cache hits and misses at debug level.

        Args:
            key: The cache key to retrieve.

        Returns:
            The cached value, or None if not found or expired.
        """
        with self._lock:
            if key not in self._cache:
                self._miss_count += 1
                logger.debug(f"Cache miss for key: {key}")
                return None

            entry = self._cache[key]

            # Check if entry has expired
            if time.time() > entry["expires_at"]:
                del self._cache[key]
                self._miss_count += 1
                logger.debug(f"Cache expired for key: {key}")
                return None

            self._hit_count += 1
            logger.debug(f"Cache hit for key: {key}")
            return entry["value"]

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """
        Store a value in the cache with a specified TTL.

        Args:
            key: The cache key.
            value: The value to cache.
            ttl_seconds: Time-to-live in seconds.
        """
        with self._lock:
            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl_seconds,
            }
            logger.debug(f"Cache set for key: {key} with TTL: {ttl_seconds}s")

    def invalidate(self, key: str) -> None:
        """
        Manually invalidate a specific cache entry.

        Args:
            key: The cache key to invalidate.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache invalidated for key: {key}")

    def clear(self) -> None:
        """
        Clear all entries from the cache.
        """
        with self._lock:
            self._cache.clear()
            logger.debug("Cache cleared")

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary containing:
                - hit_count: Total number of cache hits.
                - miss_count: Total number of cache misses.
                - hit_rate: Hit rate as a percentage (0-100).
                - entry_count: Current number of entries in cache.
        """
        with self._lock:
            total_requests = self._hit_count + self._miss_count
            hit_rate = (
                (self._hit_count / total_requests * 100)
                if total_requests > 0
                else 0.0
            )

            return {
                "hit_count": self._hit_count,
                "miss_count": self._miss_count,
                "hit_rate": hit_rate,
                "entry_count": len(self._cache),
            }


# Module-level singleton instance
cache = TTLCache()


def cached(key_prefix: str, ttl: int) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to wrap a function with cache logic.

    Checks cache first before executing the function. On cache miss,
    executes the function and stores the result with the specified TTL.

    Args:
        key_prefix: Prefix for the cache key.
        ttl: Time-to-live in seconds for cached results.

    Returns:
        A decorator function.

    Example:
        @cached(key_prefix="quote", ttl=CACHE_TTL_QUOTE)
        def get_stock_quote(symbol: str) -> float:
            # Function implementation
            return price
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Build cache key from function name, prefix, and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Cache miss: call function and store result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator

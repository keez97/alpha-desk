"""
Thread-safe circuit breaker implementation for AlphaDesk data sources.

Implements a 3-state circuit breaker per data source:
  CLOSED (normal) → failures → OPEN (fail-fast) → cooldown → HALF_OPEN (probe)
  HALF_OPEN → 2 successes → CLOSED or 1 failure → OPEN

Each data source (yahoo_direct, fds, yfinance) has its own breaker with
tuned thresholds to handle source-specific failure patterns.
"""

import logging
import threading
import time
from typing import Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"           # Normal operation
    OPEN = "OPEN"               # Fail-fast mode (too many failures)
    HALF_OPEN = "HALF_OPEN"     # Probing after cooldown expires


class CircuitBreaker:
    """
    Thread-safe circuit breaker for a single data source.

    Tracks failures and transitions between CLOSED/OPEN/HALF_OPEN states.
    In HALF_OPEN, requires 2 consecutive successes to return to CLOSED.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int,
        cooldown_seconds: int,
    ):
        """
        Initialize a circuit breaker.

        Args:
            name: Name of the data source (e.g., "yahoo_direct")
            failure_threshold: Number of failures before opening the circuit
            cooldown_seconds: Seconds to wait before transitioning to HALF_OPEN
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds

        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._consecutive_successes = 0
        self._opened_at: Optional[float] = None
        self._last_failure_at: Optional[float] = None
        self._last_failure_reason: Optional[str] = None

    def is_available(self) -> bool:
        """
        Check if the circuit breaker allows requests.

        Returns True if CLOSED or HALF_OPEN (ready to probe).
        Returns False if OPEN (fail-fast mode).

        Returns:
            True if requests should be attempted, False otherwise.
        """
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.HALF_OPEN:
                return True

            # OPEN state
            if self._opened_at is None:
                return False

            # Check if cooldown has expired
            elapsed = time.time() - self._opened_at
            if elapsed >= self.cooldown_seconds:
                # Transition to HALF_OPEN to probe
                logger.info(
                    f"Circuit breaker '{self.name}' cooldown expired, "
                    f"entering HALF_OPEN state"
                )
                self._state = CircuitState.HALF_OPEN
                self._consecutive_successes = 0
                return True

            return False

    def record_success(self) -> None:
        """
        Record a successful request.

        - In CLOSED state: reset failure count
        - In HALF_OPEN state: increment consecutive successes,
          transition to CLOSED after 2 successes
        """
        with self._lock:
            if self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0
                logger.debug(f"Circuit breaker '{self.name}': success in CLOSED state, reset failures")

            elif self._state == CircuitState.HALF_OPEN:
                self._consecutive_successes += 1
                logger.debug(
                    f"Circuit breaker '{self.name}': success in HALF_OPEN state "
                    f"({self._consecutive_successes}/2)"
                )

                if self._consecutive_successes >= 2:
                    # Transition back to CLOSED
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._consecutive_successes = 0
                    logger.info(
                        f"Circuit breaker '{self.name}' recovered, "
                        f"entering CLOSED state"
                    )

    def record_failure(self) -> None:
        """
        Record a failed request.

        - In CLOSED state: increment failure count, transition to OPEN if threshold reached
        - In HALF_OPEN state: immediately transition to OPEN
        """
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                # Fail immediately during probe
                self._state = CircuitState.OPEN
                self._opened_at = time.time()
                self._failure_count = self.failure_threshold
                self._last_failure_at = time.time()
                logger.warning(
                    f"Circuit breaker '{self.name}': failure during probe, "
                    f"entering OPEN state"
                )

            else:  # CLOSED or OPEN
                self._failure_count += 1
                self._last_failure_at = time.time()

                if self._state == CircuitState.CLOSED and self._failure_count >= self.failure_threshold:
                    # Transition to OPEN
                    self._state = CircuitState.OPEN
                    self._opened_at = time.time()
                    logger.warning(
                        f"Circuit breaker '{self.name}': failure threshold reached "
                        f"({self._failure_count}/{self.failure_threshold}), entering OPEN state"
                    )
                else:
                    logger.debug(
                        f"Circuit breaker '{self.name}': failure recorded "
                        f"({self._failure_count}/{self.failure_threshold})"
                    )

    def force_open(self, reason: str) -> None:
        """
        Immediately open the circuit with an extended cooldown.

        Used for critical errors (e.g., 402 Insufficient Credits) that
        require an extended wait period.

        Args:
            reason: Reason for forcing the circuit open (e.g., "402 Insufficient Credits")
        """
        with self._lock:
            self._state = CircuitState.OPEN
            self._opened_at = time.time()
            self._last_failure_reason = reason
            # Extended cooldown: 2x the normal cooldown
            self.cooldown_seconds = int(self.cooldown_seconds * 2)
            self._failure_count = self.failure_threshold
            self._last_failure_at = time.time()
            logger.error(
                f"Circuit breaker '{self.name}' forced OPEN: {reason} "
                f"(extended cooldown: {self.cooldown_seconds}s)"
            )

    def status(self) -> Dict:
        """
        Get the current status of the circuit breaker.

        Returns:
            Dict with keys:
                - name: Data source name
                - state: Current state (CLOSED, OPEN, HALF_OPEN)
                - failure_count: Current failure count
                - opened_at: Timestamp when opened (or None if not open)
                - last_failure: Timestamp of last failure (or None)
                - reason: Reason for forced open (or None)
                - cooldown_remaining: Seconds until available (or None if CLOSED)
        """
        with self._lock:
            cooldown_remaining = None
            if self._state == CircuitState.OPEN and self._opened_at is not None:
                cooldown_remaining = max(
                    0,
                    self.cooldown_seconds - (time.time() - self._opened_at),
                )

            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "opened_at": self._opened_at,
                "last_failure": self._last_failure_at,
                "reason": self._last_failure_reason,
                "cooldown_remaining": cooldown_remaining,
            }

    def reset(self) -> None:
        """Reset the circuit breaker to CLOSED state. For testing/debug only."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._consecutive_successes = 0
            self._opened_at = None
            self._last_failure_at = None
            self._last_failure_reason = None
            logger.info(f"Circuit breaker '{self.name}' reset to CLOSED state")


# Module-level instances for each data source
# Tuned thresholds based on source reliability patterns

_breaker_yahoo_direct = CircuitBreaker(
    name="yahoo_direct",
    failure_threshold=8,      # Primary source, tolerant of transients
    cooldown_seconds=90,      # Railway IP gets 429'd periodically
)

_breaker_fds = CircuitBreaker(
    name="fds",
    failure_threshold=3,      # Dead API ($0.01), fail fast
    cooldown_seconds=300,     # 5 minute cooldown before retry
)

_breaker_yfinance = CircuitBreaker(
    name="yfinance",
    failure_threshold=10,     # Last resort, very tolerant
    cooldown_seconds=90,      # Standard cooldown
)

# Mapping for easy lookup
_breakers: Dict[str, CircuitBreaker] = {
    "yahoo_direct": _breaker_yahoo_direct,
    "fds": _breaker_fds,
    "yfinance": _breaker_yfinance,
}


def get_breaker(name: str) -> CircuitBreaker:
    """
    Get the circuit breaker for a data source.

    Args:
        name: Data source name (yahoo_direct, fds, or yfinance)

    Returns:
        CircuitBreaker instance for the source

    Raises:
        KeyError: If source name is not recognized
    """
    if name not in _breakers:
        raise KeyError(
            f"Unknown data source: {name}. "
            f"Must be one of: {list(_breakers.keys())}"
        )
    return _breakers[name]


def all_status() -> Dict[str, Dict]:
    """
    Get status of all circuit breakers.

    Returns:
        Dict mapping source names to their status dicts.
        Useful for debug endpoints.
    """
    return {name: breaker.status() for name, breaker in _breakers.items()}

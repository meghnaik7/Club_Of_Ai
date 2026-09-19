"""
Lightweight Circuit Breaker for External AI Providers.
Tracks provider health, trips OPEN after repeated failures to protect latency,
and transitions to HALF-OPEN after a cooldown window to probe service recovery.
"""
import time
import threading
import logging
from enum import Enum
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"        # Normal operation: requests pass through
    OPEN = "OPEN"            # Tripped: requests blocked, immediate fallback
    HALF_OPEN = "HALF_OPEN"  # Probing: limited test request allowed


class CircuitBreaker:
    """
    Thread-safe circuit breaker scoped per AI provider.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
        half_open_success_threshold: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_success_threshold = half_open_success_threshold

        self._lock = threading.Lock()
        # provider -> {"state": CircuitState, "failure_count": int, "success_count": int, "last_failure_time": float}
        self._registry: Dict[str, Dict] = {}

    def _get_provider_state(self, provider: str) -> Dict:
        if provider not in self._registry:
            self._registry[provider] = {
                "state": CircuitState.CLOSED,
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": 0.0,
            }
        return self._registry[provider]

    def can_execute(self, provider: str) -> Tuple[bool, Optional[float]]:
        """
        Determines if a request can be dispatched to the provider.
        Returns:
            (can_execute: bool, cooldown_remaining: Optional[float])
        """
        with self._lock:
            info = self._get_provider_state(provider)
            now = time.time()
            current_state = info["state"]

            if current_state == CircuitState.CLOSED:
                return True, None

            if current_state == CircuitState.OPEN:
                elapsed = now - info["last_failure_time"]
                if elapsed >= self.cooldown_seconds:
                    logger.info(
                        f"Circuit breaker for provider '{provider}' cooldown elapsed ({elapsed:.1f}s). "
                        f"Transitioning to HALF_OPEN."
                    )
                    info["state"] = CircuitState.HALF_OPEN
                    info["success_count"] = 0
                    return True, None
                else:
                    remaining = self.cooldown_seconds - elapsed
                    return False, remaining

            if current_state == CircuitState.HALF_OPEN:
                # In HALF_OPEN, we permit a test request
                return True, None

            return True, None

    def record_success(self, provider: str) -> None:
        """Records a successful response from the provider."""
        with self._lock:
            info = self._get_provider_state(provider)
            current_state = info["state"]

            if current_state == CircuitState.HALF_OPEN:
                info["success_count"] += 1
                if info["success_count"] >= self.half_open_success_threshold:
                    logger.info(
                        f"Circuit breaker for provider '{provider}' recovered after trial success. "
                        f"Resetting to CLOSED."
                    )
                    info["state"] = CircuitState.CLOSED
                    info["failure_count"] = 0
                    info["success_count"] = 0
            elif current_state == CircuitState.CLOSED:
                info["failure_count"] = 0

    def record_failure(self, provider: str, error: Optional[Exception] = None) -> None:
        """Records a failure from the provider."""
        with self._lock:
            info = self._get_provider_state(provider)
            now = time.time()
            info["last_failure_time"] = now

            if info["state"] == CircuitState.HALF_OPEN:
                logger.warning(
                    f"Circuit breaker test failed in HALF_OPEN for provider '{provider}'. "
                    f"Tripping back to OPEN."
                )
                info["state"] = CircuitState.OPEN
                info["failure_count"] = self.failure_threshold
                info["success_count"] = 0
            else:
                info["failure_count"] += 1
                if info["failure_count"] >= self.failure_threshold and info["state"] == CircuitState.CLOSED:
                    logger.warning(
                        f"Circuit breaker tripped to OPEN for provider '{provider}' "
                        f"after {info['failure_count']} consecutive failures. Error: {error}"
                    )
                    info["state"] = CircuitState.OPEN

    def get_state(self, provider: str) -> CircuitState:
        with self._lock:
            # Check if cooldown has elapsed to auto-refresh state
            info = self._get_provider_state(provider)
            if info["state"] == CircuitState.OPEN:
                if (time.time() - info["last_failure_time"]) >= self.cooldown_seconds:
                    info["state"] = CircuitState.HALF_OPEN
                    info["success_count"] = 0
            return info["state"]

    def reset(self, provider: Optional[str] = None) -> None:
        """Resets the circuit breaker state for a specific or all providers."""
        with self._lock:
            if provider:
                if provider in self._registry:
                    self._registry[provider] = {
                        "state": CircuitState.CLOSED,
                        "failure_count": 0,
                        "success_count": 0,
                        "last_failure_time": 0.0,
                    }
            else:
                self._registry.clear()


# Global circuit breaker instance
circuit_breaker = CircuitBreaker()

"""
Bounded Retry Mechanism with Exponential Backoff and Jitter.
Enforces retry limits, exponential backoff, retry hint parsing (Retry-After),
and strict exclusion of non-retryable errors (auth, content safety, invalid args).
"""
import time
import random
import logging
from typing import Callable, Any, Optional, Tuple, TypeVar
from app.ai.errors import AIError, ErrorCategory, classify_exception

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryPolicy:
    """
    Configurable exponential backoff retry policy.
    """

    def __init__(
        self,
        max_retries: int = 2,
        initial_delay: float = 0.5,
        backoff_factor: float = 2.0,
        max_delay: float = 10.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.jitter = jitter

    def calculate_delay(self, attempt: int, retry_after_hint: Optional[float] = None) -> float:
        """
        Calculates delay for attempt (0-indexed).
        Respects Retry-After hint from provider if provided.
        """
        if retry_after_hint is not None and retry_after_hint > 0:
            return min(self.max_delay, float(retry_after_hint))

        delay = self.initial_delay * (self.backoff_factor ** attempt)
        if self.jitter:
            delay += random.uniform(0.0, 0.25 * delay)
        return min(self.max_delay, delay)

    def execute(
        self,
        fn: Callable[..., T],
        *args,
        operation_name: str = "LLM Call",
        on_retry: Optional[Callable[[int, AIError, float], None]] = None,
        **kwargs,
    ) -> Tuple[T, int]:
        """
        Executes fn(*args, **kwargs) with bounded retries.
        Returns:
            Tuple[Result, total_attempts_made]
        Raises:
            AIError if retries exhausted or non-retryable error occurs.
        """
        attempts = 0
        last_classified_error: Optional[AIError] = None

        while attempts <= self.max_retries:
            attempts += 1
            try:
                result = fn(*args, **kwargs)
                return result, attempts
            except Exception as raw_exc:
                classified_err = classify_exception(raw_exc)
                last_classified_error = classified_err

                # Non-retryable errors abort immediately
                if not classified_err.retryable or classified_err.category == ErrorCategory.NON_RETRYABLE:
                    logger.warning(
                        f"[{operation_name}] Permanent error encountered ({classified_err.code}): {classified_err.message}. "
                        f"Aborting without retry."
                    )
                    raise classified_err

                # If we've reached max_retries, stop and raise
                if attempts > self.max_retries:
                    logger.warning(
                        f"[{operation_name}] Exhausted maximum retries ({self.max_retries}) on error ({classified_err.code}): {classified_err.message}."
                    )
                    raise classified_err

                # Calculate backoff delay
                retry_after = classified_err.details.get("retry_after")
                delay = self.calculate_delay(attempts - 1, retry_after_hint=retry_after)

                logger.info(
                    f"[{operation_name}] Temporary failure ({classified_err.code}). "
                    f"Attempt {attempts}/{self.max_retries}. Retrying in {delay:.2f}s..."
                )

                if on_retry:
                    on_retry(attempts, classified_err, delay)

                time.sleep(delay)

        if last_classified_error:
            raise last_classified_error
        raise AIError(f"[{operation_name}] Execution failed after {attempts} attempts.")


# Default global retry policy
default_retry_policy = RetryPolicy()

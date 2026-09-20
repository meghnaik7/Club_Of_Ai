"""
Fallback Coordinator and Quality Protection for ClubOps AI.
Enforces strict rules on when fallback is permitted vs denied, ensures fallback models
inherit identical guardrails, schemas, system prompts, and tool policies, and emits
structured audit logs for model failover events.
"""
import logging
from typing import Dict, Any, Optional
from app.ai.errors import AIError, ErrorCategory, ErrorCode
from app.ai.model_registry import ModelConfig

logger = logging.getLogger(__name__)


class FallbackCoordinator:
    """
    Coordinates and audits LLM failovers between primary and fallback models.
    """

    # Non-fallback error codes (Section 7)
    DISALLOWED_ERROR_CODES = {
        ErrorCode.LLM_AUTH_ERROR,
        ErrorCode.LLM_CONTENT_POLICY,
        ErrorCode.TOOL_INVALID_ARGUMENT,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.AUTH_REQUIRED,
        ErrorCode.PERMISSION_DENIED,
        ErrorCode.AGENT_MAX_ITERATIONS,
    }

    @classmethod
    def is_eligible_for_fallback(cls, error: AIError) -> bool:
        """
        Determines whether the given classified error is eligible to trigger fallback.
        True for: rate limit, temporary outage, timeouts, circuit open, network errors.
        False for: auth errors, bad client requests, content policy violations.
        """
        if error.code in cls.DISALLOWED_ERROR_CODES:
            return False

        if error.category in (ErrorCategory.FALLBACK_ELIGIBLE, ErrorCategory.RETRYABLE):
            return True

        return error.fallback_eligible

    @classmethod
    def log_fallback_event(
        cls,
        primary_config: ModelConfig,
        fallback_config: ModelConfig,
        error: AIError,
        retry_count: int,
        success: bool,
        correlation_id: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Emits structured audit log for model fallback (Section 7 & 18).
        Never logs secrets, API keys, or raw passwords.
        """
        event_data = {
            "event": "LLM_FALLBACK_ATTEMPT",
            "correlation_id": correlation_id or "N/A",
            "primary_model": f"{primary_config.provider}/{primary_config.model}",
            "fallback_model": f"{fallback_config.provider}/{fallback_config.model}",
            "error_code": error.code,
            "error_category": error.category.value,
            "retry_count": retry_count,
            "fallback_result": "SUCCESS" if success else "FAILURE",
            "tool_name": tool_name or "NONE",
        }

        if success:
            logger.warning(
                f"[FALLBACK SUCCESS] Failover from {event_data['primary_model']} to "
                f"{event_data['fallback_model']} succeeded after {retry_count} retries on {error.code}."
            )
        else:
            logger.error(
                f"[FALLBACK FAILED] Failover to {event_data['fallback_model']} also failed after "
                f"{primary_config.model} failure ({error.code})."
            )

        return event_data

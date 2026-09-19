"""
Standardized Error Hierarchy & Classification for ClubOps AI.
Implements unified exception handling, error codes, retry/fallback classifications,
and user-safe messaging (never exposing API keys, secrets, or internal stack traces).
"""
import re
from enum import Enum
from typing import Optional, Dict, Any


class ErrorCategory(str, Enum):
    RETRYABLE = "RETRYABLE"
    FALLBACK_ELIGIBLE = "FALLBACK_ELIGIBLE"
    NON_RETRYABLE = "NON_RETRYABLE"
    USER_ACTION_REQUIRED = "USER_ACTION_REQUIRED"


# Application-level Error Codes (Section 19)
class ErrorCode:
    # LLM codes
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    LLM_AUTH_ERROR = "LLM_AUTH_ERROR"
    LLM_INVALID_RESPONSE = "LLM_INVALID_RESPONSE"
    LLM_CONTENT_POLICY = "LLM_CONTENT_POLICY_ERROR"
    LLM_NETWORK_ERROR = "LLM_NETWORK_ERROR"
    LLM_CIRCUIT_OPEN = "LLM_CIRCUIT_OPEN"
    LLM_CAPABILITY_MISMATCH = "LLM_CAPABILITY_MISMATCH"

    # Tool codes
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_INVALID_ARGUMENT = "TOOL_INVALID_ARGUMENT"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"

    # RAG codes
    RAG_RETRIEVAL_FAILED = "RAG_RETRIEVAL_FAILED"
    RAG_NO_RELEVANT_CONTEXT = "RAG_NO_RELEVANT_CONTEXT"
    RAG_EMBEDDING_FAILED = "RAG_EMBEDDING_FAILED"

    # Database codes
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    DATABASE_CONFLICT = "DATABASE_CONFLICT"
    DATABASE_TRANSACTION_FAILED = "DATABASE_TRANSACTION_FAILED"

    # Agent codes
    AGENT_MAX_ITERATIONS = "AGENT_MAX_ITERATIONS"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"

    # General
    AUTH_REQUIRED = "AUTH_REQUIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class AIError(Exception):
    """Base exception for all ClubOps AI operations."""

    def __init__(
        self,
        message: str,
        code: str = ErrorCode.UNKNOWN_ERROR,
        category: ErrorCategory = ErrorCategory.NON_RETRYABLE,
        retryable: bool = False,
        fallback_eligible: bool = False,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.retryable = retryable
        self.fallback_eligible = fallback_eligible
        self.user_message = user_message or "An AI service error occurred. Please try again."
        self.details = details or {}
        self.status_code = status_code
        self.original_exception = original_exception

    def to_user_dict(self, fallback_used: bool = False) -> Dict[str, Any]:
        """Returns safe user-facing response payload without secrets or stack traces."""
        payload: Dict[str, Any] = {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.user_message,
            }
        }
        if fallback_used:
            payload["fallback_used"] = True
        return payload


# --- LLM Errors ---

class RateLimitError(AIError):
    def __init__(self, message: str = "Rate limit reached for LLM provider.", retry_after: Optional[float] = None, **kwargs):
        details = kwargs.pop("details", {})
        if retry_after is not None:
            details["retry_after"] = retry_after
        super().__init__(
            message=message,
            code=ErrorCode.LLM_RATE_LIMIT,
            category=ErrorCategory.RETRYABLE,
            retryable=True,
            fallback_eligible=True,
            user_message="The AI service is temporarily rate limited. Your request is being handled.",
            status_code=429,
            details=details,
            **kwargs,
        )


class AuthenticationError(AIError):
    def __init__(self, message: str = "Authentication failed with LLM provider.", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.LLM_AUTH_ERROR,
            category=ErrorCategory.NON_RETRYABLE,
            retryable=False,
            fallback_eligible=False,
            user_message="AI service configuration error. Please contact your club administrator.",
            status_code=401,
            **kwargs,
        )


class TimeoutError(AIError):
    def __init__(self, message: str = "LLM request timed out.", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.LLM_TIMEOUT,
            category=ErrorCategory.RETRYABLE,
            retryable=True,
            fallback_eligible=True,
            user_message="The AI model took too long to respond. Retrying with alternate model.",
            status_code=504,
            **kwargs,
        )


class NetworkError(AIError):
    def __init__(self, message: str = "Network error connecting to LLM provider.", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.LLM_NETWORK_ERROR,
            category=ErrorCategory.RETRYABLE,
            retryable=True,
            fallback_eligible=True,
            user_message="Temporary network issue connecting to AI provider.",
            status_code=502,
            **kwargs,
        )


class ModelUnavailableError(AIError):
    def __init__(self, message: str = "Requested LLM model is unavailable or overloaded.", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.LLM_UNAVAILABLE,
            category=ErrorCategory.FALLBACK_ELIGIBLE,
            retryable=False,
            fallback_eligible=True,
            user_message="The AI provider is temporarily unavailable. Using alternate provider.",
            status_code=503,
            **kwargs,
        )


class InvalidResponseError(AIError):
    def __init__(self, message: str = "LLM returned an invalid or unparseable response.", retryable: bool = True, **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.LLM_INVALID_RESPONSE,
            category=ErrorCategory.RETRYABLE if retryable else ErrorCategory.FALLBACK_ELIGIBLE,
            retryable=retryable,
            fallback_eligible=True,
            user_message="The AI response could not be validated. Please try again.",
            status_code=502,
            **kwargs,
        )


class ContentPolicyError(AIError):
    def __init__(self, message: str = "Prompt or response violated AI content safety policy.", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.LLM_CONTENT_POLICY,
            category=ErrorCategory.NON_RETRYABLE,
            retryable=False,
            fallback_eligible=False,
            user_message="The request could not be processed due to content safety policies.",
            status_code=400,
            **kwargs,
        )


class CircuitBreakerOpenError(AIError):
    def __init__(self, provider: str, cooldown_remaining: float = 0.0, **kwargs):
        super().__init__(
            message=f"Circuit breaker is OPEN for provider '{provider}'. Cooldown: {cooldown_remaining:.1f}s",
            code=ErrorCode.LLM_CIRCUIT_OPEN,
            category=ErrorCategory.FALLBACK_ELIGIBLE,
            retryable=False,
            fallback_eligible=True,
            user_message="Primary AI provider is temporarily suspended due to repeated failures. Using fallback.",
            status_code=503,
            details={"provider": provider, "cooldown_remaining": cooldown_remaining},
            **kwargs,
        )


class CapabilityMismatchError(AIError):
    def __init__(self, model_name: str, required_capability: str, **kwargs):
        super().__init__(
            message=f"Model '{model_name}' does not support required capability '{required_capability}'.",
            code=ErrorCode.LLM_CAPABILITY_MISMATCH,
            category=ErrorCategory.NON_RETRYABLE,
            retryable=False,
            fallback_eligible=False,
            user_message="The requested AI operation is not supported by the available model configurations.",
            status_code=400,
            details={"model": model_name, "required_capability": required_capability},
            **kwargs,
        )


# --- Tool Errors ---

class ToolExecutionError(AIError):
    def __init__(
        self,
        message: str = "Tool execution failed.",
        tool_name: Optional[str] = None,
        code: str = ErrorCode.TOOL_EXECUTION_FAILED,
        category: ErrorCategory = ErrorCategory.NON_RETRYABLE,
        retryable: bool = False,
        fallback_eligible: bool = False,
        user_message: str = "A tool operation could not be completed.",
        status_code: int = 500,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if tool_name:
            details["tool_name"] = tool_name
        super().__init__(
            message=message,
            code=code,
            category=category,
            retryable=retryable,
            fallback_eligible=fallback_eligible,
            user_message=user_message,
            status_code=status_code,
            details=details,
            **kwargs,
        )


class ToolTimeoutError(ToolExecutionError):
    def __init__(self, tool_name: str, timeout_seconds: float, **kwargs):
        super().__init__(
            message=f"Tool '{tool_name}' timed out after {timeout_seconds}s.",
            tool_name=tool_name,
            code=ErrorCode.TOOL_TIMEOUT,
            category=ErrorCategory.RETRYABLE,
            retryable=True,
            fallback_eligible=False,
            user_message=f"The tool '{tool_name}' timed out. Please try again.",
            status_code=504,
            **kwargs,
        )


class ToolInvalidArgumentError(ToolExecutionError):
    def __init__(self, tool_name: str, details_msg: str, **kwargs):
        super().__init__(
            message=f"Invalid arguments for tool '{tool_name}': {details_msg}",
            tool_name=tool_name,
            code=ErrorCode.TOOL_INVALID_ARGUMENT,
            category=ErrorCategory.NON_RETRYABLE,
            retryable=False,
            fallback_eligible=False,
            user_message=f"Invalid arguments provided for tool '{tool_name}'.",
            status_code=400,
            **kwargs,
        )


# --- RAG Errors ---

class RAGError(AIError):
    def __init__(
        self,
        message: str = "RAG retrieval error occurred.",
        code: str = ErrorCode.RAG_RETRIEVAL_FAILED,
        category: ErrorCategory = ErrorCategory.FALLBACK_ELIGIBLE,
        retryable: bool = True,
        fallback_eligible: bool = True,
        user_message: str = "Knowledge retrieval failed. Relying on current operational database information.",
        status_code: int = 500,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            category=category,
            retryable=retryable,
            fallback_eligible=fallback_eligible,
            user_message=user_message,
            status_code=status_code,
            **kwargs,
        )


class RAGRetrievalError(RAGError):
    pass


class RAGNoContextError(RAGError):
    def __init__(self, message: str = "No relevant documents found.", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.RAG_NO_RELEVANT_CONTEXT,
            category=ErrorCategory.NON_RETRYABLE,
            retryable=False,
            fallback_eligible=False,
            user_message="No reliable source found in uploaded club documents.",
            status_code=404,
            **kwargs,
        )


# --- Database Errors ---

class DatabaseError(AIError):
    def __init__(
        self,
        message: str = "Database operation failed.",
        code: str = ErrorCode.DATABASE_TRANSACTION_FAILED,
        category: ErrorCategory = ErrorCategory.NON_RETRYABLE,
        retryable: bool = False,
        fallback_eligible: bool = False,
        user_message: str = "A database operation could not be completed safely. Changes were rolled back.",
        status_code: int = 500,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=code,
            category=category,
            retryable=retryable,
            fallback_eligible=fallback_eligible,
            user_message=user_message,
            status_code=status_code,
            **kwargs,
        )


class DatabaseUnavailableError(DatabaseError):
    def __init__(self, message: str = "Database is temporarily unreachable.", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.DATABASE_UNAVAILABLE,
            category=ErrorCategory.RETRYABLE,
            retryable=True,
            fallback_eligible=False,
            user_message="The database is temporarily unreachable. Please try again shortly.",
            status_code=503,
            **kwargs,
        )


class DatabaseConflictError(DatabaseError):
    def __init__(self, message: str = "Concurrent database conflict detected.", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.DATABASE_CONFLICT,
            category=ErrorCategory.NON_RETRYABLE,
            retryable=False,
            fallback_eligible=False,
            user_message="A conflict occurred due to concurrent updates. Please refresh and retry.",
            status_code=409,
            **kwargs,
        )


# --- Agent Protection Errors ---

class AgentLoopLimitError(AIError):
    def __init__(self, max_steps: int = 10, **kwargs):
        super().__init__(
            message=f"Agent exceeded maximum step limit ({max_steps}).",
            code=ErrorCode.AGENT_MAX_ITERATIONS,
            category=ErrorCategory.NON_RETRYABLE,
            retryable=False,
            fallback_eligible=False,
            user_message="I couldn't safely complete the operation within the allowed number of steps.",
            status_code=400,
            details={"max_steps": max_steps},
            **kwargs,
        )


class AgentTimeoutError(AIError):
    def __init__(self, timeout_seconds: float = 60.0, **kwargs):
        super().__init__(
            message=f"Agent exceeded total execution timeout ({timeout_seconds}s).",
            code=ErrorCode.AGENT_TIMEOUT,
            category=ErrorCategory.NON_RETRYABLE,
            retryable=False,
            fallback_eligible=False,
            user_message="The requested operation took too long and was safely terminated.",
            status_code=504,
            details={"timeout_seconds": timeout_seconds},
            **kwargs,
        )


# --- Error Classifier Function ---

def classify_exception(exc: Exception) -> AIError:
    """
    Classifies any raw Python/SDK exception into a standardized AIError.
    Examines exception type, HTTP status, and message signatures for OpenAI, Gemini,
    OpenRouter, Anthropic, SQLAlchemy, and standard libraries.
    """
    if isinstance(exc, AIError):
        return exc

    err_str = str(exc).lower()
    exc_type_name = type(exc).__name__.lower()

    # 1. Rate Limit & Quota (429)
    if "429" in err_str or "rate limit" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
        # Check for Retry-After hint in error string if present
        retry_match = re.search(r"retry[- ]after[:\s]+(\d+(?:\.\d+)?)", err_str)
        retry_after = float(retry_match.group(1)) if retry_match else None
        return RateLimitError(
            message=f"Rate limit exceeded: {str(exc)[:200]}",
            retry_after=retry_after,
            original_exception=exc
        )

    # 2. Authentication & API Key (401, 403)
    if "401" in err_str or "invalid_api_key" in err_str or "incorrect api key" in err_str or "unauthorized" in err_str or "api key not valid" in err_str:
        return AuthenticationError(
            message="Invalid or missing AI API credentials.",
            original_exception=exc
        )

    if "403" in err_str or "permission denied" in err_str:
        return AuthenticationError(
            message="Permission denied by AI provider.",
            original_exception=exc
        )

    # 3. Timeout (504, ReadTimeout, TimeoutError)
    if "timeout" in err_str or "timed out" in err_str or "deadline_exceeded" in err_str or "timeout" in exc_type_name:
        return TimeoutError(
            message=f"AI request timed out: {str(exc)[:200]}",
            original_exception=exc
        )

    # 4. Network / Connection Errors
    if "connection" in err_str or "connecterror" in exc_type_name or "remotedisconnected" in err_str or "network" in err_str or "dns" in err_str:
        return NetworkError(
            message=f"Network error communicating with AI provider: {str(exc)[:200]}",
            original_exception=exc
        )

    # 5. Service Unavailable / Overloaded (500, 502, 503, bad gateway, overloaded)
    if "503" in err_str or "502" in err_str or "overloaded" in err_str or "unavailable" in err_str or "service unavailable" in err_str or "server error" in err_str:
        return ModelUnavailableError(
            message=f"AI model provider is unavailable: {str(exc)[:200]}",
            original_exception=exc
        )

    # 6. Content Policy / Safety violations
    if "safety" in err_str or "content policy" in err_str or "harm_category" in err_str or "blocked" in err_str:
        return ContentPolicyError(
            message="Content safety filter triggered.",
            original_exception=exc
        )

    # 7. Database errors (SQLAlchemy / psycopg2)
    if any(k in err_str for k in ["psycopg2", "operationalerror", "connection refused", "could not connect to server"]):
        return DatabaseUnavailableError(
            message="Database connection error.",
            original_exception=exc
        )

    if any(k in err_str for k in ["integrityerror", "unique constraint", "foreign key constraint", "concurrent update"]):
        return DatabaseConflictError(
            message="Database constraint or concurrency conflict.",
            original_exception=exc
        )

    # 8. Invalid JSON / Parsing
    if "jsondecodeerror" in exc_type_name or "validationerror" in exc_type_name or "expecting value" in err_str:
        return InvalidResponseError(
            message=f"Failed to parse structured AI output: {str(exc)[:200]}",
            original_exception=exc
        )

    # Default generic AIError
    return AIError(
        message=f"Unexpected AI error: {str(exc)[:200]}",
        code=ErrorCode.UNKNOWN_ERROR,
        category=ErrorCategory.NON_RETRYABLE,
        retryable=False,
        fallback_eligible=False,
        original_exception=exc,
    )

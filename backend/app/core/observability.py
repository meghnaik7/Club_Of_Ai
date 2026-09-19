import os
import logging
from typing import Optional, Any, Callable
from functools import wraps

from app.core.config import settings

logger = logging.getLogger("clubops.observability")

try:
    import langsmith
    from langsmith import Client as LangSmithClient
    from langsmith import traceable as ls_traceable
    HAS_LANGSMITH = True
except ImportError:
    HAS_LANGSMITH = False
    LangSmithClient = None
    ls_traceable = None

_client: Optional[Any] = None

def init_observability() -> bool:
    """
    Initializes LangSmith observability configuration and validates connectivity.
    Ensures environment variables are active for LangChain / LangGraph automated tracing.
    """
    global _client
    api_key = settings.LANGCHAIN_API_KEY or settings.LANGSMITH_API_KEY or os.getenv("LANGCHAIN_API_KEY")
    project = settings.LANGCHAIN_PROJECT or settings.LANGSMITH_PROJECT or "ClubOps-AI"
    endpoint = settings.LANGCHAIN_ENDPOINT or settings.LANGSMITH_ENDPOINT or "https://api.smith.langchain.com"

    if not api_key:
        logger.info("[Observability] LangSmith API key not configured. Tracing is disabled.")
        return False

    # Ensure system environment variables are set for automatic LangChain/LangGraph instrumentation
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGCHAIN_PROJECT"] = project
    os.environ["LANGCHAIN_ENDPOINT"] = endpoint
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = api_key
    os.environ["LANGSMITH_PROJECT"] = project
    os.environ["LANGSMITH_ENDPOINT"] = endpoint

    if HAS_LANGSMITH:
        try:
            _client = LangSmithClient(api_key=api_key, api_url=endpoint)
            logger.info(f"[Observability] LangSmith connected successfully. Tracing to project: '{project}'")
            return True
        except Exception as e:
            logger.warning(f"[Observability] LangSmith client initialization warning: {e}")
            return True
    else:
        logger.info(f"[Observability] LangSmith package not installed, but env variables set for project '{project}'.")
        return False

def get_langsmith_client():
    """Returns the active LangSmith Client instance if initialized, else None."""
    global _client
    if _client is None and HAS_LANGSMITH:
        init_observability()
    return _client

def is_observability_enabled() -> bool:
    """Checks whether LangSmith tracing is configured and active."""
    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY") or settings.LANGCHAIN_API_KEY
    return bool(api_key)

def traceable(name: Optional[str] = None, run_type: str = "chain", **trace_kwargs):
    """
    Robust traceable decorator.
    Uses LangSmith's @traceable if available and tracing is enabled,
    otherwise acts as a lightweight transparent wrapper.
    """
    if HAS_LANGSMITH and ls_traceable is not None and is_observability_enabled():
        return ls_traceable(name=name, run_type=run_type, **trace_kwargs)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator

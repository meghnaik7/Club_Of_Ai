"""
Observability helper for ClubOps AI modules (LangGraph agents, RAG pipelines, and tools).
"""
try:
    from app.core.observability import (
        init_observability,
        get_langsmith_client,
        is_observability_enabled,
        traceable
    )
except ImportError:
    try:
        from backend.app.core.observability import (
            init_observability,
            get_langsmith_client,
            is_observability_enabled,
            traceable
        )
    except ImportError:
        def init_observability(): return False
        def get_langsmith_client(): return None
        def is_observability_enabled(): return False
        def traceable(name=None, run_type="chain", **kwargs):
            def decorator(func): return func
            return decorator

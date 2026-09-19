"""Re-export of centralized LLM service from app.ai."""
try:
    from app.ai.llm_service import *
except ImportError:
    from backend.app.ai.llm_service import *

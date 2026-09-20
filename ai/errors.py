"""Re-export of error hierarchy from app.ai."""
try:
    from app.ai.errors import *
except ImportError:
    from backend.app.ai.errors import *

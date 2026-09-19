import os
import re
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)

# Fallback in-memory saver is always available
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver

# Optional imports for PostgreSQL checkpointer
try:
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg_pool import ConnectionPool
    HAS_POSTGRES_CHECKPOINTER = True
except ImportError as e:
    logger.warning(f"[Checkpointer] Postgres checkpointer dependencies unavailable: {e}")
    HAS_POSTGRES_CHECKPOINTER = False
    PostgresSaver = None
    ConnectionPool = None


def normalize_postgres_url(url: str) -> str:
    """
    Normalizes database URLs for PostgreSQL drivers.
    Converts legacy 'postgres://' schemes (common in Heroku/Render/AWS) to 'postgresql://'.
    """
    if not url:
        return url
    trimmed = url.strip()
    if trimmed.startswith("postgres://"):
        trimmed = "postgresql://" + trimmed[len("postgres://"):]
    return trimmed


def safe_sanitize_url(url: str) -> str:
    """
    Masks credentials in a database connection URL for safe logging and status reporting.
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
            sanitized = parsed._replace(netloc=netloc)
            return urlunparse(sanitized)
        return url
    except Exception:
        return re.sub(r":([^:@]+)@", r":***@", url)


class CheckpointerManager:
    """
    Production-grade Checkpointer Manager for LangGraph state persistence.
    Supports PostgreSQL (PostgresSaver) with connection pooling for cloud deployments,
    with automatic table creation (setup) and resilient fallback to in-memory checkpointer.
    """

    def __init__(self):
        self._pool: Optional[Any] = None
        self._checkpointer: Optional[BaseCheckpointSaver] = None
        self._checkpointer_type: str = "Uninitialized"
        self._is_cloud_persistent: bool = False
        self._is_connected: bool = False
        self._last_error: Optional[str] = None
        self._sanitized_url: str = ""
        self._db_host: str = ""
        self._db_name: str = ""

    def get_checkpointer(
        self,
        db_url: Optional[str] = None,
        force_memory: bool = False,
        min_size: int = 1,
        max_size: int = 20,
        timeout: float = 10.0
    ) -> BaseCheckpointSaver:
        """
        Retrieves or initializes the active LangGraph checkpointer.
        If a valid PostgreSQL connection string is provided, initializes PostgresSaver
        backed by a ConnectionPool and runs table migrations (.setup()).
        Falls back seamlessly to MemorySaver if PostgreSQL is unreachable or disabled.
        """
        if self._checkpointer is not None and not force_memory:
            return self._checkpointer

        if force_memory:
            logger.info("[Checkpointer] Explicit MemorySaver requested.")
            self._checkpointer = MemorySaver()
            self._checkpointer_type = "MemorySaver"
            self._is_cloud_persistent = False
            self._is_connected = True
            self._last_error = None
            return self._checkpointer

        # Determine target connection URL
        target_url = db_url
        if not target_url:
            try:
                from app.core.config import settings
                target_url = getattr(settings, "CHECKPOINTER_DATABASE_URL", None) or getattr(settings, "DATABASE_URL", None)
            except Exception:
                target_url = os.getenv("CHECKPOINTER_DATABASE_URL") or os.getenv("DATABASE_URL")

        # Check if URL represents PostgreSQL
        if not target_url or target_url.startswith("sqlite") or not HAS_POSTGRES_CHECKPOINTER:
            reason = "SQLite/local database detected" if (target_url and target_url.startswith("sqlite")) else (
                "Postgres checkpointer libraries not installed" if not HAS_POSTGRES_CHECKPOINTER else "No database URL configured"
            )
            logger.info(f"[Checkpointer] Using in-memory checkpointer ({reason}).")
            self._checkpointer = MemorySaver()
            self._checkpointer_type = "MemorySaver"
            self._is_cloud_persistent = False
            self._is_connected = True
            self._last_error = None
            return self._checkpointer

        # Attempt PostgreSQL connection
        normalized_url = normalize_postgres_url(target_url)
        self._sanitized_url = safe_sanitize_url(normalized_url)
        try:
            parsed = urlparse(normalized_url)
            self._db_host = parsed.hostname or "localhost"
            self._db_name = parsed.path.lstrip("/") or "default"
        except Exception:
            self._db_host = "remote"
            self._db_name = "default"

        try:
            logger.info(f"[Checkpointer] Connecting to PostgreSQL at {self._db_host}/{self._db_name} for permanent persistence...")
            # Close existing pool if any
            self.close_checkpointer_pool()

            # Initialize connection pool
            self._pool = ConnectionPool(
                conninfo=normalized_url,
                min_size=min_size,
                max_size=max_size,
                timeout=timeout,
                open=True,
                kwargs={"autocommit": True}
            )

            # Test pool connection
            with self._pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")

            # Initialize PostgresSaver and execute schema migrations
            saver = PostgresSaver(self._pool)
            saver.setup()

            self._checkpointer = saver
            self._checkpointer_type = "PostgresSaver"
            self._is_cloud_persistent = True
            self._is_connected = True
            self._last_error = None
            logger.info(f"[Checkpointer] Successfully initialized PostgresSaver on {self._db_host}/{self._db_name}. Checkpoint tables verified.")
            return self._checkpointer

        except Exception as e:
            self._last_error = str(e)
            logger.warning(
                f"[Checkpointer Warning] Could not connect to PostgreSQL checkpointer at {self._db_host} ({e}). "
                "Falling back to MemorySaver so AI operations remain available."
            )
            self.close_checkpointer_pool()
            self._checkpointer = MemorySaver()
            self._checkpointer_type = "MemorySaver"
            self._is_cloud_persistent = False
            self._is_connected = False
            return self._checkpointer

    def set_checkpointer(self, checkpointer: BaseCheckpointSaver, checkpointer_type: str = "Custom"):
        """Explicitly override the active checkpointer (primarily used in tests)."""
        self._checkpointer = checkpointer
        self._checkpointer_type = checkpointer_type
        self._is_cloud_persistent = isinstance(checkpointer, PostgresSaver) if PostgresSaver else False
        self._is_connected = True
        self._last_error = None

    def close_checkpointer_pool(self, timeout: float = 1.0):
        """Closes the active database connection pool during server shutdown."""
        if self._pool is not None:
            try:
                self._pool.close(timeout=timeout)
                logger.info("[Checkpointer] Connection pool closed successfully.")
            except Exception as e:
                logger.warning(f"[Checkpointer] Error closing connection pool: {e}")
            finally:
                self._pool = None

    def get_status(self) -> Dict[str, Any]:
        """Returns runtime diagnostics and status of the checkpointer system."""
        pool_stats = None
        if self._pool is not None:
            try:
                stats = self._pool.get_stats()
                pool_stats = {
                    "pool_min": stats.get("pool_min", 0),
                    "pool_max": stats.get("pool_max", 0),
                    "pool_size": stats.get("pool_size", 0),
                    "pool_available": stats.get("pool_available", 0),
                    "requests_waiting": stats.get("requests_waiting", 0)
                }
            except Exception:
                pool_stats = {"active": True}

        return {
            "checkpointer_type": self._checkpointer_type,
            "is_cloud_persistent": self._is_cloud_persistent,
            "is_connected": self._is_connected,
            "database_host": self._db_host if self._is_cloud_persistent else "in-memory",
            "database_name": self._db_name if self._is_cloud_persistent else "n/a",
            "sanitized_url": self._sanitized_url if self._is_cloud_persistent else "memory://",
            "has_pool": self._pool is not None,
            "pool_stats": pool_stats,
            "last_error": self._last_error
        }


# Singleton manager instance
checkpointer_manager = CheckpointerManager()

def get_checkpointer(
    db_url: Optional[str] = None,
    force_memory: bool = False
) -> BaseCheckpointSaver:
    """Convenience helper to obtain the global checkpointer."""
    return checkpointer_manager.get_checkpointer(db_url=db_url, force_memory=force_memory)

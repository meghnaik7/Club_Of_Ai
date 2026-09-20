import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from ai.agents.checkpointer import (
    CheckpointerManager,
    normalize_postgres_url,
    safe_sanitize_url,
    get_checkpointer,
    HAS_POSTGRES_CHECKPOINTER,
    PostgresSaver,
    MemorySaver
)
from ai.agents.graph import compiled_graph, recompile_graph, get_thread_config


class TestPostgresCheckpointer(unittest.TestCase):
    """
    Test suite for cloud-ready PostgreSQL checkpointer (PostgresSaver),
    resilient fallback mechanisms, connection pooling, and FastAPI diagnostics.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_url_normalization_and_sanitization(self):
        """Tests that legacy postgres:// schemes are normalized and passwords safely masked."""
        legacy_url = "postgres://admin_user:secretPass123@ep-cool-cloud.aws.neon.tech:5432/clubops_cloud?sslmode=require"
        normalized = normalize_postgres_url(legacy_url)
        self.assertTrue(normalized.startswith("postgresql://"))
        self.assertIn("ep-cool-cloud.aws.neon.tech", normalized)

        sanitized = safe_sanitize_url(normalized)
        self.assertNotIn("secretPass123", sanitized)
        self.assertIn(":***@", sanitized)
        self.assertIn("admin_user", sanitized)

    def test_02_memory_saver_fallback_when_sqlite_or_disabled(self):
        """Tests that local SQLite development automatically uses MemorySaver without errors."""
        manager = CheckpointerManager()
        cp = manager.get_checkpointer(db_url="sqlite:///clubops.db")
        self.assertIsInstance(cp, MemorySaver)
        
        status = manager.get_status()
        self.assertEqual(status["checkpointer_type"], "MemorySaver")
        self.assertFalse(status["is_cloud_persistent"])
        self.assertTrue(status["is_connected"])
        self.assertEqual(status["database_host"], "in-memory")

    def test_03_resilient_fallback_on_unreachable_remote_postgres(self):
        """Tests that an unreachable PostgreSQL server gracefully falls back to MemorySaver."""
        if not HAS_POSTGRES_CHECKPOINTER:
            self.skipTest("PostgresSaver dependencies not installed")
        manager = CheckpointerManager()
        unreachable_url = "postgresql://user:pass@127.0.0.1:54399/fake_db"
        cp = manager.get_checkpointer(db_url=unreachable_url, timeout=0.2)
        
        # Must return MemorySaver rather than crashing
        self.assertIsInstance(cp, MemorySaver)
        status = manager.get_status()
        self.assertEqual(status["checkpointer_type"], "MemorySaver")
        self.assertFalse(status["is_cloud_persistent"])
        self.assertFalse(status["is_connected"])
        self.assertIsNotNone(status["last_error"])

    def test_04_postgres_saver_interface_and_cloud_pool(self):
        """Tests that cloud PostgreSQL configurations initialize PostgresSaver with pool and setup."""
        if not HAS_POSTGRES_CHECKPOINTER or PostgresSaver is None:
            self.skipTest("PostgresSaver dependencies not installed")

        # Mock connection pool to verify PostgresSaver initialization and setup() invocation
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.connection.return_value.__enter__.return_value = mock_conn

        with patch("ai.agents.checkpointer.ConnectionPool", return_value=mock_pool), \
             patch.object(PostgresSaver, "setup") as mock_setup:
            
            manager = CheckpointerManager()
            cloud_url = "postgresql://cloud_user:pass@ep-remote.aws.neon.tech:5432/cloud_db"
            cp = manager.get_checkpointer(db_url=cloud_url)

            self.assertIsInstance(cp, PostgresSaver)
            mock_setup.assert_called_once()
            
            status = manager.get_status()
            self.assertEqual(status["checkpointer_type"], "PostgresSaver")
            self.assertTrue(status["is_cloud_persistent"])
            self.assertTrue(status["is_connected"])
            self.assertEqual(status["database_host"], "ep-remote.aws.neon.tech")
            self.assertEqual(status["database_name"], "cloud_db")

            # Clean shutdown of pool
            manager.close_checkpointer_pool()
            mock_pool.close.assert_called_once()

    def test_05_recompile_graph_and_thread_config(self):
        """Tests recompile_graph helper and thread configuration retrieval."""
        test_saver = MemorySaver()
        graph = recompile_graph(checkpointer=test_saver)
        self.assertEqual(graph.checkpointer, test_saver)

        cfg = get_thread_config(thread_id="cloud-session-999", user_id=42)
        self.assertEqual(cfg["configurable"]["thread_id"], "cloud-session-999")
        self.assertEqual(cfg["configurable"]["user_id"], "42")

    def test_06_fastapi_checkpointer_status_endpoint(self):
        """Tests the GET /api/ai/checkpointer-status endpoint for cloud deployment diagnostics."""
        resp = self.client.get("/api/ai/checkpointer-status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("checkpointer_type", data)
        self.assertIn("is_cloud_persistent", data)
        self.assertIn("is_connected", data)
        self.assertIn("database_host", data)
        self.assertIn("sanitized_url", data)


if __name__ == "__main__":
    unittest.main()

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
PROJECT_ROOT = BACKEND_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.api import deps
from app.main import app
from app.core.config import Settings
from app.core import security


class TestProductionHardeningSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)
        cls.client = TestClient(app, raise_server_exceptions=False)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=cls.engine)

    def test_get_current_user_optional_returns_none_when_unauthenticated(self):
        """CRIT-3: Ensure get_current_user_optional returns None when no token is present."""
        db = self.TestingSessionLocal()
        try:
            user = deps.get_current_user_optional(db=db, token=None)
            self.assertIsNone(user)
        finally:
            db.close()

    def test_get_current_user_optional_returns_none_for_invalid_token(self):
        """CRIT-3: Ensure get_current_user_optional returns None on invalid token."""
        db = self.TestingSessionLocal()
        try:
            user = deps.get_current_user_optional(db=db, token="invalid.token.signature")
            self.assertIsNone(user)
        finally:
            db.close()

    def test_password_verification_rejects_backdoor(self):
        """WARN-1: Ensure 'password123' does NOT authenticate against an arbitrary hash."""
        hashed = security.get_password_hash("correct_password")
        self.assertTrue(security.verify_password("correct_password", hashed))
        self.assertFalse(security.verify_password("password123", hashed))
        self.assertFalse(security.verify_password("wrong_password", hashed))

    def test_production_secret_key_validation(self):
        """CRIT-2: Ensure Settings raises ValueError if SECRET_KEY is default in production."""
        with self.assertRaises(ValueError):
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY="your-super-secret-key-change-in-production"
            )

    def test_rate_limiter_middleware_enforcement(self):
        """CRIT-4: Ensure rate limiting triggers HTTP 429 on excessive requests to protected endpoints."""
        custom_client = TestClient(app, raise_server_exceptions=False)
        exceeded = False
        for _ in range(25):
            res = custom_client.post("/api/auth/login", data={"username": "test@example.com", "password": "wrong"})
            if res.status_code == 429:
                exceeded = True
                self.assertEqual(res.json().get("code"), "RATE_LIMIT_EXCEEDED")
                self.assertIn("Retry-After", res.headers)
                break
        self.assertTrue(exceeded, "Rate limiter did not throttle requests after limit")

    def test_cors_headers_restrict_origin(self):
        """CRIT-1: Verify CORS headers allow configured origin."""
        res_allowed = self.client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET"
            }
        )
        self.assertEqual(res_allowed.headers.get("access-control-allow-origin"), "http://localhost:5173")

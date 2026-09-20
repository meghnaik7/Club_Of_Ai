import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
PROJECT_ROOT = BACKEND_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.api import deps
from app.core.database import get_db
from app.core.security import get_password_hash, create_access_token
from app.core.permissions import seed_permissions
from app.main import app
from app.models.user import User, UserRole
from app.models.team import Club, Team, TeamMembership, ClubMembership, TeamRole, ClubRole
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.event import Event, EventStatus
from app.models.task import Task, TaskStatus, TaskPriority, TaskAssignment
from app.db.seed_teams_and_roles import seed_demo_accounts_and_org


class TestUserProfileAndDemoLogin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

        def override_get_db():
            db = cls.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[deps.get_db] = override_get_db
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=cls.engine)
        app.dependency_overrides.clear()

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.TestingSessionLocal()
        seed_permissions(self.db)
        # Seed realistic demo data
        self.demo_data = seed_demo_accounts_and_org(self.db)

    def tearDown(self):
        self.db.close()

    def _get_token_for_user(self, user: User) -> str:
        return create_access_token(user.id)

    # ─────────────────────────────────────────────────────────────
    # FEATURE 2: DEMO LOGIN TESTS
    # ─────────────────────────────────────────────────────────────

    def test_demo_login_admin(self):
        """Verify Admin demo login returns token, ADMIN role, and /admin/organization redirect."""
        res = self.client.post("/api/v1/auth/demo-login", json={"demo_account": "admin"})
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["role"], "ADMIN")
        self.assertEqual(data["redirect_url"], "/admin/organization")
        self.assertEqual(data["user"]["email"], "admin@demo.local")

    def test_demo_login_club_head(self):
        """Verify Club Head demo login returns token, CLUB_HEAD role, and /dashboard redirect."""
        res = self.client.post("/api/v1/auth/demo-login", json={"demo_account": "club_head"})
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["role"], "CLUB_HEAD")
        self.assertEqual(data["redirect_url"], "/dashboard")
        self.assertEqual(data["user"]["email"], "clubhead@demo.local")

    def test_demo_login_subteam_lead(self):
        """Verify SubTeam Lead demo login returns token, SUBTEAM_LEAD role, and /teams redirect."""
        res = self.client.post("/api/v1/auth/demo-login", json={"demo_account": "subteam_lead"})
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["role"], "SUBTEAM_LEAD")
        self.assertEqual(data["redirect_url"], "/teams")
        self.assertEqual(data["user"]["email"], "teamlead@demo.local")

    def test_demo_login_volunteer(self):
        """Verify Volunteer demo login returns token, VOLUNTEER role, and /dashboard redirect."""
        res = self.client.post("/api/v1/auth/demo-login", json={"demo_account": "volunteer"})
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["role"], "VOLUNTEER")
        self.assertEqual(data["redirect_url"], "/dashboard")
        self.assertEqual(data["user"]["email"], "volunteer@demo.local")

    def test_demo_login_invalid_account(self):
        """Verify invalid demo account rejected with 400 Bad Request."""
        res = self.client.post("/api/v1/auth/demo-login", json={"demo_account": "super_hacker"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid demo account", res.json()["detail"])

    def test_demo_login_cannot_choose_arbitrary_role(self):
        """Verify frontend cannot pass an arbitrary role to elevate privileges."""
        res = self.client.post("/api/v1/auth/demo-login", json={"demo_account": "volunteer", "role": "ADMIN"})
        self.assertEqual(res.status_code, 200)
        # Even if payload has "role": "ADMIN", backend determines real role from volunteer DB account
        data = res.json()
        self.assertEqual(data["role"], "VOLUNTEER")
        self.assertEqual(data["redirect_url"], "/dashboard")

    # ─────────────────────────────────────────────────────────────
    # FEATURE 1: USER PROFILE GET TESTS
    # ─────────────────────────────────────────────────────────────

    def test_get_volunteer_profile(self):
        """Verify Volunteer gets complete profile with basic info, organization, workload, authorized tasks, events, and permissions."""
        vol_user = self.demo_data["volunteer"]
        token = self._get_token_for_user(vol_user)
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.get("/api/v1/users/me/profile", headers=headers)
        self.assertEqual(res.status_code, 200, res.text)
        profile = res.json()

        # Basic Info
        basic = profile["basic_info"]
        self.assertEqual(basic["email"], vol_user.email)
        self.assertEqual(basic["full_name"], "Demo Volunteer 1")
        self.assertEqual(basic["account_status"], "ACTIVE")

        # Organization
        org = profile["organization"]
        self.assertEqual(org["role"], "VOLUNTEER")
        self.assertEqual(org["club_name"], "GDG Demo Club")
        self.assertEqual(org["subteam_name"], "AI/ML Team")
        self.assertIsNotNone(org["club_head_info"])
        self.assertIsNotNone(org["subteam_lead_info"])

        # Skills & Availability
        self.assertTrue(len(profile["skills"]) > 0)
        self.assertIn("Python", profile["skills"])
        self.assertIn("WEEKDAYS", profile["availability"])

        # Workload
        wl = profile["workload"]
        self.assertIn("active_tasks", wl)
        self.assertIn("completed_tasks", wl)
        self.assertIn("overdue_tasks", wl)
        self.assertIn("load_status", wl)
        self.assertIn(wl["load_status"], ["LOW", "MEDIUM", "OVERLOADED"])

        # Tasks scoping: volunteer only sees assigned tasks (not unassigned web team tasks)
        task_titles = [t["title"] for t in profile["tasks"]]
        self.assertIn("Prepare AI Workshop Colab Notebooks", task_titles)
        self.assertNotIn("Deploy Registration & RSVP Portal", task_titles)

        # Permissions: human readable
        perms = profile["permissions"]
        self.assertTrue(len(perms["human_readable"]) > 0)
        self.assertTrue(any("View assigned tasks" in p for p in perms["human_readable"]))

    def test_get_club_head_profile(self):
        """Verify Club Head gets profile showing club level info, subteam=None, and club tasks."""
        head_user = self.demo_data["club_head"]
        token = self._get_token_for_user(head_user)
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.get("/api/v1/users/me/profile", headers=headers)
        self.assertEqual(res.status_code, 200, res.text)
        profile = res.json()

        self.assertEqual(profile["organization"]["role"], "CLUB_HEAD")
        self.assertEqual(profile["organization"]["club_name"], "GDG Demo Club")
        self.assertIsNone(profile["organization"]["subteam_name"])
        self.assertTrue(any("Manage club members" in p for p in profile["permissions"]["human_readable"]))

    def test_get_subteam_lead_profile(self):
        """Verify SubTeam Lead gets profile with their team and team tasks."""
        lead_user = self.demo_data["subteam_lead"]
        token = self._get_token_for_user(lead_user)
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.get("/api/v1/users/me/profile", headers=headers)
        self.assertEqual(res.status_code, 200, res.text)
        profile = res.json()

        self.assertEqual(profile["organization"]["role"], "SUBTEAM_LEAD")
        self.assertEqual(profile["organization"]["subteam_name"], "AI/ML Team")
        self.assertTrue(any("Manage own subteam" in p for p in profile["permissions"]["human_readable"]))

    def test_get_admin_profile(self):
        """Verify Admin profile shows full system permissions."""
        admin_user = self.demo_data["admin"]
        token = self._get_token_for_user(admin_user)
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.get("/api/v1/users/me/profile", headers=headers)
        self.assertEqual(res.status_code, 200, res.text)
        profile = res.json()

        self.assertEqual(profile["organization"]["role"], "ADMIN")
        self.assertTrue(any("Full system administration" in p for p in profile["permissions"]["human_readable"]))

    # ─────────────────────────────────────────────────────────────
    # FEATURE 1: USER PROFILE PATCH / EDITING TESTS
    # ─────────────────────────────────────────────────────────────

    def test_update_allowed_personal_fields(self):
        """Verify user can update allowed fields: full_name, phone, bio, avatar_url, skills, availability."""
        vol_user = self.demo_data["volunteer"]
        token = self._get_token_for_user(vol_user)
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "full_name": "Updated Volunteer Name",
            "phone": "+1-555-9999",
            "bio": "New bio for testing.",
            "avatar_url": "https://example.com/photo.jpg",
            "skills": ["Rust", "PyTorch", "Kubernetes"],
            "availability": "WEEKDAYS"
        }

        res = self.client.patch("/api/v1/users/me/profile", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200, res.text)
        updated = res.json()

        self.assertEqual(updated["basic_info"]["full_name"], "Updated Volunteer Name")
        self.assertEqual(updated["basic_info"]["phone"], "+1-555-9999")
        self.assertEqual(updated["basic_info"]["bio"], "New bio for testing.")
        self.assertEqual(updated["basic_info"]["avatar_url"], "https://example.com/photo.jpg")
        self.assertIn("Rust", updated["skills"])
        self.assertEqual(updated["availability"], "WEEKDAYS")

    def test_reject_unauthorized_role_change(self):
        """Verify attempts to modify role via profile PATCH are rejected with 403 Forbidden."""
        vol_user = self.demo_data["volunteer"]
        token = self._get_token_for_user(vol_user)
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.patch("/api/v1/users/me/profile", json={"role": "ADMIN"}, headers=headers)
        self.assertEqual(res.status_code, 403)
        self.assertIn("Unauthorized field modification", res.json()["detail"])

    def test_reject_unauthorized_club_change(self):
        """Verify attempts to modify club_id via profile PATCH are rejected with 403 Forbidden."""
        vol_user = self.demo_data["volunteer"]
        token = self._get_token_for_user(vol_user)
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.patch("/api/v1/users/me/profile", json={"club_id": 999}, headers=headers)
        self.assertEqual(res.status_code, 403)
        self.assertIn("Unauthorized field modification", res.json()["detail"])

    def test_reject_unauthorized_subteam_change(self):
        """Verify attempts to modify subteam_id via profile PATCH are rejected with 403 Forbidden."""
        vol_user = self.demo_data["volunteer"]
        token = self._get_token_for_user(vol_user)
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.patch("/api/v1/users/me/profile", json={"subteam_id": 999}, headers=headers)
        self.assertEqual(res.status_code, 403)
        self.assertIn("Unauthorized field modification", res.json()["detail"])

    # ─────────────────────────────────────────────────────────────
    # RBAC & DATA ISOLATION VERIFICATION
    # ─────────────────────────────────────────────────────────────

    def test_volunteer_cannot_access_admin_organization(self):
        """Verify volunteer receives 403 when trying to access admin organization endpoints."""
        vol_user = self.demo_data["volunteer"]
        token = self._get_token_for_user(vol_user)
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.get("/api/v1/admin/users", headers=headers)
        self.assertEqual(res.status_code, 403)

    def test_admin_can_access_admin_organization(self):
        """Verify Admin can access admin organization endpoints."""
        admin_user = self.demo_data["admin"]
        token = self._get_token_for_user(admin_user)
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.get("/api/v1/admin/users", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(res.json()) > 0)

    def test_jwt_authenticates_regular_endpoints(self):
        """Verify token from demo login successfully authenticates standard protected endpoints."""
        res_login = self.client.post("/api/v1/auth/demo-login", json={"demo_account": "volunteer"})
        self.assertEqual(res_login.status_code, 200)
        token = res_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Call /api/v1/auth/me
        res_me = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(res_me.status_code, 200)
        self.assertEqual(res_me.json()["email"], "volunteer@demo.local")

        # Call /api/v1/tasks
        res_tasks = self.client.get("/api/v1/tasks/", headers=headers)
        self.assertEqual(res_tasks.status_code, 200)


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

import app.db.base
from app.db.base_class import Base
from app.core.permissions import seed_permissions
from app.core.security import get_password_hash, create_access_token
from app.models.user import User, UserRole
from app.models.team import Club, Team, TeamMembership, ClubMembership, TeamRole, ClubRole
from app.models.permission import Permission, UserPermission, ScopeType, PermissionEffect
from app.models.event import Event
from app.models.task import Task, TaskStatus, TaskPriority, TaskAssignment
from app.models.volunteer import Volunteer, VolunteerStatus
from app.services.authz import AuthorizationService
from app.main import app
from app.api import deps


from sqlalchemy.pool import StaticPool


class TestAuthorizationPermissionsComprehensive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=cls.engine)

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.TestingSessionLocal()
        seed_permissions(self.db)

        pwd = get_password_hash("password123")

        # 1. Setup Clubs
        self.club1 = Club(name="AI Club", description="Premier AI Club")
        self.club2 = Club(name="Robotics Club", description="Robotics Club")
        self.db.add_all([self.club1, self.club2])
        self.db.flush()

        # 2. Setup SubTeams
        self.subteam1 = Team(name="ML Team", club_id=self.club1.id)
        self.subteam2 = Team(name="Web Team", club_id=self.club1.id)
        self.subteam_b = Team(name="Hardware Team", club_id=self.club2.id)
        self.db.add_all([self.subteam1, self.subteam2, self.subteam_b])
        self.db.flush()

        # 3. Setup Users across the hierarchy
        self.admin = User(email="admin@test.org", hashed_password=pwd, full_name="Global Admin", role=UserRole.ADMIN, is_active=True)
        self.head1 = User(email="head1@test.org", hashed_password=pwd, full_name="Head Club 1", role=UserRole.CLUB_HEAD, club_id=self.club1.id, is_active=True)
        self.head2 = User(email="head2@test.org", hashed_password=pwd, full_name="Head Club 2", role=UserRole.CLUB_HEAD, club_id=self.club2.id, is_active=True)
        self.lead1 = User(email="lead1@test.org", hashed_password=pwd, full_name="Lead Subteam 1", role=UserRole.SUBTEAM_LEAD, club_id=self.club1.id, subteam_id=self.subteam1.id, is_active=True)
        self.lead2 = User(email="lead2@test.org", hashed_password=pwd, full_name="Lead Subteam 2", role=UserRole.SUBTEAM_LEAD, club_id=self.club1.id, subteam_id=self.subteam2.id, is_active=True)
        self.vol1 = User(email="vol1@test.org", hashed_password=pwd, full_name="Volunteer Subteam 1", role=UserRole.VOLUNTEER, club_id=self.club1.id, subteam_id=self.subteam1.id, is_active=True)
        self.vol2 = User(email="vol2@test.org", hashed_password=pwd, full_name="Volunteer Subteam 2", role=UserRole.VOLUNTEER, club_id=self.club1.id, subteam_id=self.subteam2.id, is_active=True)
        self.vol_b = User(email="volb@test.org", hashed_password=pwd, full_name="Volunteer Club 2", role=UserRole.VOLUNTEER, club_id=self.club2.id, subteam_id=self.subteam_b.id, is_active=True)

        self.db.add_all([self.admin, self.head1, self.head2, self.lead1, self.lead2, self.vol1, self.vol2, self.vol_b])
        self.db.flush()

        # Link team lead_id
        self.subteam1.lead_id = self.lead1.id
        self.subteam2.lead_id = self.lead2.id

        # Memberships
        self.db.add_all([
            ClubMembership(club_id=self.club1.id, user_id=self.head1.id, role=ClubRole.CLUB_HEAD, is_active=True),
            ClubMembership(club_id=self.club2.id, user_id=self.head2.id, role=ClubRole.CLUB_HEAD, is_active=True),
            TeamMembership(team_id=self.subteam1.id, user_id=self.lead1.id, role=TeamRole.SUBTEAM_LEAD, is_active=True),
            TeamMembership(team_id=self.subteam2.id, user_id=self.lead2.id, role=TeamRole.SUBTEAM_LEAD, is_active=True),
            TeamMembership(team_id=self.subteam1.id, user_id=self.vol1.id, role=TeamRole.VOLUNTEER, is_active=True),
            TeamMembership(team_id=self.subteam2.id, user_id=self.vol2.id, role=TeamRole.VOLUNTEER, is_active=True),
            TeamMembership(team_id=self.subteam_b.id, user_id=self.vol_b.id, role=TeamRole.VOLUNTEER, is_active=True),
        ])

        # Volunteer profiles
        self.vp1 = Volunteer(user_id=self.vol1.id, club_id=self.club1.id, subteam_id=self.subteam1.id, status=VolunteerStatus.ACTIVE)
        self.vp2 = Volunteer(user_id=self.vol2.id, club_id=self.club1.id, subteam_id=self.subteam2.id, status=VolunteerStatus.ACTIVE)
        self.vpb = Volunteer(user_id=self.vol_b.id, club_id=self.club2.id, subteam_id=self.subteam_b.id, status=VolunteerStatus.ACTIVE)
        self.db.add_all([self.vp1, self.vp2, self.vpb])
        self.db.flush()

        # Events
        future = datetime.now(timezone.utc) + timedelta(days=10)
        self.ev1 = Event(title="AI Summit", club_id=self.club1.id, created_by=self.head1.id, date=future)
        self.ev2 = Event(title="RoboExpo", club_id=self.club2.id, created_by=self.head2.id, date=future)
        self.db.add_all([self.ev1, self.ev2])
        self.db.flush()

        # Tasks
        self.task_s1 = Task(title="Train ML Model", event_id=self.ev1.id, team_id=self.subteam1.id, created_by=self.lead1.id)
        self.task_s2 = Task(title="Build Dashboard", event_id=self.ev1.id, team_id=self.subteam2.id, created_by=self.lead2.id)
        self.task_b = Task(title="Solder Motors", event_id=self.ev2.id, team_id=self.subteam_b.id, created_by=self.head2.id)
        self.db.add_all([self.task_s1, self.task_s2, self.task_b])
        self.db.flush()

        # Assign vol1 to task_s1
        self.asgn1 = TaskAssignment(task_id=self.task_s1.id, volunteer_id=self.vp1.id)
        self.db.add(self.asgn1)
        self.db.commit()

        # Setup test client with overridden dependency
        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[deps.get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def _auth_headers(self, user: User):
        token = create_access_token(subject=str(user.id))
        return {"Authorization": f"Bearer {token}"}

    # ─────────────────────────────────────────────────────────────
    # Unit Authorization Tests
    # ─────────────────────────────────────────────────────────────

    def test_admin_systemwide_authority(self):
        """Admin has unrestricted access across all clubs, teams, tasks, and system operations."""
        self.assertTrue(AuthorizationService.is_admin(self.admin))
        self.assertTrue(AuthorizationService.can(self.db, self.admin, "club.manage"))
        self.assertTrue(AuthorizationService.can(self.db, self.admin, "team.create"))
        self.assertTrue(AuthorizationService.can(self.db, self.admin, "team.delete"))
        self.assertTrue(AuthorizationService.can(self.db, self.admin, "task.delete", resource=self.task_s1))
        self.assertTrue(AuthorizationService.can(self.db, self.admin, "task.delete", resource=self.task_b))
        self.assertTrue(AuthorizationService.can_access_club(self.db, self.admin, self.club1.id))
        self.assertTrue(AuthorizationService.can_access_club(self.db, self.admin, self.club2.id))
        self.assertTrue(AuthorizationService.can_manage_task(self.db, self.admin, self.task_s1.id))
        self.assertTrue(AuthorizationService.can_manage_task(self.db, self.admin, self.task_b.id))

    def test_club_head_scoped_within_club(self):
        """Club Head has full authority in their club, but zero access to other clubs."""
        self.assertTrue(AuthorizationService.is_club_head(self.db, self.head1, club_id=self.club1.id))
        self.assertTrue(AuthorizationService.can_access_club(self.db, self.head1, self.club1.id))
        self.assertTrue(AuthorizationService.can_manage_task(self.db, self.head1, self.task_s1.id))
        self.assertTrue(AuthorizationService.can_access_subteam(self.db, self.head1, self.subteam1.id))
        self.assertTrue(AuthorizationService.can(self.db, self.head1, "task.delete", resource=self.task_s1))

        # Denied from Club 2
        self.assertFalse(AuthorizationService.can_access_club(self.db, self.head1, self.club2.id))
        self.assertFalse(AuthorizationService.can_manage_task(self.db, self.head1, self.task_b.id))
        self.assertFalse(AuthorizationService.can_access_subteam(self.db, self.head1, self.subteam_b.id))
        self.assertFalse(AuthorizationService.can(self.db, self.head1, "task.delete", resource=self.task_b))
        self.assertFalse(AuthorizationService.can(self.db, self.head1, "team.update", resource=self.subteam_b, scope_type="TEAM", scope_id=self.subteam_b.id))

    def test_subteam_lead_boundaries(self):
        """SubTeam Lead can manage only their own subteam and cannot delete tasks or teams."""
        self.assertTrue(AuthorizationService.is_subteam_lead(self.db, self.lead1, subteam_id=self.subteam1.id))
        self.assertTrue(AuthorizationService.can_access_subteam(self.db, self.lead1, self.subteam1.id))
        self.assertTrue(AuthorizationService.can_manage_task(self.db, self.lead1, self.task_s1.id))
        self.assertTrue(AuthorizationService.can(self.db, self.lead1, "task.create", scope_type="TEAM", scope_id=self.subteam1.id))
        self.assertTrue(AuthorizationService.can(self.db, self.lead1, "task.update", resource=self.task_s1))

        # Denied from Subteam 2
        self.assertFalse(AuthorizationService.can_manage_task(self.db, self.lead1, self.task_s2.id))
        self.assertFalse(AuthorizationService.can(self.db, self.lead1, "task.create", scope_type="TEAM", scope_id=self.subteam2.id))
        self.assertFalse(AuthorizationService.can(self.db, self.lead1, "task.update", resource=self.task_s2))

        # SubTeam Lead cannot delete tasks or teams
        self.assertFalse(AuthorizationService.can(self.db, self.lead1, "task.delete", resource=self.task_s1))
        self.assertFalse(AuthorizationService.can(self.db, self.lead1, "team.delete", resource=self.subteam1, scope_type="TEAM", scope_id=self.subteam1.id))
        self.assertFalse(AuthorizationService.can(self.db, self.lead1, "team.create", scope_type="CLUB"))

    def test_volunteer_permissions_and_restrictions(self):
        """Volunteers can view assigned tasks and change status, but cannot create/manage tasks or org entities."""
        self.assertTrue(AuthorizationService.can_access_task(self.db, self.vol1, self.task_s1.id))
        self.assertTrue(AuthorizationService.can(self.db, self.vol1, "task.view", resource=self.task_s1))
        self.assertTrue(AuthorizationService.can(self.db, self.vol1, "task.status.update", resource=self.task_s1))
        self.assertTrue(AuthorizationService.can(self.db, self.vol1, "task.comment", resource=self.task_s1))

        # Prohibitions
        self.assertFalse(AuthorizationService.can(self.db, self.vol1, "task.update", resource=self.task_s1))
        self.assertFalse(AuthorizationService.can(self.db, self.vol1, "task.assign", resource=self.task_s1))
        self.assertFalse(AuthorizationService.can(self.db, self.vol1, "task.delete", resource=self.task_s1))
        self.assertFalse(AuthorizationService.can(self.db, self.vol1, "task.create", scope_type="TEAM", scope_id=self.subteam1.id))
        self.assertFalse(AuthorizationService.can(self.db, self.vol1, "team.create", scope_type="CLUB"))
        self.assertFalse(AuthorizationService.can(self.db, self.vol1, "event.create"))
        self.assertFalse(AuthorizationService.can(self.db, self.vol1, "announcement.create"))

    def test_cross_subteam_volunteer_assignment_guards(self):
        """Lead cannot assign volunteers from another subteam or club; Club Head can assign within club."""
        # SubTeam Lead 1 can assign Volunteer 1 (same subteam)
        self.assertTrue(AuthorizationService.can_assign_task(self.db, self.lead1, self.task_s1.id, self.vp1.id))
        # SubTeam Lead 1 CANNOT assign Volunteer 2 (different subteam)
        self.assertFalse(AuthorizationService.can_assign_task(self.db, self.lead1, self.task_s1.id, self.vp2.id))
        # SubTeam Lead 1 CANNOT assign Volunteer B (different club)
        self.assertFalse(AuthorizationService.can_assign_task(self.db, self.lead1, self.task_s1.id, self.vpb.id))

        # Club Head 1 CAN assign Volunteer 2 to task_s1 (within same club)
        self.assertTrue(AuthorizationService.can_assign_task(self.db, self.head1, self.task_s1.id, self.vp2.id))
        # Club Head 1 CANNOT assign Volunteer B to task_s1 (different club)
        self.assertFalse(AuthorizationService.can_assign_task(self.db, self.head1, self.task_s1.id, self.vpb.id))

    def test_permission_overrides_resolution(self):
        """ALLOW grant gives permission; DENY always takes precedence."""
        perm_create = self.db.query(Permission).filter(Permission.key == "task.create").first()

        # Vol1 initially cannot create task
        self.assertFalse(AuthorizationService.can(self.db, self.vol1, "task.create", scope_type="TEAM", scope_id=self.subteam1.id))

        # Explicit ALLOW
        ov_allow = UserPermission(
            user_id=self.vol1.id,
            permission_id=perm_create.id,
            scope_type=ScopeType.TEAM,
            scope_id=self.subteam1.id,
            effect=PermissionEffect.ALLOW
        )
        self.db.add(ov_allow)
        self.db.commit()

        self.assertTrue(AuthorizationService.can(self.db, self.vol1, "task.create", scope_type="TEAM", scope_id=self.subteam1.id))
        self.assertFalse(AuthorizationService.can(self.db, self.vol1, "task.create", scope_type="TEAM", scope_id=self.subteam2.id))

        # Explicit DENY on Lead1
        self.assertTrue(AuthorizationService.can(self.db, self.lead1, "task.create", scope_type="TEAM", scope_id=self.subteam1.id))

        ov_deny = UserPermission(
            user_id=self.lead1.id,
            permission_id=perm_create.id,
            scope_type=ScopeType.GLOBAL,
            scope_id=None,
            effect=PermissionEffect.DENY
        )
        self.db.add(ov_deny)
        self.db.commit()

        self.assertFalse(AuthorizationService.can(self.db, self.lead1, "task.create", scope_type="TEAM", scope_id=self.subteam1.id))

    # ─────────────────────────────────────────────────────────────
    # API HTTP Endpoint Authorization Tests
    # ─────────────────────────────────────────────────────────────

    def test_api_admin_org_tree_access(self):
        """Admin can access organization tree; Volunteer is denied with 403."""
        r_admin = self.client.get("/api/v1/admin/organization/tree", headers=self._auth_headers(self.admin))
        self.assertEqual(r_admin.status_code, 200)

        r_vol = self.client.get("/api/v1/admin/organization/tree", headers=self._auth_headers(self.vol1))
        self.assertEqual(r_vol.status_code, 403)

    def test_api_team_creation_permissions(self):
        """Club Head can create a team in their club; Volunteer is denied 403."""
        # Volunteer denied
        r_vol = self.client.post("/api/v1/teams/", json={"name": "New Team", "description": "Desc", "club_id": self.club1.id}, headers=self._auth_headers(self.vol1))
        self.assertEqual(r_vol.status_code, 403)

        # Club Head creating team in their club -> 201
        r_head = self.client.post("/api/v1/teams/", json={"name": "NLP Team", "description": "NLP", "club_id": self.club1.id}, headers=self._auth_headers(self.head1))
        self.assertEqual(r_head.status_code, 201)

        # Club Head attempting to create team in another club -> 403
        r_head_cross = self.client.post("/api/v1/teams/", json={"name": "Drone Team", "description": "Drone", "club_id": self.club2.id}, headers=self._auth_headers(self.head1))
        self.assertEqual(r_head_cross.status_code, 403)

    def test_api_task_creation_permissions(self):
        """SubTeam Lead can create task for their subteam; Volunteer is denied; Subteam Lead cannot create for another subteam."""
        # Volunteer denied
        r_vol = self.client.post("/api/v1/tasks/", json={"title": "Vol Task", "event_id": self.ev1.id, "team_id": self.subteam1.id}, headers=self._auth_headers(self.vol1))
        self.assertEqual(r_vol.status_code, 403)

        # Lead 1 creating task for Subteam 1 -> 200
        r_lead1 = self.client.post("/api/v1/tasks/", json={"title": "Model Evaluation", "event_id": self.ev1.id, "team_id": self.subteam1.id}, headers=self._auth_headers(self.lead1))
        self.assertEqual(r_lead1.status_code, 200)

        # Lead 1 attempting to create task for Subteam 2 -> 403
        r_lead1_cross = self.client.post("/api/v1/tasks/", json={"title": "UI Bug", "event_id": self.ev1.id, "team_id": self.subteam2.id}, headers=self._auth_headers(self.lead1))
        self.assertEqual(r_lead1_cross.status_code, 403)

    def test_api_task_delete_permissions(self):
        """Club Head and Admin can delete task; Volunteer and SubTeam Lead are denied with 403."""
        r_vol = self.client.delete(f"/api/v1/tasks/{self.task_s1.id}", headers=self._auth_headers(self.vol1))
        self.assertEqual(r_vol.status_code, 403)

        r_lead = self.client.delete(f"/api/v1/tasks/{self.task_s1.id}", headers=self._auth_headers(self.lead1))
        self.assertEqual(r_lead.status_code, 403)

        # Head 1 deleting task in their club -> 200
        r_head = self.client.delete(f"/api/v1/tasks/{self.task_s1.id}", headers=self._auth_headers(self.head1))
        self.assertEqual(r_head.status_code, 200)

    def test_api_task_status_update_by_assigned_volunteer(self):
        """Assigned volunteer can update status, but non-assigned volunteer cannot."""
        # Vol1 is assigned to task_s1 -> updating status succeeds
        r_status = self.client.put(f"/api/v1/tasks/{self.task_s1.id}", json={"status": "IN_PROGRESS"}, headers=self._auth_headers(self.vol1))
        self.assertEqual(r_status.status_code, 200)

        # Vol2 is NOT assigned to task_s1 -> status update denied
        r_vol2 = self.client.put(f"/api/v1/tasks/{self.task_s1.id}", json={"status": "DONE"}, headers=self._auth_headers(self.vol2))
        self.assertEqual(r_vol2.status_code, 403)

    def test_api_announcements_permissions(self):
        """Volunteers cannot create announcements; Club Head can."""
        r_vol = self.client.post("/api/v1/announcements/", json={"title": "Test", "content": "Hello", "event_id": self.ev1.id}, headers=self._auth_headers(self.vol1))
        self.assertEqual(r_vol.status_code, 403)

        r_head = self.client.post("/api/v1/announcements/", json={"title": "AI Summit Opening", "content": "Welcome", "event_id": self.ev1.id}, headers=self._auth_headers(self.head1))
        self.assertEqual(r_head.status_code, 200)

    def test_api_events_delete_and_cross_club_protection(self):
        """Volunteers cannot delete events; Club Head 1 cannot delete Club 2 event; Club Head 1 can delete Club 1 event."""
        # Volunteer cannot delete event
        r_vol = self.client.delete(f"/api/v1/events/{self.ev1.id}", headers=self._auth_headers(self.vol1))
        self.assertEqual(r_vol.status_code, 403)

        # Head 1 cannot delete Club 2 event
        r_head_cross = self.client.delete(f"/api/v1/events/{self.ev2.id}", headers=self._auth_headers(self.head1))
        self.assertEqual(r_head_cross.status_code, 403)

        # Head 1 can delete Club 1 event
        r_head = self.client.delete(f"/api/v1/events/{self.ev1.id}", headers=self._auth_headers(self.head1))
        self.assertEqual(r_head.status_code, 200)


if __name__ == "__main__":
    unittest.main()

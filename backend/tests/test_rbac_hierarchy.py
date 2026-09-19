import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

import app.db.base
from app.db.base_class import Base
from app.core.permissions import seed_permissions
from app.models.user import User, UserRole
from app.models.team import Club, Team, TeamMembership, ClubMembership, TeamRole, ClubRole
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.event import Event, EventStatus
from app.models.task import Task, TaskStatus, TaskPriority, TaskAssignment
from app.models.audit_log import AuditLog
from app.services.authz import AuthorizationService
from app.services.org_service import OrganizationService
from ai.workflows.proposal_service import create_proposal, apply_proposal
from ai.schemas.ai_plan import EventPlan, GeneratedTask


class TestRBACHierarchy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
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

        # 1. System Admin
        self.admin = User(
            email="admin@test.org",
            hashed_password="pw",
            full_name="Global Admin",
            role=UserRole.ADMIN,
            is_active=True
        )

        # 2. Club A: AI Club
        self.club_a = Club(name="AI Club", description="AI and Data Science")
        # 3. Club B: Robotics Club
        self.club_b = Club(name="Robotics Club", description="Robotics and Embedded")
        self.db.add_all([self.admin, self.club_a, self.club_b])
        self.db.flush()

        # Club A Head & Club B Head
        self.head_a = User(
            email="head_a@test.org",
            hashed_password="pw",
            full_name="Club Head A",
            role=UserRole.CLUB_HEAD,
            club_id=self.club_a.id,
            is_active=True
        )
        self.head_b = User(
            email="head_b@test.org",
            hashed_password="pw",
            full_name="Club Head B",
            role=UserRole.CLUB_HEAD,
            club_id=self.club_b.id,
            is_active=True
        )
        self.db.add_all([self.head_a, self.head_b])
        self.db.flush()

        # SubTeams for Club A
        self.team_ml = Team(name="ML Team", club_id=self.club_a.id)
        self.team_web = Team(name="Web Team", club_id=self.club_a.id)
        self.db.add_all([self.team_ml, self.team_web])
        self.db.flush()

        # SubTeam Leads for Club A
        self.lead_ml = User(
            email="lead_ml@test.org",
            hashed_password="pw",
            full_name="ML Lead",
            role=UserRole.SUBTEAM_LEAD,
            club_id=self.club_a.id,
            subteam_id=self.team_ml.id,
            is_active=True
        )
        self.team_ml.lead_id = self.lead_ml.id

        self.lead_web = User(
            email="lead_web@test.org",
            hashed_password="pw",
            full_name="Web Lead",
            role=UserRole.SUBTEAM_LEAD,
            club_id=self.club_a.id,
            subteam_id=self.team_web.id,
            is_active=True
        )
        self.team_web.lead_id = self.lead_web.id

        # Case 2: SubTeam Volunteer (belongs to ML team)
        self.vol_ml = User(
            email="vol_ml@test.org",
            hashed_password="pw",
            full_name="ML Volunteer",
            role=UserRole.VOLUNTEER,
            club_id=self.club_a.id,
            subteam_id=self.team_ml.id,
            is_active=True
        )

        # Case 1: Direct Club Volunteer (belongs to Club A, but subteam_id is None)
        self.vol_direct = User(
            email="vol_direct@test.org",
            hashed_password="pw",
            full_name="Direct Club Volunteer",
            role=UserRole.VOLUNTEER,
            club_id=self.club_a.id,
            subteam_id=None,
            is_active=True
        )

        self.db.add_all([self.lead_ml, self.lead_web, self.vol_ml, self.vol_direct])
        self.db.flush()

        # Volunteer profiles
        self.vol_profile_ml = Volunteer(user_id=self.vol_ml.id, club_id=self.club_a.id, subteam_id=self.team_ml.id)
        self.vol_profile_direct = Volunteer(user_id=self.vol_direct.id, club_id=self.club_a.id, subteam_id=None)
        self.db.add_all([self.vol_profile_ml, self.vol_profile_direct])
        self.db.flush()

        # Event in Club A
        self.event_a = Event(
            title="AI Summit",
            club_id=self.club_a.id,
            date=datetime.utcnow() + timedelta(days=10),
            created_by=self.head_a.id
        )
        # Event in Club B
        self.event_b = Event(
            title="Robotics Expo",
            club_id=self.club_b.id,
            date=datetime.utcnow() + timedelta(days=15),
            created_by=self.head_b.id
        )
        self.db.add_all([self.event_a, self.event_b])
        self.db.flush()

        # Task in ML Team (Club A)
        self.task_ml = Task(
            title="Train model",
            event_id=self.event_a.id,
            team_id=self.team_ml.id,
            created_by=self.lead_ml.id
        )
        # Task in Web Team (Club A)
        self.task_web = Task(
            title="Build landing page",
            event_id=self.event_a.id,
            team_id=self.team_web.id,
            created_by=self.lead_web.id
        )
        # Task in Club B
        self.task_b = Task(
            title="Assemble chassis",
            event_id=self.event_b.id,
            created_by=self.head_b.id
        )
        self.db.add_all([self.task_ml, self.task_web, self.task_b])
        self.db.flush()

        # Assign vol_ml to task_ml
        self.db.add(TaskAssignment(task_id=self.task_ml.id, volunteer_id=self.vol_profile_ml.id))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    # ─────────────────────────────────────────────────────────────
    # 1. Admin Full Scope & Assignments
    # ─────────────────────────────────────────────────────────────

    def test_admin_has_unrestricted_access(self):
        """Admin can access all clubs, teams, tasks across the system."""
        self.assertTrue(AuthorizationService.can_access_club(self.db, self.admin, self.club_a.id))
        self.assertTrue(AuthorizationService.can_access_club(self.db, self.admin, self.club_b.id))
        self.assertTrue(AuthorizationService.can_access_subteam(self.db, self.admin, self.team_ml.id))
        self.assertTrue(AuthorizationService.can_manage_task(self.db, self.admin, self.task_ml.id))
        self.assertTrue(AuthorizationService.can_manage_task(self.db, self.admin, self.task_b.id))

    def test_admin_assigns_club_head(self):
        """Admin assigns a new user as Club Head and creates audit log."""
        new_user = User(email="new_head@test.org", hashed_password="pw", full_name="New Head", role=UserRole.VOLUNTEER, is_active=True)
        self.db.add(new_user)
        self.db.commit()

        res = OrganizationService.assign_club_head(
            self.db, self.admin, self.club_a.id, new_user.id, reason="Appointed by Council"
        )
        self.assertTrue(res["success"])
        self.assertEqual(new_user.role, UserRole.CLUB_HEAD)
        self.assertEqual(new_user.club_id, self.club_a.id)

        # Audit log verified
        audit = self.db.query(AuditLog).filter(AuditLog.action == "CLUB_HEAD_ASSIGNED", AuditLog.entity_id == new_user.id).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user_id, self.admin.id)

    # ─────────────────────────────────────────────────────────────
    # 2. Club Head Authority & Multi-Club Tenant Isolation
    # ─────────────────────────────────────────────────────────────

    def test_club_head_scoped_to_own_club(self):
        """Club Head can manage all teams and tasks in own club, but is DENIED on Club B."""
        # Own club: ALLOW
        self.assertTrue(AuthorizationService.can_access_club(self.db, self.head_a, self.club_a.id))
        self.assertTrue(AuthorizationService.can_access_subteam(self.db, self.head_a, self.team_ml.id))
        self.assertTrue(AuthorizationService.can_access_subteam(self.db, self.head_a, self.team_web.id))
        self.assertTrue(AuthorizationService.can_manage_task(self.db, self.head_a, self.task_ml.id))
        self.assertTrue(AuthorizationService.can_manage_task(self.db, self.head_a, self.task_web.id))

        # Other club: DENY
        self.assertFalse(AuthorizationService.can_access_club(self.db, self.head_a, self.club_b.id))
        self.assertFalse(AuthorizationService.can_manage_task(self.db, self.head_a, self.task_b.id))

    def test_club_head_cannot_appoint_club_head(self):
        """Club Head cannot appoint another Club Head (Admin only)."""
        candidate = User(email="cand@test.org", hashed_password="pw", full_name="Candidate", role=UserRole.VOLUNTEER, club_id=self.club_a.id, is_active=True)
        self.db.add(candidate)
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            OrganizationService.assign_club_head(self.db, self.head_a, self.club_a.id, candidate.id)
        self.assertEqual(ctx.exception.status_code, 403)

    # ─────────────────────────────────────────────────────────────
    # 3. SubTeam Lead Authority & Team Isolation
    # ─────────────────────────────────────────────────────────────

    def test_subteam_lead_can_manage_own_team_only(self):
        """SubTeam Lead can manage tasks in own team, but is DENIED on other teams."""
        # Own team: ALLOW
        self.assertTrue(AuthorizationService.can_access_subteam(self.db, self.lead_ml, self.team_ml.id))
        self.assertTrue(AuthorizationService.can_manage_task(self.db, self.lead_ml, self.task_ml.id))

        # Other team in same club: DENIED management
        self.assertFalse(AuthorizationService.can_manage_task(self.db, self.lead_ml, self.task_web.id))

        # Other club task: DENIED
        self.assertFalse(AuthorizationService.can_manage_task(self.db, self.lead_ml, self.task_b.id))

    def test_subteam_lead_assignment_boundaries(self):
        """SubTeam Lead can assign volunteers within own subteam, but cannot assign across teams."""
        # Assigning ML volunteer to ML task: ALLOW
        self.assertTrue(AuthorizationService.can_assign_task(self.db, self.lead_ml, self.task_ml.id, self.vol_profile_ml.id))

        # Assigning ML volunteer to Web task: DENY
        self.assertFalse(AuthorizationService.can_assign_task(self.db, self.lead_ml, self.task_web.id, self.vol_profile_ml.id))

    # ─────────────────────────────────────────────────────────────
    # 4. Volunteer Authority & Restrictions
    # ─────────────────────────────────────────────────────────────

    def test_volunteer_can_only_access_permitted_work(self):
        """Volunteer can view and update status of assigned task, but cannot manage other tasks."""
        # Assigned task: can view and update status
        self.assertTrue(AuthorizationService.can_access_task(self.db, self.vol_ml, self.task_ml.id))
        self.assertTrue(AuthorizationService.can(self.db, self.vol_ml, "task.status.update", resource=self.task_ml))

        # Cannot delete, create, or assign tasks
        self.assertFalse(AuthorizationService.can(self.db, self.vol_ml, "task.delete", resource=self.task_ml))
        self.assertFalse(AuthorizationService.can(self.db, self.vol_ml, "task.create"))
        self.assertFalse(AuthorizationService.can_manage_task(self.db, self.vol_ml, self.task_web.id))

    def test_case_1_direct_volunteer_without_subteam(self):
        """Case 1: Volunteer belongs directly to Club with no SubTeam."""
        self.assertEqual(self.vol_direct.club_id, self.club_a.id)
        self.assertIsNone(self.vol_direct.subteam_id)

        # Create a direct task under event_a without a team
        direct_task = Task(title="General Event Help", event_id=self.event_a.id, team_id=None)
        self.db.add(direct_task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=direct_task.id, volunteer_id=self.vol_profile_direct.id))
        self.db.commit()

        # Direct volunteer can access their assigned task
        self.assertTrue(AuthorizationService.can_access_task(self.db, self.vol_direct, direct_task.id))

    # ─────────────────────────────────────────────────────────────
    # 5. Invariant Validations
    # ─────────────────────────────────────────────────────────────

    def test_subteam_lead_without_subteam_rejected(self):
        """Invariant: Cannot be SUBTEAM_LEAD without a subteam_id."""
        candidate = User(email="lead_err@test.org", hashed_password="pw", full_name="Err Lead", role=UserRole.VOLUNTEER, club_id=self.club_a.id, is_active=True)
        self.db.add(candidate)
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            OrganizationService.assign_user_role(
                self.db, self.admin, candidate.id, new_role="SUBTEAM_LEAD", club_id=self.club_a.id, subteam_id=None
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_cross_club_subteam_assignment_rejected(self):
        """Invariant: Volunteer cannot belong to a SubTeam from another Club."""
        user_b = User(email="user_b@test.org", hashed_password="pw", full_name="User B", role=UserRole.VOLUNTEER, club_id=self.club_b.id, is_active=True)
        self.db.add(user_b)
        self.db.commit()

        # Attempt to assign User B (from Club B) to team_ml (which belongs to Club A)
        with self.assertRaises(HTTPException) as ctx:
            OrganizationService.assign_user_role(
                self.db, self.admin, user_b.id, new_role="VOLUNTEER", club_id=self.club_b.id, subteam_id=self.team_ml.id
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_self_promotion_rejected(self):
        """Invariant: Normal users cannot promote themselves."""
        with self.assertRaises(HTTPException) as ctx:
            OrganizationService.assign_user_role(
                self.db, self.vol_ml, self.vol_ml.id, new_role="SUBTEAM_LEAD", subteam_id=self.team_ml.id
            )
        self.assertEqual(ctx.exception.status_code, 403)

    # ─────────────────────────────────────────────────────────────
    # 6. AI Tool & Proposal Authorization
    # ─────────────────────────────────────────────────────────────

    def test_ai_proposal_subteam_lead_cross_team_rejected(self):
        """SubTeam Lead cannot use AI to propose moving a task to another SubTeam."""
        changes = [{
            "entity_type": "Task",
            "entity_id": self.task_ml.id,
            "action": "UPDATE",
            "proposed_data": {"team_id": self.team_web.id}  # Not their team!
        }]

        with self.assertRaises(HTTPException) as ctx:
            create_proposal(self.db, user_id=self.lead_ml.id, intent="Move to Web Team", changes=changes)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_ai_proposal_volunteer_bulk_action_rejected(self):
        """Volunteer cannot use AI to generate event plans or create tasks."""
        plan = EventPlan(event_title="Unauthorized Event", tasks=[GeneratedTask(title="Fake Task")])
        with self.assertRaises(HTTPException) as ctx:
            create_proposal(self.db, user_id=self.vol_ml.id, intent="Plan Event", event_plan=plan)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_ai_proposal_club_head_authorized(self):
        """Club Head can create proposals across their club."""
        changes = [{
            "entity_type": "Task",
            "entity_id": self.task_ml.id,
            "action": "UPDATE",
            "proposed_data": {"priority": "HIGH"}
        }]
        res = create_proposal(self.db, user_id=self.head_a.id, intent="Escalate priority", changes=changes)
        self.assertIsNotNone(res.proposal_id)
        self.assertEqual(res.status, "PENDING")

    # ─────────────────────────────────────────────────────────────
    # 7. Hierarchy Tree Generation
    # ─────────────────────────────────────────────────────────────

    def test_hierarchy_tree_structure(self):
        """Hierarchy tree reflects real DB relationships for Club Head, SubTeams, and Direct Volunteers."""
        tree = OrganizationService.get_club_hierarchy(self.db, self.club_a.id)
        self.assertEqual(tree["club_id"], self.club_a.id)
        self.assertEqual(tree["club_head"]["id"], self.head_a.id)
        self.assertEqual(len(tree["subteams"]), 2)
        # Direct volunteers
        direct_names = [v["full_name"] for v in tree["direct_volunteers"]]
        self.assertIn("Direct Club Volunteer", direct_names)


if __name__ == "__main__":
    unittest.main()

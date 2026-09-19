import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db.base
from app.db.base_class import Base
from app.core.permissions import seed_permissions
from app.models.user import User, UserRole
from app.models.team import Club, Team, TeamMembership, ClubMembership, EventMembership, TeamRole, ClubRole, EventRole
from app.models.permission import Permission, UserPermission, ScopeType, PermissionEffect
from app.models.event import Event, EventStatus
from app.models.task import Task, TaskStatus, TaskPriority, TaskAssignment
from app.models.volunteer import Volunteer, VolunteerStatus
from app.services.authz import AuthorizationService
from fastapi import HTTPException


class TestHierarchicalAuthorization(unittest.TestCase):
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

        # 1. Create Club
        self.club = Club(name="Club of AI", description="Premier College AI Club")
        self.db.add(self.club)
        self.db.flush()

        # 2. Create Users
        # Club Leader
        self.club_leader = User(
            email="priya@club.org",
            hashed_password="pw",
            full_name="Priya Sharma",
            is_active=True
        )
        # AWS Team Leader
        self.aws_leader = User(
            email="rahul@club.org",
            hashed_password="pw",
            full_name="Rahul Verma",
            is_active=True
        )
        # ML Team Leader
        self.ml_leader = User(
            email="sneha@club.org",
            hashed_password="pw",
            full_name="Sneha Patel",
            is_active=True
        )
        # AWS Team Member
        self.aws_member = User(
            email="rohan@club.org",
            hashed_password="pw",
            full_name="Rohan Roy",
            is_active=True
        )
        # ML-only Volunteer
        self.ml_volunteer = User(
            email="tanvi@club.org",
            hashed_password="pw",
            full_name="Tanvi Gupta",
            is_active=True
        )
        # Dual-role user: AWS Leader & ML Member
        self.dual_user = User(
            email="vikram@club.org",
            hashed_password="pw",
            full_name="Vikram Das",
            is_active=True
        )
        # Event Coordinator
        self.coordinator = User(
            email="maya@club.org",
            hashed_password="pw",
            full_name="Maya Rao",
            is_active=True
        )

        self.db.add_all([
            self.club_leader, self.aws_leader, self.ml_leader,
            self.aws_member, self.ml_volunteer, self.dual_user, self.coordinator
        ])
        self.db.flush()

        # Assign Club Leader
        self.db.add(ClubMembership(club_id=self.club.id, user_id=self.club_leader.id, role=ClubRole.CLUB_LEADER))

        # 3. Create Teams
        self.aws_team = Team(club_id=self.club.id, name="AWS Team", description="Cloud infrastructure")
        self.ml_team = Team(club_id=self.club.id, name="ML Team", description="Machine Learning & AI models")
        self.marketing_team = Team(club_id=self.club.id, name="Marketing Team", description="Outreach & Socials")
        self.db.add_all([self.aws_team, self.ml_team, self.marketing_team])
        self.db.flush()

        # 4. Assign Team Memberships
        self.db.add_all([
            TeamMembership(team_id=self.aws_team.id, user_id=self.aws_leader.id, role=TeamRole.TEAM_LEADER),
            TeamMembership(team_id=self.ml_team.id, user_id=self.ml_leader.id, role=TeamRole.TEAM_LEADER),
            TeamMembership(team_id=self.aws_team.id, user_id=self.aws_member.id, role=TeamRole.TEAM_MEMBER),
            TeamMembership(team_id=self.ml_team.id, user_id=self.ml_volunteer.id, role=TeamRole.TEAM_MEMBER),
            # Dual role:
            TeamMembership(team_id=self.aws_team.id, user_id=self.dual_user.id, role=TeamRole.TEAM_LEADER),
            TeamMembership(team_id=self.ml_team.id, user_id=self.dual_user.id, role=TeamRole.TEAM_MEMBER),
        ])

        # 5. Create Volunteer Profiles
        self.vol_aws_member = Volunteer(user_id=self.aws_member.id, skills="AWS, Python", status=VolunteerStatus.ACTIVE)
        self.vol_ml_volunteer = Volunteer(user_id=self.ml_volunteer.id, skills="PyTorch, NLP", status=VolunteerStatus.ACTIVE)
        self.db.add_all([self.vol_aws_member, self.vol_ml_volunteer])
        self.db.flush()

        # 6. Create Event & Assign Coordinator
        self.event = Event(
            title="Hackathon 2026",
            description="Annual Flagship Hackathon",
            date=datetime.utcnow() + timedelta(days=14),
            venue="Tech Auditorium",
            budget=10000.0,
            status=EventStatus.PUBLISHED,
            created_by=self.club_leader.id
        )
        self.db.add(self.event)
        self.db.flush()

        self.db.add(EventMembership(event_id=self.event.id, user_id=self.coordinator.id, role=EventRole.EVENT_COORDINATOR))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    # ── Scenario 1: Club Leader has full club scope ──
    def test_scenario_1_club_leader_full_authority(self):
        """Club Leader can create teams, assign leaders, and delete any task."""
        self.assertTrue(AuthorizationService.is_club_leader(self.db, self.club_leader))
        self.assertTrue(AuthorizationService.can(self.db, self.club_leader, "club.manage"))
        self.assertTrue(AuthorizationService.can(self.db, self.club_leader, "team.create"))
        self.assertTrue(AuthorizationService.can(self.db, self.club_leader, "team.leader.assign"))

        # Create a task in AWS team
        task = Task(event_id=self.event.id, team_id=self.aws_team.id, title="Configure VPC", status=TaskStatus.TODO)
        self.db.add(task)
        self.db.commit()

        # Club Leader can delete any task across any team
        self.assertTrue(AuthorizationService.can(self.db, self.club_leader, "task.delete", resource=task))

    # ── Scenario 2: Team Leader creates task for their own team ──
    def test_scenario_2_team_leader_creates_task_own_team(self):
        """Team Leader - AWS creates a task for AWS Team -> ALLOWED."""
        can_create = AuthorizationService.can(
            self.db, self.aws_leader, "task.create", scope_type="TEAM", scope_id=self.aws_team.id
        )
        self.assertTrue(can_create)

    # ── Scenario 3: Team Leader tries to create task in another team ──
    def test_scenario_3_team_leader_cannot_create_task_other_team(self):
        """Team Leader - AWS tries to create a task in ML Team -> REJECTED (Forbidden)."""
        can_create = AuthorizationService.can(
            self.db, self.aws_leader, "task.create", scope_type="TEAM", scope_id=self.ml_team.id
        )
        self.assertFalse(can_create)

        with self.assertRaises(HTTPException) as cm:
            AuthorizationService.require_permission(
                self.db, self.aws_leader, "task.create", scope_type="TEAM", scope_id=self.ml_team.id
            )
        self.assertEqual(cm.exception.status_code, 403)

    # ── Scenario 4: Cross-team assignment rejected ──
    def test_scenario_4_cross_team_assignment_rejected(self):
        """Team Leader - AWS tries to assign a task to a volunteer who belongs only to ML Team -> REJECTED."""
        task = Task(event_id=self.event.id, team_id=self.aws_team.id, title="Setup S3 Bucket", status=TaskStatus.TODO)
        self.db.add(task)
        self.db.commit()

        # Check membership of ML volunteer in AWS team
        is_member = self.db.query(TeamMembership).filter(
            TeamMembership.team_id == task.team_id,
            TeamMembership.user_id == self.vol_ml_volunteer.user_id
        ).first()
        self.assertIsNone(is_member, "Volunteer Tanvi must not be in AWS team")

        # Rahul Verma (AWS Leader) can assign within AWS team
        self.assertTrue(AuthorizationService.can(self.db, self.aws_leader, "task.assign", resource=task))

    # ── Scenario 5: Team Member cannot delete task ──
    def test_scenario_5_team_member_cannot_delete_task(self):
        """Team Member tries to delete a task -> REJECTED: Team Members cannot delete tasks."""
        task = Task(event_id=self.event.id, team_id=self.aws_team.id, title="Setup CloudFront", status=TaskStatus.TODO)
        self.db.add(task)
        self.db.commit()

        can_delete = AuthorizationService.can(self.db, self.aws_member, "task.delete", resource=task)
        self.assertFalse(can_delete)

        with self.assertRaises(HTTPException) as cm:
            AuthorizationService.require_permission(self.db, self.aws_member, "task.delete", resource=task)
        self.assertEqual(cm.exception.status_code, 403)

    # ── Scenario 6: Team Member updates task status of assigned task ──
    def test_scenario_6_team_member_updates_status_assigned_task(self):
        """Team Member updates task status from 'TODO' to 'IN_PROGRESS' for their assigned task -> ALLOWED."""
        task = Task(event_id=self.event.id, team_id=self.aws_team.id, title="Deploy Docker", status=TaskStatus.TODO)
        self.db.add(task)
        self.db.flush()

        # Assign Rohan (aws_member)
        assignment = TaskAssignment(task_id=task.id, volunteer_id=self.vol_aws_member.id)
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(task)

        # Rohan can update status of this assigned task
        can_update_status = AuthorizationService.can(self.db, self.aws_member, "task.status.update", resource=task)
        self.assertTrue(can_update_status)

        # But Rohan CANNOT update arbitrary fields (e.g. task.update)
        can_update_task = AuthorizationService.can(self.db, self.aws_member, "task.update", resource=task)
        self.assertFalse(can_update_task)

    # ── Scenario 7: Team Member cannot reassign tasks ──
    def test_scenario_7_team_member_cannot_reassign_task(self):
        """Team Member tries to reassign a task -> REJECTED."""
        task = Task(event_id=self.event.id, team_id=self.aws_team.id, title="Kubernetes Pods", status=TaskStatus.TODO)
        self.db.add(task)
        self.db.commit()

        can_assign = AuthorizationService.can(self.db, self.aws_member, "task.assign", resource=task)
        self.assertFalse(can_assign)

    # ── Scenario 8: Dual-Role Member (AWS Leader AND ML Member) ──
    def test_scenario_8_dual_role_permissions(self):
        """User is Team Leader for AWS AND Team Member for ML -> Can manage AWS tasks, but only execute assigned ML tasks."""
        aws_task = Task(event_id=self.event.id, team_id=self.aws_team.id, title="IAM Policies", status=TaskStatus.TODO)
        ml_task = Task(event_id=self.event.id, team_id=self.ml_team.id, title="Train LLM", status=TaskStatus.TODO)
        self.db.add_all([aws_task, ml_task])
        self.db.commit()

        # AWS Team: Has Leader permissions
        self.assertTrue(AuthorizationService.can(self.db, self.dual_user, "task.create", scope_type="TEAM", scope_id=self.aws_team.id))
        self.assertTrue(AuthorizationService.can(self.db, self.dual_user, "task.assign", resource=aws_task))
        self.assertTrue(AuthorizationService.can(self.db, self.dual_user, "task.update", resource=aws_task))

        # ML Team: Only Team Member permissions
        self.assertFalse(AuthorizationService.can(self.db, self.dual_user, "task.create", scope_type="TEAM", scope_id=self.ml_team.id))
        self.assertFalse(AuthorizationService.can(self.db, self.dual_user, "task.assign", resource=ml_task))
        self.assertFalse(AuthorizationService.can(self.db, self.dual_user, "task.delete", resource=ml_task))

    # ── Scenario 9: Event Coordinator manages tasks across teams for that event ──
    def test_scenario_9_event_coordinator_scope(self):
        """Event Coordinator for 'Hackathon 2026' can manage tasks and volunteers across all teams for that event."""
        task_aws = Task(event_id=self.event.id, team_id=self.aws_team.id, title="Server Cluster", status=TaskStatus.TODO)
        task_ml = Task(event_id=self.event.id, team_id=self.ml_team.id, title="Model Serving", status=TaskStatus.TODO)
        self.db.add_all([task_aws, task_ml])
        self.db.commit()

        # Event Coordinator has event-level scope across both teams within this event
        self.assertTrue(AuthorizationService.can(self.db, self.coordinator, "task.create", scope_type="EVENT", scope_id=self.event.id))
        self.assertTrue(AuthorizationService.can(self.db, self.coordinator, "task.assign", resource=task_aws))
        self.assertTrue(AuthorizationService.can(self.db, self.coordinator, "task.assign", resource=task_ml))
        self.assertTrue(AuthorizationService.can(self.db, self.coordinator, "task.delete", resource=task_aws))

        # But for another event, Maya has no authority
        other_event = Event(
            title="Design Bootcamp",
            date=datetime.utcnow() + timedelta(days=30),
            created_by=self.club_leader.id
        )
        self.db.add(other_event)
        self.db.flush()
        other_task = Task(event_id=other_event.id, team_id=self.aws_team.id, title="Bootcamp AWS Setup")
        self.db.add(other_task)
        self.db.commit()

        self.assertFalse(AuthorizationService.can(self.db, self.coordinator, "task.assign", resource=other_task))

    # ── Scenario 10: Explicit Permission Override ──
    def test_scenario_10_explicit_permission_override(self):
        """Club Leader grants 'task.create' to Team Member Rohan -> Rohan can create tasks despite being a Team Member."""
        # Initially, Rohan (aws_member) cannot create tasks
        self.assertFalse(AuthorizationService.can(self.db, self.aws_member, "task.create", scope_type="TEAM", scope_id=self.aws_team.id))

        # Find permission id for task.create
        perm = self.db.query(Permission).filter(Permission.key == "task.create").first()
        self.assertIsNotNone(perm)

        # Add explicit override: ALLOW task.create
        override = UserPermission(
            user_id=self.aws_member.id,
            permission_id=perm.id,
            scope_type=ScopeType.GLOBAL,
            effect=PermissionEffect.ALLOW
        )
        self.db.add(override)
        self.db.commit()

        # Now Rohan CAN create tasks
        self.assertTrue(AuthorizationService.can(self.db, self.aws_member, "task.create", scope_type="TEAM", scope_id=self.aws_team.id))

        # Explicit DENY override takes precedence over role
        override.effect = PermissionEffect.DENY
        self.db.commit()
        self.assertFalse(AuthorizationService.can(self.db, self.aws_member, "task.create", scope_type="TEAM", scope_id=self.aws_team.id))

    # ── Scenario 11: AI Agent Command Scoping ──
    def test_scenario_11_ai_command_scoping(self):
        """AI command scopes unassigned tasks to authorized team and provides explanatory breakdown."""
        from ai.tools.command_tool import _handle_assignment_command

        # Create unowned tasks across multiple teams
        aws_t1 = Task(event_id=self.event.id, team_id=self.aws_team.id, title="AWS Task 1", status=TaskStatus.TODO)
        aws_t2 = Task(event_id=self.event.id, team_id=self.aws_team.id, title="AWS Task 2", status=TaskStatus.TODO)
        ml_t1 = Task(event_id=self.event.id, team_id=self.ml_team.id, title="ML Task 1", status=TaskStatus.TODO)
        ml_t2 = Task(event_id=self.event.id, team_id=self.ml_team.id, title="ML Task 2", status=TaskStatus.TODO)
        ml_t3 = Task(event_id=self.event.id, team_id=self.ml_team.id, title="ML Task 3", status=TaskStatus.TODO)
        mkt_t1 = Task(event_id=self.event.id, team_id=self.marketing_team.id, title="Marketing Task 1", status=TaskStatus.TODO)

        self.db.add_all([aws_t1, aws_t2, ml_t1, ml_t2, ml_t3, mkt_t1])
        self.db.commit()

        # Rahul (AWS Team Leader) asks AI to assign unowned tasks to Rohan
        result = _handle_assignment_command(
            db=self.db,
            command="Assign all unowned tasks to Rohan",
            event_id=self.event.id,
            user_id=self.aws_leader.id,
            auto_confirm=False
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "AWAITING_CONFIRMATION")
        self.assertEqual(len(result["tasks_affected"]), 2)
        self.assertIn(aws_t1.id, result["tasks_affected"])
        self.assertIn(aws_t2.id, result["tasks_affected"])
        self.assertNotIn(ml_t1.id, result["tasks_affected"])
        self.assertNotIn(mkt_t1.id, result["tasks_affected"])

        # Check informative feedback breakdown
        msg = result["message"]
        self.assertIn("AWS Team", msg)
        self.assertIn("ML Team: 3", msg)
        self.assertIn("Marketing Team: 1", msg)

    # ── Scenario 12: User Authz Summary Structure ──
    def test_scenario_12_user_authz_summary(self):
        """Verify summary returns complete profile of roles, teams, and permissions."""
        leader_summary = AuthorizationService.get_user_authz_summary(self.db, self.club_leader)
        self.assertTrue(leader_summary["is_club_leader"])
        self.assertEqual(leader_summary["club_role"], "CLUB_LEADER")
        self.assertIn("club.manage", leader_summary["permissions"])
        self.assertIn("team.create", leader_summary["permissions"])

        dual_summary = AuthorizationService.get_user_authz_summary(self.db, self.dual_user)
        self.assertFalse(dual_summary["is_club_leader"])
        team_roles_dict = {t["id"]: t["role"] for t in dual_summary["teams"]}
        self.assertEqual(team_roles_dict.get(self.aws_team.id), "TEAM_LEADER")
        self.assertEqual(team_roles_dict.get(self.ml_team.id), "TEAM_MEMBER")


if __name__ == "__main__":
    unittest.main()

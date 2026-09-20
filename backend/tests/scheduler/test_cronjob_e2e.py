"""
End-to-end cron job test suite using codingarmy123@gmail.com as reference email.

Tests the full check_overdue_volunteer_tasks cron job with:
  1. Overdue detection → Team Lead notification (Level 1)
  2. Escalation → Club Head notification (Level 2)
  3. Unassigned overdue task → leadership notification
  4. Idempotency — duplicate run produces no new notifications
  5. Deadline extension — extended task stops being flagged
  6. Completed task ignored
  7. Admin API endpoint trigger
"""
import unittest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.base_class import Base
import app.db.base  # registers all models (including Notification)
from app.models.user import User, UserRole
from app.models.team import Club, Team, TeamMembership, ClubMembership, TeamRole, ClubRole
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.event import Event, EventStatus
from app.models.task import Task, TaskStatus, TaskPriority, TaskAssignment
from app.models.notification import (
    Notification,
    NotificationType,
    NotificationSeverity,
    EscalationLevelRole,
)
from app.scheduler.jobs import check_overdue_volunteer_tasks
from app.scheduler.scheduler import get_scheduler_status
from app.services.hierarchy_service import get_notification_recipients
from app.main import app
from app.api import deps


# ═══════════════════════════════════════════════════════════════════════
# TEST EMAIL — reference provided by the user
# ═══════════════════════════════════════════════════════════════════════
REFERENCE_EMAIL = "codingarmy123@gmail.com"


class CronJobE2ETestCase(unittest.TestCase):
    """In-memory SQLite base that sets up a full club hierarchy using codingarmy123@gmail.com."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()
        self.now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)

        # ── 1. System Admin ──
        self.admin = User(
            email="admin.cronjob@clubops.test",
            full_name="System Admin",
            hashed_password="pw",
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.db.add(self.admin)

        # ── 2. Club & Club Head ──
        self.club = Club(name="CodingArmy Club", description="Competitive Programming Club")
        self.db.add(self.club)
        self.db.flush()

        self.head = User(
            email="head.cronjob@clubops.test",
            full_name="Dr. Coding Head",
            hashed_password="pw",
            role=UserRole.CLUB_HEAD,
            club_id=self.club.id,
            is_active=True,
        )
        self.db.add(self.head)
        self.db.flush()

        self.club_membership = ClubMembership(
            user_id=self.head.id,
            club_id=self.club.id,
            role=ClubRole.CLUB_HEAD,
            is_active=True,
        )
        self.db.add(self.club_membership)

        # ── 3. SubTeam & Team Lead ──
        self.team = Team(name="Backend Dev Team", club_id=self.club.id)
        self.db.add(self.team)
        self.db.flush()

        self.lead = User(
            email="lead.cronjob@clubops.test",
            full_name="Team Lead Arjun",
            hashed_password="pw",
            role=UserRole.SUBTEAM_LEAD,
            club_id=self.club.id,
            subteam_id=self.team.id,
            is_active=True,
        )
        self.db.add(self.lead)
        self.db.flush()

        self.team.lead_id = self.lead.id
        self.team_membership = TeamMembership(
            user_id=self.lead.id,
            team_id=self.team.id,
            role=TeamRole.SUBTEAM_LEAD,
            is_active=True,
        )
        self.db.add(self.team_membership)

        # ── 4. Volunteer (codingarmy123@gmail.com) ──
        self.vol_user = User(
            email=REFERENCE_EMAIL,
            full_name="CodingArmy Volunteer",
            hashed_password="pw",
            role=UserRole.VOLUNTEER,
            club_id=self.club.id,
            subteam_id=self.team.id,
            is_active=True,
        )
        self.db.add(self.vol_user)
        self.db.flush()

        self.vol = Volunteer(
            user_id=self.vol_user.id,
            club_id=self.club.id,
            subteam_id=self.team.id,
            status=VolunteerStatus.ACTIVE,
        )
        self.db.add(self.vol)

        # ── 5. Event ──
        self.event = Event(
            title="CodeSprint 2026",
            club_id=self.club.id,
            date=self.now + timedelta(days=7),
            status=EventStatus.PUBLISHED,
            created_by=self.head.id,
        )
        self.db.add(self.event)
        self.db.commit()

    def tearDown(self):
        self.db.close()


# ═══════════════════════════════════════════════════════════════════════
# TEST 1 — Overdue Task Detection → Level 1 Team Lead Notification
# ═══════════════════════════════════════════════════════════════════════
class Test01_OverdueDetection(CronJobE2ETestCase):

    def test_overdue_task_notifies_team_lead(self):
        """An overdue task assigned to codingarmy123@gmail.com triggers Level 1 notification to Team Lead."""
        task = Task(
            title="Setup CI/CD Pipeline",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.IN_PROGRESS,
            due_date=self.now - timedelta(hours=2),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        # ── Assertions ──
        self.assertEqual(summary["overdue_tasks_found"], 1)
        self.assertEqual(summary["team_leads_notified"], 1)
        self.assertEqual(summary["errors"], 0)

        notif = self.db.query(Notification).filter(Notification.task_id == task.id).first()
        self.assertIsNotNone(notif, "Notification record must exist in DB")
        self.assertEqual(notif.recipient_id, self.lead.id)
        self.assertEqual(notif.notification_type, NotificationType.TASK_OVERDUE.value)
        self.assertEqual(notif.escalation_level, EscalationLevelRole.TEAM_LEAD.value)
        self.assertEqual(notif.severity, NotificationSeverity.WARNING.value)
        self.assertIn("CodingArmy Volunteer", notif.message)
        self.assertIn("Setup CI/CD Pipeline", notif.message)
        self.assertIn("CodeSprint 2026", notif.message)

        print(f"\n✅ TEST 1 PASSED: Overdue task detected for {REFERENCE_EMAIL}")
        print(f"   Notification → Team Lead '{self.lead.full_name}' (ID: {self.lead.id})")
        print(f"   Title: {notif.title}")
        print(f"   Severity: {notif.severity}")
        print(f"   Summary: {summary}")


# ═══════════════════════════════════════════════════════════════════════
# TEST 2 — Level 2 Escalation → Club Head Notification
# ═══════════════════════════════════════════════════════════════════════
class Test02_EscalationToHead(CronJobE2ETestCase):

    def test_escalation_notifies_club_head(self):
        """When overdue exceeds escalation threshold (60 min), Head receives Level 2 CRITICAL notification."""
        task = Task(
            title="Deploy Staging Server",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.TODO,
            due_date=self.now - timedelta(hours=3),  # 3 hours overdue > 60 min threshold
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        self.assertEqual(summary["team_leads_notified"], 1, "Team Lead should still get Level 1")
        self.assertEqual(summary["heads_notified"], 1, "Head should get Level 2 escalation")
        self.assertEqual(summary["errors"], 0)

        esc_notif = (
            self.db.query(Notification)
            .filter(
                Notification.task_id == task.id,
                Notification.notification_type == NotificationType.TASK_OVERDUE_ESCALATION.value,
            )
            .first()
        )
        self.assertIsNotNone(esc_notif, "Escalation notification must exist in DB")
        self.assertEqual(esc_notif.recipient_id, self.head.id)
        self.assertEqual(esc_notif.severity, NotificationSeverity.CRITICAL.value)
        self.assertIn("CodingArmy Volunteer", esc_notif.message)
        self.assertIn("Team Lead Arjun", esc_notif.message)

        print(f"\n✅ TEST 2 PASSED: Escalation triggered for {REFERENCE_EMAIL}")
        print(f"   Escalation → Club Head '{self.head.full_name}' (ID: {self.head.id})")
        print(f"   Level 1 (Team Lead) + Level 2 (Head) both dispatched")
        print(f"   Escalation severity: CRITICAL")
        print(f"   Summary: {summary}")


# ═══════════════════════════════════════════════════════════════════════
# TEST 3 — Unassigned Overdue Task → Leadership Notification
# ═══════════════════════════════════════════════════════════════════════
class Test03_UnassignedOverdueTask(CronJobE2ETestCase):

    def test_unassigned_overdue_notifies_leadership(self):
        """An overdue task with NO volunteer assignments sends notification to Team Lead or Head."""
        task = Task(
            title="Write API Documentation",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.TODO,
            due_date=self.now - timedelta(hours=1),
        )
        self.db.add(task)
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        self.assertEqual(summary["overdue_tasks_found"], 1)
        self.assertEqual(summary["errors"], 0)

        notif = self.db.query(Notification).filter(Notification.task_id == task.id).first()
        self.assertIsNotNone(notif, "Unassigned overdue must still generate notification")
        self.assertEqual(notif.notification_type, NotificationType.UNASSIGNED_TASK_OVERDUE.value)
        self.assertIn("Write API Documentation", notif.message)

        print(f"\n✅ TEST 3 PASSED: Unassigned overdue task detected")
        print(f"   Notification → Recipient ID {notif.recipient_id}")
        print(f"   Type: {notif.notification_type}")
        print(f"   Summary: {summary}")


# ═══════════════════════════════════════════════════════════════════════
# TEST 4 — Idempotency: Duplicate Run Creates No New Notifications
# ═══════════════════════════════════════════════════════════════════════
class Test04_Idempotency(CronJobE2ETestCase):

    def test_duplicate_cron_run_no_extra_notifications(self):
        """Running the cron job twice on the same data must NOT create duplicate notifications."""
        task = Task(
            title="Order Swag Kits",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.IN_PROGRESS,
            due_date=self.now - timedelta(minutes=45),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        # First run
        s1 = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)
        count_after_first = self.db.query(Notification).count()

        # Second run
        s2 = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)
        count_after_second = self.db.query(Notification).count()

        self.assertEqual(s1["team_leads_notified"], 1)
        self.assertEqual(s2["team_leads_notified"], 0, "Second run must NOT create new notifications")
        self.assertGreater(s2["skipped_duplicates"], 0, "Second run must report skipped duplicates")
        self.assertEqual(count_after_first, count_after_second, "DB notification count must be unchanged")

        print(f"\n✅ TEST 4 PASSED: Idempotency verified for {REFERENCE_EMAIL}")
        print(f"   Run 1 → {s1['team_leads_notified']} notification(s)")
        print(f"   Run 2 → {s2['team_leads_notified']} notification(s), {s2['skipped_duplicates']} skipped")
        print(f"   DB count unchanged: {count_after_first} → {count_after_second}")


# ═══════════════════════════════════════════════════════════════════════
# TEST 5 — Completed Task Is Ignored
# ═══════════════════════════════════════════════════════════════════════
class Test05_CompletedTaskIgnored(CronJobE2ETestCase):

    def test_completed_task_not_flagged(self):
        """A task marked DONE should NOT be flagged overdue even if past its deadline."""
        task = Task(
            title="Book Venue",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.DONE,
            due_date=self.now - timedelta(hours=5),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        self.assertEqual(summary["overdue_tasks_found"], 0)
        self.assertGreater(summary["completed_tasks_ignored"], 0)
        self.assertEqual(self.db.query(Notification).count(), 0)

        print(f"\n✅ TEST 5 PASSED: Completed task correctly ignored")
        print(f"   Completed tasks ignored: {summary['completed_tasks_ignored']}")
        print(f"   Overdue found: {summary['overdue_tasks_found']}")


# ═══════════════════════════════════════════════════════════════════════
# TEST 6 — Deadline Extension Stops Overdue Detection
# ═══════════════════════════════════════════════════════════════════════
class Test06_DeadlineExtension(CronJobE2ETestCase):

    def test_extended_deadline_excludes_task(self):
        """If a deadline is extended into the future, the cron job must NOT flag it as overdue."""
        task = Task(
            title="Finalize Judge Panel",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.IN_PROGRESS,
            due_date=self.now - timedelta(hours=1),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        # Extend deadline into the future
        task.due_date = self.now + timedelta(hours=6)
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        self.assertEqual(summary["overdue_tasks_found"], 0)
        self.assertEqual(summary["team_leads_notified"], 0)
        self.assertEqual(self.db.query(Notification).count(), 0)

        print(f"\n✅ TEST 6 PASSED: Deadline extension correctly excluded task")
        print(f"   Overdue found after extension: {summary['overdue_tasks_found']}")


# ═══════════════════════════════════════════════════════════════════════
# TEST 7 — Hierarchy Resolution for codingarmy123@gmail.com
# ═══════════════════════════════════════════════════════════════════════
class Test07_HierarchyResolution(CronJobE2ETestCase):

    def test_full_hierarchy_chain(self):
        """Verify the full hierarchy chain: Volunteer → Team Lead → Head → Admin."""
        recipients = get_notification_recipients(
            volunteer_id=self.vol.id,
            event_id=self.event.id,
            db=self.db,
        )

        self.assertEqual(recipients.volunteer.email, REFERENCE_EMAIL)
        self.assertEqual(recipients.volunteer.full_name, "CodingArmy Volunteer")
        self.assertEqual(recipients.team_lead.id, self.lead.id)
        self.assertEqual(recipients.head.id, self.head.id)
        self.assertEqual(recipients.admin.id, self.admin.id)

        print(f"\n✅ TEST 7 PASSED: Full hierarchy resolved for {REFERENCE_EMAIL}")
        print(f"   Volunteer: {recipients.volunteer.full_name} ({recipients.volunteer.email})")
        print(f"   Team Lead: {recipients.team_lead.full_name}")
        print(f"   Club Head: {recipients.head.full_name}")
        print(f"   Admin:     {recipients.admin.full_name}")


# ═══════════════════════════════════════════════════════════════════════
# TEST 8 — Admin API Endpoint Trigger
# ═══════════════════════════════════════════════════════════════════════
class Test08_AdminEndpoint(CronJobE2ETestCase):

    def setUp(self):
        super().setUp()
        self.client = TestClient(app)

    def test_admin_trigger_endpoint(self):
        """Admin can trigger the cron job via POST /api/v1/admin/scheduler/check-overdue-tasks."""
        task = Task(
            title="Prepare Judging Criteria",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.TODO,
            due_date=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        def override_get_db():
            yield self.db

        app.dependency_overrides[deps.get_db] = override_get_db
        app.dependency_overrides[deps.get_current_user] = lambda: self.admin

        try:
            response = self.client.post("/api/v1/admin/scheduler/check-overdue-tasks")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
            self.assertIn("summary", data)
            self.assertEqual(data["summary"]["overdue_tasks_found"], 1)
            self.assertEqual(data["summary"]["team_leads_notified"], 1)

            print(f"\n✅ TEST 8 PASSED: Admin endpoint trigger successful")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {data}")
        finally:
            app.dependency_overrides.clear()

    def test_non_admin_gets_403(self):
        """Non-admin (the volunteer codingarmy123@gmail.com) is blocked from triggering the cron job."""
        def override_get_db():
            yield self.db

        app.dependency_overrides[deps.get_db] = override_get_db
        app.dependency_overrides[deps.get_current_user] = lambda: self.vol_user

        try:
            response = self.client.post("/api/v1/admin/scheduler/check-overdue-tasks")
            self.assertEqual(response.status_code, 403)

            print(f"\n✅ TEST 8b PASSED: {REFERENCE_EMAIL} correctly blocked (403)")
            print(f"   Status: {response.status_code}")
        finally:
            app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════
# TEST 9 — Scheduler Status Endpoint
# ═══════════════════════════════════════════════════════════════════════
class Test09_SchedulerStatus(CronJobE2ETestCase):

    def test_scheduler_status_returns_config(self):
        """Scheduler status reports correct configuration values."""
        status = get_scheduler_status()

        self.assertIn("enabled", status)
        self.assertIn("interval_minutes", status)
        self.assertIn("timezone", status)
        self.assertEqual(status["interval_minutes"], 240)
        self.assertEqual(status["timezone"], "Asia/Kolkata")

        print(f"\n✅ TEST 9 PASSED: Scheduler status endpoint verified")
        print(f"   Enabled: {status['enabled']}")
        print(f"   Interval: {status['interval_minutes']} minutes")
        print(f"   Timezone: {status['timezone']}")
        print(f"   Running:  {status['running']}")


# ═══════════════════════════════════════════════════════════════════════
# TEST 10 — Multiple Overdue Tasks for codingarmy123@gmail.com
# ═══════════════════════════════════════════════════════════════════════
class Test10_MultipleOverdueTasks(CronJobE2ETestCase):

    def test_multiple_overdue_tasks_all_detected(self):
        """Multiple overdue tasks for the same volunteer each generate their own notification."""
        tasks = []
        for title in ["Write Unit Tests", "Code Review PR #42", "Fix Memory Leak"]:
            t = Task(
                title=title,
                event_id=self.event.id,
                team_id=self.team.id,
                status=TaskStatus.IN_PROGRESS,
                due_date=self.now - timedelta(hours=1),
            )
            self.db.add(t)
            self.db.flush()
            self.db.add(TaskAssignment(task_id=t.id, volunteer_id=self.vol.id))
            tasks.append(t)
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        self.assertEqual(summary["overdue_tasks_found"], 3)
        self.assertEqual(summary["team_leads_notified"], 3)
        self.assertEqual(summary["errors"], 0)

        notif_count = self.db.query(Notification).filter(
            Notification.recipient_id == self.lead.id,
        ).count()
        self.assertEqual(notif_count, 3)

        print(f"\n✅ TEST 10 PASSED: 3 overdue tasks for {REFERENCE_EMAIL} → 3 notifications")
        print(f"   Summary: {summary}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

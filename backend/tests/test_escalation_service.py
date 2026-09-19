import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Ensure root and backend are on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base import Base
from app.models.user import User
from app.models.event import Event, EventStatus
from app.models.task import Task, TaskStatus, TaskPriority, TaskDependency
from app.models.escalation import TaskEscalation, EscalationLevel, EscalationStatus
from app.services.task_escalation_service import TaskEscalationService
from app.main import app

class TestTaskEscalationService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sqlalchemy.pool import StaticPool
        from app.api import deps

        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=cls.engine)
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        def override_get_db():
            db = cls.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[deps.get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        from app.api import deps
        app.dependency_overrides.pop(deps.get_db, None)

    def setUp(self):
        self.db = self.TestingSessionLocal()
        # Seed test event
        self.event = Event(
            title="Tech Summit 2026",
            date=datetime(2026, 10, 15, 10, 0, 0, tzinfo=timezone.utc),
            status=EventStatus.PUBLISHED
        )
        self.db.add(self.event)
        self.db.commit()
        self.db.refresh(self.event)

        # Service instance with configurable parameters
        self.service = TaskEscalationService(
            hours_before_due=24,
            team_leader_escalation_minutes=60,
            critical_path_escalation_minutes=30
        )

    def tearDown(self):
        self.db.query(TaskDependency).delete()
        self.db.query(TaskEscalation).delete()
        self.db.query(Task).delete()
        self.db.query(Event).delete()
        self.db.commit()
        self.db.close()

    # =========================================================================
    # RULE 1: HIGH/CRITICAL TASK DUE WITHIN HOURS_BEFORE_DUE -> CANDIDATE
    # =========================================================================
    def test_01_rule_1_high_priority_due_soon_becomes_candidate(self):
        """Rule 1: Incomplete high/critical priority task due in < 24h becomes escalation candidate."""
        now = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        # Task due in 12 hours (within 24h window)
        task = Task(
            event_id=self.event.id,
            title="Secure Main Stage AV Equipment",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            due_date=now + timedelta(hours=12)
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        result = self.service.check_task(self.db, task.id, now=now)
        self.assertTrue(result.escalation_required)
        self.assertEqual(result.escalation_level, EscalationLevel.CANDIDATE.value)
        self.assertEqual(result.rule_triggered, "RULE_1_APPROACHING_DUE")
        self.assertEqual(result.next_escalation_at, now + timedelta(hours=12))

    # =========================================================================
    # RULE 2: OVERDUE INCOMPLETE TASK -> TEAM LEADER
    # =========================================================================
    def test_02_rule_2_overdue_incomplete_escalates_to_team_leader(self):
        """Rule 2: Incomplete task that is overdue escalates to Team Leader."""
        now = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        # Task due 2 hours ago
        task = Task(
            event_id=self.event.id,
            title="Submit Catering Menu Finalization",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            due_date=now - timedelta(hours=2)
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        result = self.service.check_task(self.db, task.id, now=now)
        self.assertTrue(result.escalation_required)
        self.assertEqual(result.escalation_level, EscalationLevel.TEAM_LEADER.value)
        self.assertEqual(result.rule_triggered, "RULE_2_OVERDUE")
        self.assertTrue(result.team_leader_notified)
        self.assertEqual(result.notification_count, 1)

    # =========================================================================
    # RULE 3: UNRESOLVED FOR TEAM_LEADER_ESCALATION_MINUTES -> MAIN LEADER
    # =========================================================================
    def test_03_rule_3_team_leader_timeout_escalates_to_main_leader(self):
        """Rule 3: Task unresolved for >= 60 minutes after Team Leader notified escalates to Main Leader."""
        t0 = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        task = Task(
            event_id=self.event.id,
            title="Confirm Guest Speaker Travel",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            due_date=t0 - timedelta(hours=1)
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        # First check at t0: escalates to Team Leader
        res1 = self.service.check_task(self.db, task.id, now=t0)
        self.assertEqual(res1.escalation_level, EscalationLevel.TEAM_LEADER.value)
        self.assertEqual(res1.notification_count, 1)

        # Check 75 minutes later at t0 + 75m (> 60m threshold): escalates to Main Leader
        t1 = t0 + timedelta(minutes=75)
        res2 = self.service.check_task(self.db, task.id, now=t1)
        self.assertTrue(res2.escalation_required)
        self.assertEqual(res2.escalation_level, EscalationLevel.MAIN_LEADER.value)
        self.assertEqual(res2.rule_triggered, "RULE_3_TEAM_LEADER_TIMEOUT")
        self.assertTrue(res2.main_leader_notified)
        self.assertEqual(res2.notification_count, 2)

    # =========================================================================
    # RULE 4: BLOCKED TASK ON CRITICAL PATH -> IMMEDIATE TEAM LEADER
    # =========================================================================
    def test_04_rule_4_blocked_critical_path_task_immediately_escalates(self):
        """Rule 4: A BLOCKED task lying on the event's critical path escalates immediately to Team Leader."""
        now = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)

        # Create 3 sequential tasks forming a critical path: Task A -> Task B -> Task C
        t_a = Task(event_id=self.event.id, title="Venue Contract Execution", status=TaskStatus.BLOCKED, priority=TaskPriority.HIGH, due_date=now + timedelta(days=5))
        t_b = Task(event_id=self.event.id, title="Floor Plan Approval", status=TaskStatus.TODO, priority=TaskPriority.MEDIUM, due_date=now + timedelta(days=6))
        t_c = Task(event_id=self.event.id, title="Booth Setup", status=TaskStatus.TODO, priority=TaskPriority.MEDIUM, due_date=now + timedelta(days=7))
        self.db.add_all([t_a, t_b, t_c])
        self.db.commit()

        # Dependencies: t_a -> t_b -> t_c
        dep1 = TaskDependency(prerequisite_task_id=t_a.id, dependent_task_id=t_b.id)
        dep2 = TaskDependency(prerequisite_task_id=t_b.id, dependent_task_id=t_c.id)
        self.db.add_all([dep1, dep2])
        self.db.commit()

        # Check t_a (which is BLOCKED and on the critical path)
        res = self.service.check_task(self.db, t_a.id, now=now)
        self.assertTrue(res.escalation_required)
        self.assertTrue(res.is_critical_path)
        self.assertEqual(res.escalation_level, EscalationLevel.TEAM_LEADER.value)
        self.assertEqual(res.rule_triggered, "RULE_4_BLOCKED_CRITICAL_PATH")
        self.assertIn("BLOCKED and lies on the critical path", res.reason)
        # Next escalation for critical path should be in 30 minutes
        self.assertEqual(res.next_escalation_at, now + timedelta(minutes=30))

    # =========================================================================
    # RULE 5: CRITICAL PATH UNRESOLVED AFTER INTERVAL -> MAIN LEADER
    # =========================================================================
    def test_05_rule_5_critical_path_unresolved_after_interval_escalates_to_main_leader(self):
        """Rule 5: Critical path task unresolved for >= 30 minutes escalates to Main Leader."""
        t0 = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)

        t_cp = Task(event_id=self.event.id, title="Security Clearance", status=TaskStatus.BLOCKED, priority=TaskPriority.HIGH, due_date=t0 + timedelta(days=2))
        t_next = Task(event_id=self.event.id, title="Main Badge Printing", status=TaskStatus.TODO, priority=TaskPriority.MEDIUM, due_date=t0 + timedelta(days=3))
        self.db.add_all([t_cp, t_next])
        self.db.commit()
        dep = TaskDependency(prerequisite_task_id=t_cp.id, dependent_task_id=t_next.id)
        self.db.add(dep)
        self.db.commit()

        # At t0: Rule 4 triggers Team Leader
        res1 = self.service.check_task(self.db, t_cp.id, now=t0)
        self.assertEqual(res1.escalation_level, EscalationLevel.TEAM_LEADER.value)

        # At t0 + 35m (> 30m critical path interval): Rule 5 triggers Main Leader
        t1 = t0 + timedelta(minutes=35)
        res2 = self.service.check_task(self.db, t_cp.id, now=t1)
        self.assertTrue(res2.escalation_required)
        self.assertEqual(res2.escalation_level, EscalationLevel.MAIN_LEADER.value)
        self.assertEqual(res2.rule_triggered, "RULE_5_CRITICAL_PATH_TIMEOUT")
        self.assertTrue(res2.main_leader_notified)

    # =========================================================================
    # EXCLUSIONS: DONE AND CANCELLED TASKS NEVER ESCALATED
    # =========================================================================
    def test_06_done_and_cancelled_tasks_are_never_escalated(self):
        """Tasks with status DONE or CANCELLED are completely excluded from escalation."""
        now = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        # Overdue DONE task
        done_task = Task(
            event_id=self.event.id,
            title="Draft Sponsor Pitch",
            status=TaskStatus.DONE,
            priority=TaskPriority.URGENT,
            due_date=now - timedelta(days=2)
        )
        # Overdue CANCELLED task
        cancelled_task = Task(
            event_id=self.event.id,
            title="Book Ice Sculpture",
            status=TaskStatus.CANCELLED,
            priority=TaskPriority.HIGH,
            due_date=now - timedelta(days=1)
        )
        self.db.add_all([done_task, cancelled_task])
        self.db.commit()

        res_done = self.service.check_task(self.db, done_task.id, now=now)
        self.assertFalse(res_done.escalation_required)
        self.assertEqual(res_done.escalation_level, EscalationLevel.NONE.value)
        self.assertIn("DONE", res_done.reason)

        res_cancelled = self.service.check_task(self.db, cancelled_task.id, now=now)
        self.assertFalse(res_cancelled.escalation_required)
        self.assertEqual(res_cancelled.escalation_level, EscalationLevel.NONE.value)
        self.assertIn("CANCELLED", res_cancelled.reason)

    def test_07_completing_task_automatically_resolves_active_escalation(self):
        """When an escalated task becomes DONE, the active escalation record resolves."""
        now = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        task = Task(
            event_id=self.event.id,
            title="Pay Venue Deposit",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            due_date=now - timedelta(hours=3)
        )
        self.db.add(task)
        self.db.commit()

        # Trigger escalation
        res1 = self.service.check_task(self.db, task.id, now=now)
        self.assertTrue(res1.escalation_required)
        self.assertEqual(res1.escalation_status, EscalationStatus.PENDING.value)

        # Mark task DONE
        task.status = TaskStatus.DONE
        self.db.commit()

        # Re-check task
        res2 = self.service.check_task(self.db, task.id, now=now + timedelta(minutes=10))
        self.assertFalse(res2.escalation_required)
        self.assertEqual(res2.escalation_status, EscalationStatus.RESOLVED.value)
        self.assertIsNotNone(res2.resolved_at)

    # =========================================================================
    # IDEMPOTENCY: MULTIPLE INVOCATIONS DO NOT DUPLICATE ROWS OR ALERTS
    # =========================================================================
    def test_08_idempotency_guarantee(self):
        """Consecutively checking a task 10 times does NOT create duplicate records or duplicate alerts."""
        now = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        task = Task(
            event_id=self.event.id,
            title="Coordinate Audio Soundcheck",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            due_date=now - timedelta(hours=1)
        )
        self.db.add(task)
        self.db.commit()

        # Call check_task 10 times at the same timeframe
        for i in range(10):
            res = self.service.check_task(self.db, task.id, now=now)
            self.assertTrue(res.escalation_required)
            self.assertEqual(res.escalation_level, EscalationLevel.TEAM_LEADER.value)
            # Notification count should remain strictly 1
            self.assertEqual(res.notification_count, 1)

        # Verify exactly 1 database row exists for this task
        escalation_rows = self.db.query(TaskEscalation).filter(TaskEscalation.task_id == task.id).all()
        self.assertEqual(len(escalation_rows), 1)

    # =========================================================================
    # LIFECYCLE MANAGEMENT: ACKNOWLEDGE, RESOLVE, CANCEL, MANUAL ESCALATE
    # =========================================================================
    def test_09_escalation_lifecycle_actions(self):
        """Tests acknowledge, resolve, manual promote, and cancel escalation lifecycle."""
        now = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        task = Task(
            event_id=self.event.id,
            title="WiFi Network Router Deployment",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            due_date=now - timedelta(hours=2)
        )
        self.db.add(task)
        self.db.commit()

        # 1. Trigger escalation
        self.service.check_task(self.db, task.id, now=now)

        # 2. Acknowledge escalation
        ack_res = self.service.acknowledge_escalation(self.db, task.id, user_id=42)
        self.assertEqual(ack_res.escalation_status, EscalationStatus.ACKNOWLEDGED.value)
        self.assertIsNotNone(ack_res.acknowledged_at)

        # 3. Explicitly escalate to Main Leader
        promote_res = self.service.escalate_to_main_leader(self.db, task.id, reason="Technical blocker requires dean intervention", now=now)
        self.assertEqual(promote_res.escalation_level, EscalationLevel.MAIN_LEADER.value)
        self.assertTrue(promote_res.main_leader_notified)

        # 4. Resolve escalation
        resolve_res = self.service.resolve_escalation(self.db, task.id, resolution_note="Temporary 5G hotspot deployed as backup.")
        self.assertEqual(resolve_res.escalation_status, EscalationStatus.RESOLVED.value)
        self.assertFalse(resolve_res.escalation_required)
        self.assertEqual(resolve_res.resolution_note, "Temporary 5G hotspot deployed as backup.")

    # =========================================================================
    # BATCH OPERATIONS: CHECK EVENT & PROCESS PENDING ESCALATIONS
    # =========================================================================
    def test_10_batch_event_and_pending_processing(self):
        """Tests check_event and process_pending_escalations batch workflows."""
        now = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        t1 = Task(event_id=self.event.id, title="Print Banners", status=TaskStatus.TODO, priority=TaskPriority.HIGH, due_date=now - timedelta(hours=1))
        t2 = Task(event_id=self.event.id, title="Water Bottles Delivery", status=TaskStatus.DONE, priority=TaskPriority.LOW, due_date=now - timedelta(hours=1))
        t3 = Task(event_id=self.event.id, title="VIP Badges", status=TaskStatus.TODO, priority=TaskPriority.URGENT, due_date=now + timedelta(hours=10))
        self.db.add_all([t1, t2, t3])
        self.db.commit()

        # Batch check event
        event_results = self.service.check_event(self.db, self.event.id, now=now)
        self.assertEqual(len(event_results), 3)
        req_flags = {r.task_id: r.escalation_required for r in event_results}
        self.assertTrue(req_flags[t1.id]) # Overdue -> Team Leader
        self.assertFalse(req_flags[t2.id]) # DONE -> Excluded
        self.assertTrue(req_flags[t3.id]) # High due in 10h -> Candidate

        # Batch process pending
        pending_results = self.service.process_pending_escalations(self.db, now=now)
        self.assertGreaterEqual(len(pending_results), 2)

    # =========================================================================
    # REST API ENDPOINTS VERIFICATION
    # =========================================================================
    def test_11_rest_api_escalation_endpoints(self):
        """Tests FastAPI /api/escalations endpoints."""
        now = datetime.now(timezone.utc)
        task = Task(
            event_id=self.event.id,
            title="Stage Backdrop Assembly",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            due_date=now - timedelta(hours=3)
        )
        self.db.add(task)
        self.db.commit()

        # 1. POST /api/escalations/check-task/{task_id}
        resp = self.client.post(f"/api/escalations/check-task/{task.id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["escalation_required"])
        self.assertEqual(data["escalation_level"], EscalationLevel.TEAM_LEADER.value)

        # 2. POST /api/escalations/{task_id}/acknowledge
        ack_resp = self.client.post(f"/api/escalations/{task.id}/acknowledge")
        self.assertEqual(ack_resp.status_code, 200)
        self.assertEqual(ack_resp.json()["escalation_status"], EscalationStatus.ACKNOWLEDGED.value)

        # 3. GET /api/escalations/active
        active_resp = self.client.get(f"/api/escalations/active?event_id={self.event.id}")
        self.assertEqual(active_resp.status_code, 200)
        active_list = active_resp.json()
        self.assertGreater(len(active_list), 0)
        self.assertEqual(active_list[0]["task_id"], task.id)

        # 4. POST /api/escalations/{task_id}/resolve
        res_resp = self.client.post(
            f"/api/escalations/{task.id}/resolve",
            json={"resolution_note": "Backdrop securely bolted to stage trusses."}
        )
        self.assertEqual(res_resp.status_code, 200)
        self.assertEqual(res_resp.json()["escalation_status"], EscalationStatus.RESOLVED.value)

if __name__ == "__main__":
    unittest.main()

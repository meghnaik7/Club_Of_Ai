import unittest
from datetime import timedelta
from tests.scheduler.test_base import BaseSchedulerTestCase
from app.models.task import Task, TaskStatus, TaskAssignment
from app.models.notification import Notification
from app.scheduler.jobs import check_overdue_volunteer_tasks


class TestOverdueTaskDetection(BaseSchedulerTestCase):
    def test_overdue_task_detected(self):
        """Active incomplete task past its deadline must be detected and notified."""
        task = Task(
            title="Prepare Registration Desk",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.IN_PROGRESS,
            due_date=self.now - timedelta(hours=1),
        )
        self.db.add(task)
        self.db.flush()

        assignment = TaskAssignment(task_id=task.id, volunteer_id=self.vol.id)
        self.db.add(assignment)
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        self.assertEqual(summary["overdue_tasks_found"], 1)
        self.assertEqual(summary["team_leads_notified"], 1)

        # Verify notification created in database
        notif = self.db.query(Notification).filter(Notification.task_id == task.id).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.recipient_id, self.lead.id)
        self.assertEqual(notif.notification_type, "TASK_OVERDUE")
        self.assertEqual(notif.escalation_level, "TEAM_LEAD")
        self.assertIn("Rahul Patel", notif.message)
        self.assertIn("Prepare Registration Desk", notif.message)

    def test_future_task_ignored(self):
        """Task whose deadline is in the future must NOT be flagged as overdue."""
        task = Task(
            title="Post Event Cleanup",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.TODO,
            due_date=self.now + timedelta(hours=2),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)
        self.assertEqual(summary["overdue_tasks_found"], 0)
        self.assertEqual(summary["team_leads_notified"], 0)

        notif_count = self.db.query(Notification).count()
        self.assertEqual(notif_count, 0)

    def test_cancelled_task_ignored(self):
        """Cancelled tasks must be ignored even if deadline has passed."""
        task = Task(
            title="Cancelled Task",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.CANCELLED,
            due_date=self.now - timedelta(hours=3),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)
        self.assertEqual(summary["overdue_tasks_found"], 0)


if __name__ == "__main__":
    unittest.main()

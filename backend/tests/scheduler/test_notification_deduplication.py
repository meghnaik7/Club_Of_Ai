import unittest
from datetime import timedelta
from tests.scheduler.test_base import BaseSchedulerTestCase
from app.models.task import Task, TaskStatus, TaskAssignment
from app.models.notification import Notification, EscalationLevelRole, NotificationType
from app.scheduler.jobs import check_overdue_volunteer_tasks


class TestNotificationDeduplication(BaseSchedulerTestCase):
    def test_cron_runs_twice_no_duplicate_notifications(self):
        """
        Running the cron job multiple times for the same overdue task must NOT create
        duplicate notifications for the same recipient and level.
        """
        task = Task(
            title="Coordinate Guest Speaker",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.IN_PROGRESS,
            due_date=self.now - timedelta(minutes=45),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        # Run 1
        summary_1 = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)
        self.assertEqual(summary_1["team_leads_notified"], 1)
        self.assertEqual(summary_1["skipped_duplicates"], 0)

        # Count records
        notifs_count_1 = self.db.query(Notification).filter(Notification.task_id == task.id).count()
        self.assertEqual(notifs_count_1, 1)

        # Run 2 (e.g. 4 hours later, task still incomplete at Level 1)
        summary_2 = check_overdue_volunteer_tasks(db=self.db, current_time=self.now + timedelta(minutes=10))
        self.assertEqual(summary_2["team_leads_notified"], 0)
        self.assertGreaterEqual(summary_2["skipped_duplicates"], 1)

        # Count records must still be exactly 1
        notifs_count_2 = self.db.query(Notification).filter(Notification.task_id == task.id).count()
        self.assertEqual(notifs_count_2, 1)

    def test_cron_runs_ten_times_strictly_idempotent(self):
        """Repeatedly running cron 10 times creates exactly 1 Team Lead and 1 Head notification."""
        task = Task(
            title="Security Check",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.TODO,
            due_date=self.now - timedelta(hours=2),  # > 60 mins overdue
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        # Run 10 times consecutively
        for i in range(10):
            check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        lead_notifs = self.db.query(Notification).filter(
            Notification.task_id == task.id,
            Notification.escalation_level == EscalationLevelRole.TEAM_LEAD.value,
        ).count()
        self.assertEqual(lead_notifs, 1)

        head_notifs = self.db.query(Notification).filter(
            Notification.task_id == task.id,
            Notification.escalation_level == EscalationLevelRole.HEAD.value,
        ).count()
        self.assertEqual(head_notifs, 1)


if __name__ == "__main__":
    unittest.main()

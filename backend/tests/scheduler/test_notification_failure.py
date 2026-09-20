import unittest
from datetime import timedelta
from unittest.mock import patch
from tests.scheduler.test_base import BaseSchedulerTestCase
from app.models.task import Task, TaskStatus, TaskAssignment
from app.models.notification import Notification
from app.scheduler.jobs import check_overdue_volunteer_tasks
from app.services.notification_service import NotificationService


class TestNotificationFailure(BaseSchedulerTestCase):
    def test_one_task_failure_does_not_stop_cron_job(self):
        """
        When notification for Task 1 encounters a database error,
        the transaction is rolled back and Task 2 is still successfully processed.
        """
        task1 = Task(
            title="Faulty Task",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.IN_PROGRESS,
            due_date=self.now - timedelta(hours=1),
        )
        task2 = Task(
            title="Healthy Task",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.IN_PROGRESS,
            due_date=self.now - timedelta(hours=1),
        )
        self.db.add_all([task1, task2])
        self.db.flush()

        self.db.add_all([
            TaskAssignment(task_id=task1.id, volunteer_id=self.vol.id),
            TaskAssignment(task_id=task2.id, volunteer_id=self.vol.id),
        ])
        self.db.commit()

        # Simulate exception when sending notification specifically for task1
        original_send = NotificationService.send_in_app_notification

        def side_effect(db, recipient_id, task_id, *args, **kwargs):
            if task_id == task1.id:
                raise RuntimeError("Simulated transient database error on task1")
            return original_send(db, recipient_id, task_id, *args, **kwargs)

        with patch.object(NotificationService, "send_in_app_notification", side_effect=side_effect):
            summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        # Task 1 errored, Task 2 succeeded
        self.assertEqual(summary["errors"], 1)
        self.assertEqual(summary["team_leads_notified"], 1)

        # Confirm Task 2 notification exists in DB
        task2_notif = self.db.query(Notification).filter(Notification.task_id == task2.id).first()
        self.assertIsNotNone(task2_notif)


if __name__ == "__main__":
    unittest.main()

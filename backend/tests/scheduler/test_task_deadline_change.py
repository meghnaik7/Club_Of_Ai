import unittest
from datetime import timedelta
from tests.scheduler.test_base import BaseSchedulerTestCase
from app.models.task import Task, TaskStatus, TaskAssignment
from app.models.notification import Notification
from app.scheduler.jobs import check_overdue_volunteer_tasks


class TestTaskDeadlineChange(BaseSchedulerTestCase):
    def test_deadline_extension_stops_overdue_detection(self):
        """When deadline is extended to the future, the job re-evaluates database deadline and excludes it."""
        # Originally overdue task
        task = Task(
            title="Book Seminar Hall",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.IN_PROGRESS,
            due_date=self.now - timedelta(hours=1),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        # Update deadline into future (e.g. extension granted)
        task.due_date = self.now + timedelta(hours=3)
        self.db.commit()

        # Run cron
        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        self.assertEqual(summary["overdue_tasks_found"], 0)
        self.assertEqual(summary["team_leads_notified"], 0)

        notif_count = self.db.query(Notification).filter(Notification.task_id == task.id).count()
        self.assertEqual(notif_count, 0)


if __name__ == "__main__":
    unittest.main()

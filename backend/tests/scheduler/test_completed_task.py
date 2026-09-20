import unittest
from datetime import timedelta
from tests.scheduler.test_base import BaseSchedulerTestCase
from app.models.task import Task, TaskStatus, TaskAssignment
from app.models.notification import Notification
from app.scheduler.jobs import check_overdue_volunteer_tasks


class TestCompletedTask(BaseSchedulerTestCase):
    def test_completed_task_no_notification(self):
        """Completed task (status = DONE) must not generate notifications even if past due."""
        task = Task(
            title="Design Event Poster",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.DONE,
            due_date=self.now - timedelta(hours=3),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        self.assertEqual(summary["overdue_tasks_found"], 0)
        self.assertEqual(summary["completed_tasks_ignored"], 1)
        self.assertEqual(summary["team_leads_notified"], 0)
        self.assertEqual(summary["heads_notified"], 0)

        notif_count = self.db.query(Notification).filter(Notification.task_id == task.id).count()
        self.assertEqual(notif_count, 0)

    def test_task_marked_done_stops_notifications(self):
        """Task that was overdue and then marked DONE must stop generating further notifications."""
        task = Task(
            title="Print Badges",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.IN_PROGRESS,
            due_date=self.now - timedelta(minutes=30),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        # First run: Team Lead is notified
        check_overdue_volunteer_tasks(db=self.db, current_time=self.now)
        self.assertEqual(
            self.db.query(Notification).filter(Notification.task_id == task.id).count(), 1
        )

        # Volunteer completes the task
        task.status = TaskStatus.DONE
        self.db.commit()

        # Subsequent run 2 hours later (beyond escalation threshold)
        summary = check_overdue_volunteer_tasks(
            db=self.db, current_time=self.now + timedelta(hours=2)
        )
        self.assertEqual(summary["overdue_tasks_found"], 0)
        self.assertEqual(summary["heads_notified"], 0)

        # Head was never notified because task was marked DONE
        head_notifs = self.db.query(Notification).filter(
            Notification.task_id == task.id,
            Notification.escalation_level == "HEAD",
        ).count()
        self.assertEqual(head_notifs, 0)


if __name__ == "__main__":
    unittest.main()

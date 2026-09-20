import unittest
from datetime import timedelta
from tests.scheduler.test_base import BaseSchedulerTestCase
from app.models.task import Task, TaskStatus, TaskAssignment
from app.models.notification import Notification, EscalationLevelRole, NotificationType
from app.scheduler.jobs import check_overdue_volunteer_tasks


class TestEscalation(BaseSchedulerTestCase):
    def test_escalation_threshold_not_reached(self):
        """When task is overdue by less than 60 minutes, Head is NOT notified."""
        task = Task(
            title="Arrange Stage Decorations",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.IN_PROGRESS,
            due_date=self.now - timedelta(minutes=25),  # 25 mins overdue < 60 mins
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        self.assertEqual(summary["team_leads_notified"], 1)
        self.assertEqual(summary["heads_notified"], 0)

        # Confirm no HEAD notification exists
        head_notif = self.db.query(Notification).filter(
            Notification.task_id == task.id,
            Notification.escalation_level == EscalationLevelRole.HEAD.value,
        ).first()
        self.assertIsNone(head_notif)

    def test_escalation_threshold_reached(self):
        """When task remains overdue for >= 60 minutes, it escalates to Head."""
        task = Task(
            title="Arrange Stage Decorations",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.IN_PROGRESS,
            due_date=self.now - timedelta(minutes=90),  # 90 mins overdue >= 60 mins
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        self.assertEqual(summary["team_leads_notified"], 1)
        self.assertEqual(summary["heads_notified"], 1)

        # Verify Head notification
        head_notif = self.db.query(Notification).filter(
            Notification.task_id == task.id,
            Notification.escalation_level == EscalationLevelRole.HEAD.value,
        ).first()
        self.assertIsNotNone(head_notif)
        self.assertEqual(head_notif.recipient_id, self.head.id)
        self.assertEqual(head_notif.notification_type, NotificationType.TASK_OVERDUE_ESCALATION.value)
        self.assertIn("🚨 Escalated Overdue Task", head_notif.title)
        self.assertIn("Dr. Sarah Head", self.head.full_name)
        self.assertIn("Priya Shah", head_notif.message)


if __name__ == "__main__":
    unittest.main()

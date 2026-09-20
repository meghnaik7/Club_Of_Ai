import unittest
from datetime import timedelta
from tests.scheduler.test_base import BaseSchedulerTestCase
from app.models.task import Task, TaskStatus, TaskAssignment
from app.models.notification import Notification, EscalationLevelRole, NotificationType
from app.scheduler.jobs import check_overdue_volunteer_tasks
from app.services.hierarchy_service import get_notification_recipients


class TestHierarchyNotification(BaseSchedulerTestCase):
    def test_volunteer_to_team_lead_notification(self):
        """When a volunteer task becomes overdue, the Team Lead receives Level 1 notification."""
        task = Task(
            title="Setup Audio System",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.TODO,
            due_date=self.now - timedelta(minutes=30),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        # Check hierarchy resolution directly
        recipients = get_notification_recipients(self.vol.id, self.event.id, self.db)
        self.assertEqual(recipients.volunteer.id, self.vol_user.id)
        self.assertEqual(recipients.team_lead.id, self.lead.id)
        self.assertEqual(recipients.head.id, self.head.id)
        self.assertEqual(recipients.admin.id, self.admin.id)

        # Execute cron
        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)
        self.assertEqual(summary["team_leads_notified"], 1)
        self.assertEqual(summary["heads_notified"], 0)

        notif = self.db.query(Notification).filter(Notification.task_id == task.id).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.recipient_id, self.lead.id)
        self.assertEqual(notif.notification_type, NotificationType.TASK_OVERDUE.value)
        self.assertEqual(notif.escalation_level, EscalationLevelRole.TEAM_LEAD.value)
        self.assertIn("Priya Shah", self.lead.full_name)
        self.assertIn("Rahul Patel", notif.message)
        self.assertIn("Setup Audio System", notif.message)
        self.assertIn("TechFest 2026", notif.message)


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import timedelta
from tests.scheduler.test_base import BaseSchedulerTestCase
from app.models.user import User, UserRole
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.task import Task, TaskStatus, TaskAssignment
from app.models.notification import Notification, EscalationLevelRole
from app.scheduler.jobs import check_overdue_volunteer_tasks


class TestMissingHead(BaseSchedulerTestCase):
    def test_missing_team_lead_and_missing_head_falls_back_to_admin(self):
        """When neither Team Lead nor Head exists, notification falls back to System Admin."""
        # Deactivate lead and head
        self.lead.is_active = False
        self.head.is_active = False
        self.db.commit()

        task = Task(
            title="Unsupervised Campus Permission",
            event_id=self.event.id,
            team_id=None,
            status=TaskStatus.TODO,
            due_date=self.now - timedelta(minutes=45),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        # Admin must be notified as fallback
        self.assertEqual(summary["admins_notified"], 1)

        admin_notif = self.db.query(Notification).filter(
            Notification.task_id == task.id,
            Notification.recipient_id == self.admin.id,
        ).first()
        self.assertIsNotNone(admin_notif)
        self.assertEqual(admin_notif.escalation_level, EscalationLevelRole.ADMIN.value)


if __name__ == "__main__":
    unittest.main()

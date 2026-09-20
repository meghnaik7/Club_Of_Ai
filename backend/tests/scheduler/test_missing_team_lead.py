import unittest
from datetime import timedelta
from tests.scheduler.test_base import BaseSchedulerTestCase
from app.models.user import User, UserRole
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.task import Task, TaskStatus, TaskAssignment
from app.models.notification import Notification, EscalationLevelRole
from app.scheduler.jobs import check_overdue_volunteer_tasks


class TestMissingTeamLead(BaseSchedulerTestCase):
    def test_volunteer_without_subteam_notifies_head_directly(self):
        """When a volunteer belongs directly to the club with no Team Lead, Head is notified directly."""
        direct_vol_user = User(
            email="direct_vol@test.org",
            full_name="Direct Club Volunteer",
            hashed_password="pw",
            role=UserRole.VOLUNTEER,
            club_id=self.club.id,
            subteam_id=None,  # No subteam
            is_active=True,
        )
        self.db.add(direct_vol_user)
        self.db.flush()

        direct_vol = Volunteer(
            user_id=direct_vol_user.id,
            club_id=self.club.id,
            subteam_id=None,
            status=VolunteerStatus.ACTIVE,
        )
        self.db.add(direct_vol)
        self.db.flush()

        task = Task(
            title="General Volunteer Coordination",
            event_id=self.event.id,
            team_id=None,
            status=TaskStatus.IN_PROGRESS,
            due_date=self.now - timedelta(minutes=20),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=direct_vol.id))
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        # Team lead does not exist, so Head must be notified directly
        self.assertEqual(summary["team_leads_notified"], 0)
        self.assertEqual(summary["heads_notified"], 1)

        head_notif = self.db.query(Notification).filter(
            Notification.task_id == task.id,
            Notification.recipient_id == self.head.id,
        ).first()
        self.assertIsNotNone(head_notif)
        self.assertEqual(head_notif.escalation_level, EscalationLevelRole.HEAD.value)

    def test_inactive_team_lead_escalates_to_head(self):
        """When Team Lead is marked is_active=False, notification escalates directly to Head."""
        # Deactivate team lead
        self.lead.is_active = False
        self.db.commit()

        task = Task(
            title="Setup Soundcheck",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.IN_PROGRESS,
            due_date=self.now - timedelta(minutes=25),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        # Inactive lead should not receive notification; Head is notified
        self.assertEqual(summary["team_leads_notified"], 0)
        self.assertEqual(summary["heads_notified"], 1)

        lead_notif = self.db.query(Notification).filter(
            Notification.task_id == task.id,
            Notification.recipient_id == self.lead.id,
        ).first()
        self.assertIsNone(lead_notif)

        head_notif = self.db.query(Notification).filter(
            Notification.task_id == task.id,
            Notification.recipient_id == self.head.id,
        ).first()
        self.assertIsNotNone(head_notif)


if __name__ == "__main__":
    unittest.main()

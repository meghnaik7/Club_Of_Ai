import unittest
from datetime import timedelta
from tests.scheduler.test_base import BaseSchedulerTestCase
from app.models.user import User, UserRole
from app.models.team import Team, TeamMembership, TeamRole
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.task import Task, TaskStatus, TaskAssignment
from app.models.notification import Notification, EscalationLevelRole
from app.scheduler.jobs import check_overdue_volunteer_tasks


class TestMultipleVolunteers(BaseSchedulerTestCase):
    def test_multiple_volunteers_same_team_single_lead_notification(self):
        """
        When a task has multiple volunteers under the SAME Team Lead,
        the Team Lead receives exactly ONE notification for that task (no duplicates).
        """
        # Add a second volunteer to the same team
        vol2_user = User(
            email="volunteer2@test.org",
            full_name="Ananya Sharma",
            hashed_password="pw",
            role=UserRole.VOLUNTEER,
            club_id=self.club.id,
            subteam_id=self.team.id,
            is_active=True,
        )
        self.db.add(vol2_user)
        self.db.flush()

        vol2 = Volunteer(
            user_id=vol2_user.id,
            club_id=self.club.id,
            subteam_id=self.team.id,
            status=VolunteerStatus.ACTIVE,
        )
        self.db.add(vol2)
        self.db.flush()

        task = Task(
            title="Sponsorship Outreach",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.IN_PROGRESS,
            due_date=self.now - timedelta(minutes=40),
        )
        self.db.add(task)
        self.db.flush()

        self.db.add_all([
            TaskAssignment(task_id=task.id, volunteer_id=self.vol.id),
            TaskAssignment(task_id=task.id, volunteer_id=vol2.id),
        ])
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        # Team Lead should be notified exactly once
        self.assertEqual(summary["team_leads_notified"], 1)

        lead_notifs = self.db.query(Notification).filter(
            Notification.task_id == task.id,
            Notification.recipient_id == self.lead.id,
            Notification.escalation_level == EscalationLevelRole.TEAM_LEAD.value,
        ).all()
        self.assertEqual(len(lead_notifs), 1)

    def test_multiple_volunteers_different_teams_both_leads_notified(self):
        """
        When a cross-functional task has volunteers from two different teams,
        both Team Leads are notified without conflict.
        """
        # Create second team & lead
        team2 = Team(name="Design Team", club_id=self.club.id)
        self.db.add(team2)
        self.db.flush()

        lead2 = User(
            email="lead2@test.org",
            full_name="Karan Verma",
            hashed_password="pw",
            role=UserRole.SUBTEAM_LEAD,
            club_id=self.club.id,
            subteam_id=team2.id,
            is_active=True,
        )
        self.db.add(lead2)
        self.db.flush()
        team2.lead_id = lead2.id

        vol2_user = User(
            email="vol2_design@test.org",
            full_name="Meera Joshi",
            hashed_password="pw",
            role=UserRole.VOLUNTEER,
            club_id=self.club.id,
            subteam_id=team2.id,
            is_active=True,
        )
        self.db.add(vol2_user)
        self.db.flush()

        vol2 = Volunteer(
            user_id=vol2_user.id,
            club_id=self.club.id,
            subteam_id=team2.id,
            status=VolunteerStatus.ACTIVE,
        )
        self.db.add(vol2)
        self.db.flush()

        task = Task(
            title="Produce Event Teaser Video",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.IN_PROGRESS,
            due_date=self.now - timedelta(minutes=45),
        )
        self.db.add(task)
        self.db.flush()

        self.db.add_all([
            TaskAssignment(task_id=task.id, volunteer_id=self.vol.id),  # Logistics team
            TaskAssignment(task_id=task.id, volunteer_id=vol2.id),      # Design team
        ])
        self.db.commit()

        summary = check_overdue_volunteer_tasks(db=self.db, current_time=self.now)

        # Both team leads should be notified
        self.assertEqual(summary["team_leads_notified"], 2)

        lead1_notif = self.db.query(Notification).filter(
            Notification.task_id == task.id,
            Notification.recipient_id == self.lead.id,
        ).first()
        self.assertIsNotNone(lead1_notif)

        lead2_notif = self.db.query(Notification).filter(
            Notification.task_id == task.id,
            Notification.recipient_id == lead2.id,
        ).first()
        self.assertIsNotNone(lead2_notif)


if __name__ == "__main__":
    unittest.main()

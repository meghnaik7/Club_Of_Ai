import unittest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base_class import Base
import app.db.base  # Ensures all models including Notification are registered
from app.models.user import User, UserRole
from app.models.team import Club, Team, TeamMembership, ClubMembership, TeamRole, ClubRole
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.event import Event, EventStatus
from app.models.task import Task, TaskStatus, TaskPriority, TaskAssignment
from app.models.notification import Notification


class BaseSchedulerTestCase(unittest.TestCase):
    """Base test case initializing clean in-memory SQLite database and common hierarchy fixtures."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)

        # 1. System Admin
        self.admin = User(
            email="admin@test.org",
            full_name="Global Admin",
            hashed_password="pw",
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.db.add(self.admin)

        # 2. Club & Club Head
        self.club = Club(name="AI Club", description="AI and Machine Learning Club")
        self.db.add(self.club)
        self.db.flush()

        self.head = User(
            email="head@test.org",
            full_name="Dr. Sarah Head",
            hashed_password="pw",
            role=UserRole.CLUB_HEAD,
            club_id=self.club.id,
            is_active=True,
        )
        self.db.add(self.head)
        self.db.flush()

        self.club_membership = ClubMembership(
            user_id=self.head.id,
            club_id=self.club.id,
            role=ClubRole.CLUB_HEAD,
            is_active=True,
        )
        self.db.add(self.club_membership)

        # 3. SubTeam & Team Lead
        self.team = Team(name="Logistics Team", club_id=self.club.id)
        self.db.add(self.team)
        self.db.flush()

        self.lead = User(
            email="lead@test.org",
            full_name="Priya Shah",
            hashed_password="pw",
            role=UserRole.SUBTEAM_LEAD,
            club_id=self.club.id,
            subteam_id=self.team.id,
            is_active=True,
        )
        self.db.add(self.lead)
        self.db.flush()

        self.team.lead_id = self.lead.id
        self.team_membership = TeamMembership(
            user_id=self.lead.id,
            team_id=self.team.id,
            role=TeamRole.SUBTEAM_LEAD,
            is_active=True,
        )
        self.db.add(self.team_membership)

        # 4. Volunteer User & Volunteer Profile
        self.vol_user = User(
            email="rahul@test.org",
            full_name="Rahul Patel",
            hashed_password="pw",
            role=UserRole.VOLUNTEER,
            club_id=self.club.id,
            subteam_id=self.team.id,
            is_active=True,
        )
        self.db.add(self.vol_user)
        self.db.flush()

        self.vol = Volunteer(
            user_id=self.vol_user.id,
            club_id=self.club.id,
            subteam_id=self.team.id,
            status=VolunteerStatus.ACTIVE,
        )
        self.db.add(self.vol)

        # 5. Event
        self.event = Event(
            title="TechFest 2026",
            club_id=self.club.id,
            date=self.now + timedelta(days=5),
            status=EventStatus.PUBLISHED,
            created_by=self.head.id,
        )
        self.db.add(self.event)
        self.db.commit()

    def tearDown(self):
        self.db.close()

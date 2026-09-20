import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.db.base_class import Base
from app.api import deps
from app.core.security import create_access_token
from app.models.user import User, UserRole
from app.models.team import Club, Team, TeamMembership, TeamRole, EventMembership, EventRole
from app.models.event import Event, EventStatus, Expense, EventBudgetCategory
from app.models.task import Task, TaskStatus, TaskPriority, TaskAssignment, TaskDependency, TaskComment
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.risk import EventRisk
from app.models.meeting import Meeting, MeetingActionItem
from app.models.escalation import TaskEscalation, EscalationLevel, EscalationStatus
from app.models.announcement import Announcement
from app.models.chat_history import RAGChatHistory
from app.models.document import PastLesson
from sqlalchemy.pool import StaticPool
from app.core.permissions import seed_permissions
from app.services.authz import AuthorizationService


class TestEventVolunteerDeletionAndDatetime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

        db = cls.TestingSessionLocal()
        seed_permissions(db)

        # 1. Create Clubs
        cls.club1 = Club(name="AI Robotics Club")
        cls.club2 = Club(name="Design Club")
        db.add_all([cls.club1, cls.club2])
        db.flush()

        # 2. Create Users across hierarchy
        cls.admin_user = User(
            email="superadmin@clubops.ai",
            full_name="Super Admin",
            hashed_password="pw",
            role=UserRole.ADMIN,
            is_active=True
        )
        cls.club_head1 = User(
            email="head1@clubops.ai",
            full_name="Club Head 1",
            hashed_password="pw",
            role=UserRole.CLUB_HEAD,
            club_id=cls.club1.id,
            is_active=True
        )
        cls.club_head2 = User(
            email="head2@clubops.ai",
            full_name="Club Head 2",
            hashed_password="pw",
            role=UserRole.CLUB_HEAD,
            club_id=cls.club2.id,
            is_active=True
        )
        cls.lead_user1 = User(
            email="lead1@clubops.ai",
            full_name="Lead One",
            hashed_password="pw",
            role=UserRole.SUBTEAM_LEAD,
            club_id=cls.club1.id,
            is_active=True
        )
        cls.vol_user1 = User(
            email="vol1@clubops.ai",
            full_name="Volunteer One",
            hashed_password="pw",
            role=UserRole.VOLUNTEER,
            club_id=cls.club1.id,
            is_active=True
        )
        db.add_all([cls.admin_user, cls.club_head1, cls.club_head2, cls.lead_user1, cls.vol_user1])
        db.flush()

        cls.admin_user_id = cls.admin_user.id
        cls.club_head1_id = cls.club_head1.id
        cls.club_head2_id = cls.club_head2.id
        cls.lead_user1_id = cls.lead_user1.id
        cls.vol_user1_id = cls.vol_user1.id
        cls.club1_id = cls.club1.id
        cls.club2_id = cls.club2.id

        # 3. Create Volunteer profile
        cls.volunteer1 = Volunteer(
            user_id=cls.vol_user1.id,
            club_id=cls.club1.id,
            status=VolunteerStatus.ACTIVE,
            skills="Robotics, Python"
        )
        db.add(cls.volunteer1)
        db.commit()
        cls.volunteer1_id = cls.volunteer1.id
        db.close()

        def override_get_db():
            db_session = cls.TestingSessionLocal()
            try:
                yield db_session
            finally:
                db_session.close()

        app.dependency_overrides[deps.get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=cls.engine)

    def _auth_header(self, user_id: int):
        token = create_access_token(str(user_id))
        return {"Authorization": f"Bearer {token}"}

    def test_01_event_date_time_preservation_and_update(self):
        """Verify that event scheduled date-time parses correctly and does not skew on create and update."""
        admin_headers = self._auth_header(self.admin_user_id)
        target_datetime_str = "2026-10-15T14:30"

        # Create event with local datetime string
        payload = {
            "title": "National Robotics Symposium",
            "description": "Annual state-of-the-art keynote symposium",
            "date": target_datetime_str,
            "venue": "Main Hall Auditorium",
            "budget": 50000.0,
            "expected_attendance": 250,
            "status": "PUBLISHED"
        }
        res = self.client.post("/api/v1/events/", json=payload, headers=admin_headers)
        self.assertEqual(res.status_code, 200, res.text)
        created = res.json()
        self.assertEqual(created["title"], "National Robotics Symposium")
        
        # Verify date preserves scheduled hour (14:30)
        created_date = created["date"]
        self.assertTrue(created_date.startswith("2026-10-15T14:30"), f"Expected 2026-10-15T14:30, got {created_date}")

        # Update event date and ensure update preserves local time
        new_datetime_str = "2026-11-20T09:15"
        update_payload = {"date": new_datetime_str}
        update_res = self.client.put(f"/api/v1/events/{created['id']}", json=update_payload, headers=admin_headers)
        self.assertEqual(update_res.status_code, 200, update_res.text)
        updated = update_res.json()
        self.assertTrue(updated["date"].startswith("2026-11-20T09:15"), f"Expected 2026-11-20T09:15, got {updated['date']}")

    def test_02_event_deletion_with_all_cascading_dependencies(self):
        """Verify that deleting an event with tasks, escalations, risks, meetings, action items, memberships succeeds without FK errors."""
        db = self.TestingSessionLocal()
        admin_headers = self._auth_header(self.admin_user_id)

        # Setup event with complete dependency web
        event = Event(
            title="Complex Event with Dependencies",
            date=datetime(2026, 12, 1, 10, 0),
            club_id=self.club1_id,
            created_by=self.admin_user_id
        )
        db.add(event)
        db.flush()

        # Task 1 (parent) and Task 2 (child)
        t1 = Task(title="Task 1", event_id=event.id, status=TaskStatus.TODO, created_by=self.admin_user_id)
        db.add(t1)
        db.flush()
        t2 = Task(title="Task 2 Subtask", event_id=event.id, parent_id=t1.id, status=TaskStatus.TODO)
        db.add(t2)
        db.flush()

        # Task dependency, assignment, comment
        dep = TaskDependency(dependent_task_id=t2.id, prerequisite_task_id=t1.id)
        db.add(dep)
        assign = TaskAssignment(task_id=t1.id, volunteer_id=self.volunteer1_id)
        db.add(assign)
        comment = TaskComment(task_id=t1.id, user_id=self.admin_user_id, content="Urgent task")
        db.add(comment)

        # Escalation pointing to task and event
        esc = TaskEscalation(
            task_id=t1.id,
            event_id=event.id,
            reason="Blocked by prerequisite hardware arrival",
            level=EscalationLevel.TEAM_LEADER.value,
            status=EscalationStatus.PENDING.value
        )
        db.add(esc)

        # Risk
        risk = EventRisk(
            event_id=event.id,
            task_id=t1.id,
            category="SCHEDULE",
            title="Venue delay risk",
            description="Speaker travel schedule tight"
        )
        db.add(risk)

        # Meeting & Action item
        meeting = Meeting(event_id=event.id, title="Planning Sync 1")
        db.add(meeting)
        db.flush()
        ai = MeetingActionItem(
            meeting_id=meeting.id,
            raw_text="Confirm projector",
            title="Confirm projector",
            resolved_volunteer_id=self.volunteer1_id
        )
        db.add(ai)

        # Membership
        membership = EventMembership(event_id=event.id, user_id=self.admin_user_id, role=EventRole.EVENT_COORDINATOR)
        db.add(membership)

        # Budget category & Expense
        bcat = EventBudgetCategory(event_id=event.id, name="Logistics", allocated_amount=5000.0)
        db.add(bcat)
        exp = Expense(event_id=event.id, amount=1200.0, description="Banner printing")
        db.add(exp)

        db.commit()
        event_id = event.id
        db.close()

        # Call delete as Admin
        del_res = self.client.delete(f"/api/v1/events/{event_id}", headers=admin_headers)
        self.assertEqual(del_res.status_code, 200, del_res.text)
        self.assertEqual(del_res.json(), {"ok": True})

        # Confirm event and all child rows are deleted from DB
        db2 = self.TestingSessionLocal()
        self.assertIsNone(db2.query(Event).filter(Event.id == event_id).first())
        self.assertEqual(db2.query(Task).filter(Task.event_id == event_id).count(), 0)
        self.assertEqual(db2.query(TaskEscalation).filter(TaskEscalation.event_id == event_id).count(), 0)
        self.assertEqual(db2.query(EventRisk).filter(EventRisk.event_id == event_id).count(), 0)
        self.assertEqual(db2.query(Meeting).filter(Meeting.event_id == event_id).count(), 0)
        self.assertEqual(db2.query(EventMembership).filter(EventMembership.event_id == event_id).count(), 0)
        db2.close()

    def test_03_volunteer_deletion_with_assignments_and_action_items(self):
        """Verify that deleting a volunteer removes their task assignments and cleans action item references cleanly."""
        db = self.TestingSessionLocal()
        admin_headers = self._auth_header(self.admin_user_id)

        # Create fresh user and volunteer
        user_to_delete = User(
            email="tempvol@clubops.ai",
            full_name="Temporary Volunteer",
            hashed_password="pw",
            role=UserRole.VOLUNTEER,
            club_id=self.club1_id,
            is_active=True
        )
        db.add(user_to_delete)
        db.flush()
        vol_to_delete = Volunteer(
            user_id=user_to_delete.id,
            club_id=self.club1_id,
            status=VolunteerStatus.ACTIVE,
            skills="Audio, Photography"
        )
        db.add(vol_to_delete)
        db.flush()

        # Create event and task
        ev = Event(title="Vol Test Event", date=datetime(2026, 12, 10, 10, 0), club_id=self.club1_id)
        db.add(ev)
        db.flush()
        t = Task(title="Vol Assignment Task", event_id=ev.id)
        db.add(t)
        db.flush()

        # Assign volunteer to task
        assign = TaskAssignment(task_id=t.id, volunteer_id=vol_to_delete.id)
        db.add(assign)

        # Add meeting action item resolved to this volunteer
        m = Meeting(event_id=ev.id, title="Vol Meeting")
        db.add(m)
        db.flush()
        ai = MeetingActionItem(
            meeting_id=m.id,
            raw_text="Photograph stage",
            title="Photograph stage",
            resolved_volunteer_id=vol_to_delete.id
        )
        db.add(ai)
        db.commit()

        vol_id = vol_to_delete.id
        ai_id = ai.id
        db.close()

        # Delete volunteer as Admin
        del_res = self.client.delete(f"/api/v1/volunteers/{vol_id}", headers=admin_headers)
        self.assertEqual(del_res.status_code, 200, del_res.text)

        # Verify DB state
        db2 = self.TestingSessionLocal()
        self.assertIsNone(db2.query(Volunteer).filter(Volunteer.id == vol_id).first())
        self.assertEqual(db2.query(TaskAssignment).filter(TaskAssignment.volunteer_id == vol_id).count(), 0)
        action_item = db2.query(MeetingActionItem).filter(MeetingActionItem.id == ai_id).first()
        self.assertIsNotNone(action_item)
        self.assertIsNone(action_item.resolved_volunteer_id)
        db2.close()

    def test_04_hierarchy_authorization_admin_vs_club_head(self):
        """Verify that Admin has global authorization across clubs, while Club Head is scoped to their club."""
        db = self.TestingSessionLocal()
        admin_headers = self._auth_header(self.admin_user_id)
        head1_headers = self._auth_header(self.club_head1_id)
        head2_headers = self._auth_header(self.club_head2_id)

        # Event in Club 1
        ev_club1 = Event(title="Club 1 Private Event", date=datetime(2026, 12, 15, 14, 0), club_id=self.club1_id)
        # Event in Club 2
        ev_club2 = Event(title="Club 2 Private Event", date=datetime(2026, 12, 20, 14, 0), club_id=self.club2_id)
        db.add_all([ev_club1, ev_club2])
        db.commit()

        c1_id = ev_club1.id
        c2_id = ev_club2.id
        db.close()

        # Head 1 can access Club 1 event
        res = self.client.get(f"/api/v1/events/{c1_id}", headers=head1_headers)
        self.assertEqual(res.status_code, 200)

        # Head 1 CANNOT access or delete Club 2 event (403 Forbidden)
        res = self.client.get(f"/api/v1/events/{c2_id}", headers=head1_headers)
        self.assertEqual(res.status_code, 403)
        res_del = self.client.delete(f"/api/v1/events/{c2_id}", headers=head1_headers)
        self.assertEqual(res_del.status_code, 403)

        # Admin CAN access and delete Club 2 event (Global access)
        res_admin = self.client.get(f"/api/v1/events/{c2_id}", headers=admin_headers)
        self.assertEqual(res_admin.status_code, 200)
        res_admin_del = self.client.delete(f"/api/v1/events/{c2_id}", headers=admin_headers)
        self.assertEqual(res_admin_del.status_code, 200)

    def test_rag_document_upload_admin_and_club_head_only(self):
        """Verify that for RAG, only Admin and Club Head can upload documents, while other roles are 403 Forbidden."""
        admin_headers = self._auth_header(self.admin_user_id)
        head_headers = self._auth_header(self.club_head1_id)
        lead_headers = self._auth_header(self.lead_user1_id)
        vol_headers = self._auth_header(self.vol_user1_id)

        file_payload = {
            "file": ("notes.txt", b"Past event post-mortem meeting notes for RAG indexing", "text/plain")
        }
        form_data = {
            "name": "Post Mortem Notes",
            "category": "POST_MORTEM"
        }

        # 1. Unauthenticated request -> 401
        res_unauth = self.client.post("/api/documents/upload", files=file_payload, data=form_data)
        self.assertEqual(res_unauth.status_code, 401)

        # 2. Volunteer request -> 403 Forbidden
        file_payload["file"] = ("vol_doc.txt", b"Volunteer document attempt", "text/plain")
        res_vol = self.client.post("/api/documents/upload", headers=vol_headers, files=file_payload, data=form_data)
        self.assertEqual(res_vol.status_code, 403)
        self.assertIn("Permission denied", res_vol.json()["detail"])

        # 3. SubTeam Lead request -> 403 Forbidden
        file_payload["file"] = ("lead_doc.txt", b"Lead document attempt", "text/plain")
        res_lead = self.client.post("/api/documents/upload", headers=lead_headers, files=file_payload, data=form_data)
        self.assertEqual(res_lead.status_code, 403)
        self.assertIn("Permission denied", res_lead.json()["detail"])

        # 4. Club Head request -> 403 Forbidden (Only System Admin can add documents into RAG knowledge base)
        file_payload["file"] = ("head_doc.txt", b"Club Head official post-mortem notes for RAG", "text/plain")
        res_head = self.client.post("/api/documents/upload", headers=head_headers, files=file_payload, data=form_data)
        self.assertEqual(res_head.status_code, 403)
        self.assertIn("Permission denied", res_head.json()["detail"])

        # 5. Admin request -> 201 Created
        file_payload["file"] = ("admin_doc.txt", b"Admin official campus venue policy guide", "text/plain")
        res_admin = self.client.post("/api/documents/upload", headers=admin_headers, files=file_payload, data={"name": "Venue Guide", "category": "VENUE_RULES"})
        self.assertEqual(res_admin.status_code, 201)
        data_admin = res_admin.json()
        self.assertIn("id", data_admin)
        self.assertEqual(data_admin["name"], "Venue Guide")


if __name__ == "__main__":
    unittest.main()

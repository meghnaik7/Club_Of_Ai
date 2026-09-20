import unittest
from datetime import datetime, timedelta
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db.base  # ensures all models (User, Volunteer, Event, etc.) are registered in SQLAlchemy
from app.db.base_class import Base
from app.models.user import User, UserRole
from app.models.event import Event, EventStatus
from app.models.announcement import Announcement
from app.services import announcement_service
import ai.tools.announcement_tools as announcement_tools

class TestAnnouncementModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # In-memory SQLite for testing our written announcement code
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

        # Patch SessionLocal in announcement_tools to use test database
        cls.original_tool_session = announcement_tools.SessionLocal
        announcement_tools.SessionLocal = cls.TestingSessionLocal

    @classmethod
    def tearDownClass(cls):
        announcement_tools.SessionLocal = cls.original_tool_session
        Base.metadata.drop_all(bind=cls.engine)

    def setUp(self):
        self.db = self.TestingSessionLocal()
        # Create a sample user
        self.user = User(
            email="organizer@clubofai.org",
            hashed_password="fakehashedpassword",
            full_name="Alex Organizer",
            role=UserRole.ADMIN,
            is_active=True
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        # Create a sample event
        self.event = Event(
            title="AI Hackathon 2026",
            description="A 24-hour campus hackathon to build intelligent autonomous agents.",
            date=datetime.utcnow() + timedelta(days=7),
            venue="Auditorium Hall B",
            budget=5000.0,
            expected_attendance=150,
            status=EventStatus.PUBLISHED,
            created_by=self.user.id
        )
        self.db.add(self.event)
        self.db.commit()
        self.db.refresh(self.event)

    def tearDown(self):
        self.db.query(Announcement).delete()
        self.db.query(Event).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_create_announcement(self):
        """Test creating an announcement draft."""
        announcement = announcement_service.create_announcement(
            db=self.db,
            title="Hacker Registration Now Open!",
            content="Teams of 2-4 can now register for AI Hackathon 2026.",
            event_id=self.event.id,
            target_audience="College Tech Students",
            user_id=self.user.id
        )
        self.assertIsNotNone(announcement.id)
        self.assertEqual(announcement.title, "Hacker Registration Now Open!")
        self.assertEqual(announcement.status, "DRAFT")
        self.assertEqual(announcement.event_id, self.event.id)
        self.assertEqual(announcement.target_audience, "College Tech Students")

    def test_generate_announcement_from_live_event(self):
        """Test AI generation uses live event information (title, venue, description)."""
        gen_data = announcement_service.generate_announcement(
            db=self.db,
            event_id=self.event.id,
            tone="exciting",
            target_audience="All AI Enthusiasts"
        )
        self.assertEqual(gen_data["event_id"], self.event.id)
        self.assertEqual(gen_data["event_title"], self.event.title)
        self.assertIn("AI Hackathon 2026", gen_data["title"])
        self.assertIn("Auditorium Hall B", gen_data["content"])
        self.assertIn("autonomous agents", gen_data["content"])

    def test_generate_announcement_variants(self):
        """Test multi-channel variant generation for WhatsApp, Email, and Instagram."""
        announcement = announcement_service.create_announcement(
            db=self.db,
            title="AI Hackathon Approaching",
            content="Mark your calendar for AI Hackathon 2026 at Auditorium Hall B.",
            event_id=self.event.id
        )

        variants = announcement_service.generate_announcement_variants(
            db=self.db,
            content=announcement.content,
            event_id=self.event.id,
            announcement_id=announcement.id
        )

        # 1. WhatsApp verification
        self.assertIn("whatsapp", variants)
        self.assertIn("AI Hackathon 2026", variants["whatsapp"])
        self.assertTrue("*Date:*" in variants["whatsapp"] or "Date" in variants["whatsapp"] or "2026" in variants["whatsapp"])
        self.assertIn("Auditorium Hall B", variants["whatsapp"])

        # 2. Email verification
        self.assertIn("email", variants)
        self.assertIn("subject", variants["email"])
        self.assertIn("body", variants["email"])
        self.assertIn("AI Hackathon 2026", variants["email"]["subject"])
        self.assertIn("Auditorium Hall B", variants["email"]["body"])

        # 3. Instagram verification
        self.assertIn("instagram", variants)
        self.assertIn("caption", variants["instagram"])
        self.assertIn("hashtags", variants["instagram"])
        self.assertIn("#ClubOfAI", variants["instagram"]["hashtags"])

        # Verify variants are persisted in DB
        self.db.refresh(announcement)
        self.assertIsNotNone(announcement.variants)
        saved_variants = json.loads(announcement.variants)
        self.assertIn("whatsapp", saved_variants)
        self.assertIn("email", saved_variants)
        self.assertIn("instagram", saved_variants)

    def test_get_and_list_announcements(self):
        """Test retrieving single draft and listing announcement history."""
        a1 = announcement_service.create_announcement(
            db=self.db,
            title="First Notice",
            content="First notice content",
            event_id=self.event.id
        )
        a2 = announcement_service.create_announcement(
            db=self.db,
            title="Second Notice",
            content="Second notice content",
            event_id=self.event.id
        )

        # Get announcement
        fetched = announcement_service.get_announcement(self.db, a1.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, "First Notice")

        # List announcements
        results = announcement_service.list_announcements(self.db, event_id=self.event.id)
        self.assertEqual(len(results), 2)
        titles = [r.title for r in results]
        self.assertIn("First Notice", titles)
        self.assertIn("Second Notice", titles)

    def test_update_announcement(self):
        """Test updating announcement fields."""
        announcement = announcement_service.create_announcement(
            db=self.db,
            title="Draft 1",
            content="Initial text",
            event_id=self.event.id
        )
        updated = announcement_service.update_announcement(
            db=self.db,
            announcement_id=announcement.id,
            title="Draft 1 Finalized",
            content="Polished text for distribution.",
            status="READY"
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.title, "Draft 1 Finalized")
        self.assertEqual(updated.content, "Polished text for distribution.")
        self.assertEqual(updated.status, "READY")

    def test_delete_announcement(self):
        """Test deleting announcement draft."""
        announcement = announcement_service.create_announcement(
            db=self.db,
            title="To be deleted",
            content="Temporary draft",
            event_id=self.event.id
        )
        deleted = announcement_service.delete_announcement(self.db, announcement.id)
        self.assertTrue(deleted)
        self.assertIsNone(announcement_service.get_announcement(self.db, announcement.id))

    def test_ai_tools_invocation(self):
        """Test the 7 LangChain announcement tools in ai/tools/announcement_tools.py."""
        # 1. create_announcement tool
        tool_res = announcement_tools.create_announcement.invoke({
            "title": "Tool Created Draft",
            "content": "Content via AI tool invocation",
            "event_id": self.event.id,
            "target_audience": "Volunteers"
        })
        self.assertIn("id", tool_res)
        self.assertEqual(tool_res["title"], "Tool Created Draft")
        announcement_id = tool_res["id"]

        # 2. get_announcement tool
        get_res = announcement_tools.get_announcement.invoke({"announcement_id": announcement_id})
        self.assertEqual(get_res["title"], "Tool Created Draft")

        # 3. generate_announcement tool
        gen_res = announcement_tools.generate_announcement.invoke({
            "event_id": self.event.id,
            "tone": "enthusiastic"
        })
        self.assertIn("title", gen_res)
        self.assertIn("content", gen_res)

        # 4. generate_announcement_variants tool
        var_res = announcement_tools.generate_announcement_variants.invoke({
            "announcement_id": announcement_id,
            "event_id": self.event.id
        })
        self.assertIn("whatsapp", var_res)
        self.assertIn("email", var_res)
        self.assertIn("instagram", var_res)

        # 5. list_announcements tool
        list_res = announcement_tools.list_announcements.invoke({"event_id": self.event.id})
        self.assertIsInstance(list_res, list)
        self.assertGreaterEqual(len(list_res), 1)

        # 6. update_announcement tool
        update_res = announcement_tools.update_announcement.invoke({
            "announcement_id": announcement_id,
            "title": "Tool Updated Title",
            "status": "APPROVED"
        })
        self.assertEqual(update_res["title"], "Tool Updated Title")
        self.assertEqual(update_res["status"], "APPROVED")

        # 7. delete_announcement tool
        del_res = announcement_tools.delete_announcement.invoke({"announcement_id": announcement_id})
        self.assertTrue(del_res["success"])

if __name__ == "__main__":
    unittest.main()

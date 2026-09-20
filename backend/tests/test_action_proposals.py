import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db.base
from app.db.base_class import Base
from app.models.user import User, UserRole
from app.models.event import Event
from app.models.task import Task
from app.models.audit_log import AuditLog
from ai.schemas.ai_proposal import AIProposal, AIProposalChange, ProposalStatus
from ai.workflows import proposal_service
import ai.tools.proposal_tools as proposal_tools

class TestActionProposalModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

        cls.original_session_local = proposal_tools.SessionLocal
        proposal_tools.SessionLocal = cls.TestingSessionLocal

    @classmethod
    def tearDownClass(cls):
        proposal_tools.SessionLocal = cls.original_session_local
        Base.metadata.drop_all(bind=cls.engine)

    def setUp(self):
        self.db = self.TestingSessionLocal()
        self.user = User(
            email="lead_proposer@clubofai.org",
            hashed_password="hashed_pw",
            full_name="Morgan Organizer",
            role=UserRole.ADMIN,
            is_active=True
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self):
        self.db.query(AuditLog).delete()
        self.db.query(Task).delete()
        self.db.query(Event).delete()
        self.db.query(AIProposalChange).delete()
        self.db.query(AIProposal).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_create_action_proposal_does_not_mutate_state(self):
        """Test creating an action proposal stages changes without modifying production state."""
        event_count_before = self.db.query(Event).count()
        task_count_before = self.db.query(Task).count()

        proposal = proposal_service.create_proposal(
            db=self.db,
            user_id=self.user.id,
            intent="Organize AI Demo Day",
            changes=[
                {
                    "entity_type": "Event",
                    "action": "CREATE",
                    "proposed_data": {
                        "title": "AI Demo Day 2026",
                        "description": "Showcase club projects",
                        "venue": "Campus Hall C",
                        "budget": 1200.0
                    },
                    "explanation": "Create new AI Demo Day event"
                },
                {
                    "entity_type": "Task",
                    "action": "CREATE",
                    "proposed_data": {
                        "title": "Print Posters",
                        "description": "Print 50 A3 event posters"
                    },
                    "explanation": "Create promotional task"
                }
            ]
        )

        self.assertIsNotNone(proposal.proposal_id)
        self.assertEqual(proposal.status, "PENDING")
        self.assertEqual(len(proposal.changes), 2)

        # Confirm ZERO production records were created
        self.assertEqual(self.db.query(Event).count(), event_count_before)
        self.assertEqual(self.db.query(Task).count(), task_count_before)

    def test_get_action_proposal(self):
        """Test retrieving proposal changes and status."""
        proposal = proposal_service.create_proposal(
            db=self.db,
            user_id=self.user.id,
            intent="Schedule Workshop",
            changes=[{
                "entity_type": "Event",
                "action": "CREATE",
                "proposed_data": {"title": "Python Workshop"},
                "explanation": "Workshop setup"
            }]
        )

        fetched = proposal_service.get_proposal(self.db, proposal.proposal_id)
        self.assertEqual(fetched.proposal_id, proposal.proposal_id)
        self.assertEqual(fetched.intent, "Schedule Workshop")
        self.assertEqual(fetched.status, "PENDING")
        self.assertEqual(len(fetched.changes), 1)

    def test_preview_action_diff(self):
        """Test previewing exact entity and field diffs before user confirmation."""
        proposal = proposal_service.create_proposal(
            db=self.db,
            user_id=self.user.id,
            intent="Launch Hackathon",
            changes=[{
                "entity_type": "Event",
                "action": "CREATE",
                "proposed_data": {
                    "title": "Hackathon 2026",
                    "budget": 2500.0,
                    "venue": "Engineering Center"
                }
            }]
        )

        diff_preview = proposal_service.preview_action_diff(self.db, proposal.proposal_id)
        self.assertEqual(diff_preview.proposal_id, proposal.proposal_id)
        self.assertEqual(diff_preview.total_changes, 1)
        self.assertIn("Event", diff_preview.entities_affected)

        field_diffs = diff_preview.diffs[0].field_diffs
        fields_changed = {f.field: f.change_type for f in field_diffs}
        self.assertIn("title", fields_changed)
        self.assertEqual(fields_changed["title"], "ADDED")
        self.assertIn("budget", fields_changed)
        self.assertEqual(fields_changed["budget"], "ADDED")

    def test_apply_action_proposal_and_audit_log(self):
        """Test applying proposal atomically, creating entities, and recording audit log."""
        proposal = proposal_service.create_proposal(
            db=self.db,
            user_id=self.user.id,
            intent="Create Workshop and Stage Setup",
            changes=[
                {
                    "entity_type": "Event",
                    "action": "CREATE",
                    "proposed_data": {
                        "title": "Hands-on PyTorch Workshop",
                        "description": "Deep learning models",
                        "venue": "Computer Lab 4"
                    }
                },
                {
                    "entity_type": "Task",
                    "action": "CREATE",
                    "proposed_data": {
                        "title": "Install PyTorch on 30 lab machines",
                        "description": "Run pip install torch across machines"
                    }
                }
            ]
        )

        # Apply proposal
        applied = proposal_service.apply_proposal(self.db, proposal.proposal_id, user_id=self.user.id)
        self.assertEqual(applied.status, "APPLIED")

        # Verify Event and Task were created in DB
        event = self.db.query(Event).filter(Event.title == "Hands-on PyTorch Workshop").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.venue, "Computer Lab 4")

        task = self.db.query(Task).filter(Task.title == "Install PyTorch on 30 lab machines").first()
        self.assertIsNotNone(task)

        # Verify AuditLog entries were written
        audit_logs = proposal_service.get_action_audit_log(self.db, proposal_id=proposal.proposal_id)
        self.assertEqual(len(audit_logs), 2)
        actions = [a.action for a in audit_logs]
        self.assertIn("CREATE", actions)
        self.assertEqual(audit_logs[0].user_id, self.user.id)

    def test_undo_action(self):
        """Test rolling back an applied action using its audit trail."""
        proposal = proposal_service.create_proposal(
            db=self.db,
            user_id=self.user.id,
            intent="Event to be undone",
            changes=[
                {
                    "entity_type": "Event",
                    "action": "CREATE",
                    "proposed_data": {"title": "Temporary Event", "venue": "Room 101"}
                },
                {
                    "entity_type": "Task",
                    "action": "CREATE",
                    "proposed_data": {"title": "Temporary Task"}
                }
            ]
        )
        proposal_service.apply_proposal(self.db, proposal.proposal_id, user_id=self.user.id)

        # Confirm entities exist
        self.assertIsNotNone(self.db.query(Event).filter(Event.title == "Temporary Event").first())
        self.assertIsNotNone(self.db.query(Task).filter(Task.title == "Temporary Task").first())

        # Undo proposal
        undone = proposal_service.undo_proposal(self.db, proposal.proposal_id, user_id=self.user.id)
        self.assertEqual(undone.status, "UNDONE")

        # Confirm entities were deleted
        self.assertIsNone(self.db.query(Event).filter(Event.title == "Temporary Event").first())
        self.assertIsNone(self.db.query(Task).filter(Task.title == "Temporary Task").first())

    def test_reject_action_proposal(self):
        """Test rejecting a pending proposal without modifying application state."""
        proposal = proposal_service.create_proposal(
            db=self.db,
            user_id=self.user.id,
            intent="Bad Plan to Reject",
            changes=[{
                "entity_type": "Event",
                "action": "CREATE",
                "proposed_data": {"title": "Unapproved Rave Party"}
            }]
        )

        rejected = proposal_service.reject_proposal(self.db, proposal.proposal_id, reason="Inappropriate event")
        self.assertEqual(rejected.status, "REJECTED")

        # Confirm nothing was created
        self.assertIsNone(self.db.query(Event).filter(Event.title == "Unapproved Rave Party").first())

    def test_langchain_tools_invocation(self):
        """Test invoking all 7 LangChain proposal tools via .invoke()."""
        # 1. create_action_proposal tool
        create_res = proposal_tools.create_action_proposal.invoke({
            "intent": "Tool Proposal Test",
            "event_title": "LangChain Event",
            "tasks": [{"title": "Test Task 1", "phase": "PRE_EVENT"}]
        })
        self.assertIn("proposal_id", create_res)
        p_id = create_res["proposal_id"]

        # 2. get_action_proposal tool
        get_res = proposal_tools.get_action_proposal.invoke({"proposal_id": p_id})
        self.assertEqual(get_res["status"], "PENDING")

        # 3. preview_action_diff tool
        diff_res = proposal_tools.preview_action_diff.invoke({"proposal_id": p_id})
        self.assertIn("diffs", diff_res)
        self.assertGreater(diff_res["total_changes"], 0)

        # 4. apply_action_proposal tool
        apply_res = proposal_tools.apply_action_proposal.invoke({"proposal_id": p_id})
        self.assertTrue(apply_res["success"])
        self.assertEqual(apply_res["status"], "APPLIED")

        # 5. get_action_audit_log tool
        audit_res = proposal_tools.get_action_audit_log.invoke({"proposal_id": p_id})
        self.assertIsInstance(audit_res, list)
        self.assertGreater(len(audit_res), 0)

        # 6. undo_action tool
        undo_res = proposal_tools.undo_action.invoke({"proposal_id": p_id})
        self.assertTrue(undo_res["success"])
        self.assertEqual(undo_res["status"], "UNDONE")

        # 7. reject_action_proposal tool (on new proposal)
        p2 = proposal_tools.create_action_proposal.invoke({
            "intent": "Reject Test",
            "event_title": "Cancel Event"
        })
        reject_res = proposal_tools.reject_action_proposal.invoke({
            "proposal_id": p2["proposal_id"],
            "reason": "Cancelled by user"
        })
        self.assertTrue(reject_res["success"])
        self.assertEqual(reject_res["status"], "REJECTED")

if __name__ == "__main__":
    unittest.main()

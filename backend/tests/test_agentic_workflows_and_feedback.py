import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db.base
from app.db.base_class import Base
from app.models.user import User, UserRole
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.event import Event
from app.models.task import Task, TaskAssignment, TaskDependency, TaskStatus, TaskPriority, TaskPhase
from app.models.feedback import AIFeedback
from app.models.audit_log import AuditLog
from ai.schemas.ai_proposal import AIProposal, AIProposalChange, ProposalStatus
from ai.workflows import proposal_service, task_planning_engine
from ai.tools.agentic_tools import (
    plan_event_agentic,
    recover_delayed_event,
    redistribute_volunteer_tasks,
    extract_meeting_action_items,
    agentic_rag_query,
    analyze_and_resolve_risks
)
from ai.tools.command_tool import execute_command
import app.services.context_service as context_service_mod
from fastapi.testclient import TestClient
from app.main import app
from app.api import deps

import ai.tools.agentic_tools as agentic_tools_mod
import ai.tools.command_tool as command_tool_mod
import ai.workflows.task_planning_engine as planning_engine_mod


from sqlalchemy.pool import StaticPool

class TestAgenticWorkflowsAndFeedback(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        Base.metadata.create_all(bind=cls.engine)

        import app.db.session as session_mod
        cls.orig_app_session = session_mod.SessionLocal
        session_mod.SessionLocal = cls.TestingSessionLocal

        # Patch SessionLocal across relevant modules
        cls.orig_agentic_session = agentic_tools_mod.SessionLocal
        cls.orig_command_session = command_tool_mod.SessionLocal
        cls.orig_planning_session = planning_engine_mod.SessionLocal

        agentic_tools_mod.SessionLocal = cls.TestingSessionLocal
        command_tool_mod.SessionLocal = cls.TestingSessionLocal
        planning_engine_mod.SessionLocal = cls.TestingSessionLocal

        def override_get_db():
            db = cls.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[deps.get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        import app.db.session as session_mod
        session_mod.SessionLocal = cls.orig_app_session
        agentic_tools_mod.SessionLocal = cls.orig_agentic_session
        command_tool_mod.SessionLocal = cls.orig_command_session
        planning_engine_mod.SessionLocal = cls.orig_planning_session
        Base.metadata.drop_all(bind=cls.engine)


    def setUp(self):
        self.db = self.TestingSessionLocal()
        # Admin / Organizer
        self.admin = User(
            email="lead@clubops.org",
            hashed_password="pw",
            full_name="Morgan Organizer",
            role=UserRole.ADMIN,
            is_active=True
        )
        # Volunteer 1: Rahul
        self.user_rahul = User(
            email="rahul@clubops.org",
            hashed_password="pw",
            full_name="Rahul Sharma",
            role=UserRole.VOLUNTEER,
            is_active=True
        )
        # Volunteer 2: Priya
        self.user_priya = User(
            email="priya@clubops.org",
            hashed_password="pw",
            full_name="Priya Patel",
            role=UserRole.VOLUNTEER,
            is_active=True
        )
        self.db.add_all([self.admin, self.user_rahul, self.user_priya])
        self.db.commit()

        self.vol_rahul = Volunteer(
            user_id=self.user_rahul.id,
            skills="Stage Setup, Equipment, Decoration",
            status=VolunteerStatus.ACTIVE,
            max_capacity=10
        )
        self.vol_priya = Volunteer(
            user_id=self.user_priya.id,
            skills="Marketing, Sponsorship, Coordination, Stage Setup",
            status=VolunteerStatus.ACTIVE,
            max_capacity=10
        )
        self.event = Event(
            title="TechFest 2026",
            description="Flagship annual college tech festival",
            venue="Main Auditorium",
            expected_attendance=500,
            budget=75000.0,
            date=datetime.utcnow() + timedelta(days=20),
            created_by=self.admin.id
        )
        self.db.add_all([self.vol_rahul, self.vol_priya, self.event])
        self.db.commit()

    def tearDown(self):
        self.db.query(AIFeedback).delete()
        self.db.query(AuditLog).delete()
        self.db.query(TaskDependency).delete()
        self.db.query(TaskAssignment).delete()
        self.db.query(Task).delete()
        self.db.query(Event).delete()
        self.db.query(Volunteer).delete()
        self.db.query(AIProposalChange).delete()
        self.db.query(AIProposal).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_ai_feedback_model_and_analytics(self):
        """Test submitting AI feedback and computing evaluation analytics."""
        proposal = proposal_service.create_proposal(
            db=self.db,
            user_id=self.admin.id,
            intent="Test proposal for feedback"
        )
        # Add feedback entries
        fb1 = AIFeedback(
            proposal_id=proposal.proposal_id,
            user_id=self.admin.id,
            event_id=self.event.id,
            rating="GOOD",
            feedback_type="positive_execution"
        )
        fb2 = AIFeedback(
            proposal_id=proposal.proposal_id,
            user_id=self.admin.id,
            event_id=self.event.id,
            rating="POOR",
            feedback_type="wrong_volunteer",
            comment="Priya was already handling another critical task."
        )
        self.db.add_all([fb1, fb2])
        self.db.commit()

        feedbacks = self.db.query(AIFeedback).all()
        self.assertEqual(len(feedbacks), 2)
        self.assertEqual(feedbacks[1].feedback_type, "wrong_volunteer")

    def test_volunteer_recommender_closed_loop_feedback_penalty(self):
        """Test that negative feedback (e.g. wrong_volunteer / assignment_conflict) penalizes volunteer match score."""
        # Baseline suggestion for a Stage Setup task
        baseline = task_planning_engine.suggest_task_owner(
            task_title="Stage Setup and Audio Check",
            task_skills=["Stage Setup"],
            db=self.db
        )
        recs = baseline.get("recommendations", [])
        self.assertTrue(len(recs) >= 2)

        # Record negative feedback specifically targeting Rahul
        neg_fb = AIFeedback(
            user_id=self.admin.id,
            rating="POOR",
            feedback_type="wrong_volunteer",
            comment=f"Rahul Sharma #{self.vol_rahul.id} had assignment conflict on Stage Setup.",
            metadata_json={"volunteer_id": self.vol_rahul.id}
        )
        self.db.add(neg_fb)
        self.db.commit()

        # Suggest again after feedback stored
        penalized = task_planning_engine.suggest_task_owner(
            task_title="Stage Setup and Audio Check",
            task_skills=["Stage Setup"],
            db=self.db
        )
        penalized_recs = penalized.get("recommendations", [])
        rahul_rec = next((r for r in penalized_recs if r["volunteer_id"] == self.vol_rahul.id), None)
        self.assertIsNotNone(rahul_rec)
        self.assertLess(rahul_rec["feedback_adjustment"], 0)
        self.assertIn("Feedback Loop", rahul_rec["rationale"])

    def test_ai_event_planner_agent(self):
        """Test Area A: AI Event Planner generates phases, tasks, owners, and staging proposal with Diff."""
        res = plan_event_agentic.invoke({
            "event_title": "TechFest Hackathon",
            "event_date": (datetime.utcnow() + timedelta(days=15)).strftime("%Y-%m-%d"),
            "expected_attendance": 500,
            "budget": 60000.0,
            "venue": "Main Hall",
            "event_brief": "Create complete plan for TechFest with 500 students.",
            "user_id": self.admin.id
        })
        self.assertEqual(res.get("status"), "AWAITING_CONFIRMATION")
        self.assertIsNotNone(res.get("proposal_id"))
        self.assertTrue(res.get("total_tasks_generated") >= 3)
        
        diff = res.get("diff_preview", {})
        self.assertTrue(len(diff.get("diffs", [])) >= 3)
        first_task_diff = next((d for d in diff["diffs"] if d.get("entity_type") == "Task"), None)
        self.assertIsNotNone(first_task_diff)
        self.assertIsNotNone(first_task_diff.get("proposed"))
        self.assertIn("owner", first_task_diff["proposed"])

    def test_delay_recovery_agent(self):
        """Test Area 3: Delay Recovery calculates critical path, evaluates workload, formulates strategies, and diffs."""
        # Setup delayed task and downstream dependent task
        task_venue = Task(
            event_id=self.event.id,
            title="Venue Booking Confirmation",
            status=TaskStatus.IN_PROGRESS,
            due_date=datetime.utcnow() + timedelta(days=2)
        )
        self.db.add(task_venue)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task_venue.id, volunteer_id=self.vol_rahul.id))

        task_decor = Task(
            event_id=self.event.id,
            title="Hall Decoration",
            status=TaskStatus.TODO,
            due_date=datetime.utcnow() + timedelta(days=4)
        )
        self.db.add(task_decor)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task_decor.id, volunteer_id=self.vol_rahul.id))

        # Add dependency: Decoration depends on Venue
        self.db.add(TaskDependency(dependent_task_id=task_decor.id, prerequisite_task_id=task_venue.id))
        self.db.commit()

        # Run Delay Recovery Agent
        res = recover_delayed_event.invoke({
            "event_id": self.event.id,
            "delayed_task_id": task_venue.id,
            "delay_days": 3,
            "delay_reason": "Venue booking delayed by 3 days",
            "user_id": self.admin.id
        })
        self.assertEqual(res.get("status"), "AWAITING_CONFIRMATION")
        self.assertIsNotNone(res.get("proposal_id"))
        self.assertEqual(res.get("affected_dependent_count"), 1)

        diff = res.get("diff_preview", {})
        self.assertTrue(len(diff.get("diffs", [])) >= 2)
        
        # Verify Before vs Proposed card structure
        for d in diff["diffs"]:
            self.assertIsNotNone(d.get("before"))
            self.assertIsNotNone(d.get("proposed"))
            self.assertIsNotNone(d.get("reason"))
            self.assertIsNotNone(d.get("impact"))
            self.assertEqual(d.get("confidence"), "HIGH")

    def test_volunteer_redistribution_agent(self):
        """Test Area 4: Volunteer Management Agent redistributes tasks when a volunteer is unavailable."""
        # Assign 2 tasks to Rahul
        t1 = Task(event_id=self.event.id, title="Setup Projector & Sound", status=TaskStatus.TODO, due_date=datetime.utcnow() + timedelta(days=3))
        t2 = Task(event_id=self.event.id, title="Arrange Stage Lighting", status=TaskStatus.IN_PROGRESS, due_date=datetime.utcnow() + timedelta(days=4))
        self.db.add_all([t1, t2])
        self.db.flush()
        self.db.add_all([
            TaskAssignment(task_id=t1.id, volunteer_id=self.vol_rahul.id),
            TaskAssignment(task_id=t2.id, volunteer_id=self.vol_rahul.id)
        ])
        self.db.commit()

        # Rahul unavailable tomorrow
        res = redistribute_volunteer_tasks.invoke({
            "unavailable_volunteer_name_or_id": "Rahul",
            "event_id": self.event.id,
            "unavailability_reason": "Unavailable tomorrow",
            "user_id": self.admin.id
        })
        self.assertEqual(res.get("status"), "AWAITING_CONFIRMATION")
        self.assertEqual(res.get("tasks_redistributed"), 2)
        diff = res.get("diff_preview", {})
        self.assertEqual(len(diff.get("diffs", [])), 2)
        # Priya should be recommended as alternative
        self.assertIn("Priya", str(diff))

    def test_meeting_action_extractor_agent(self):
        """Test Area 5: Meeting Action Agent parses transcript and extracts action items with owner resolution."""
        meeting_notes = (
            "TechFest Core Meeting Notes:\n"
            "- Rahul will handle sponsorship by Friday\n"
            "- Priya will contact the venue\n"
        )
        res = extract_meeting_action_items.invoke({
            "meeting_notes": meeting_notes,
            "event_id": self.event.id,
            "user_id": self.admin.id
        })
        self.assertEqual(res.get("status"), "AWAITING_CONFIRMATION")
        self.assertIsNotNone(res.get("proposal_id"))
        self.assertTrue(len(res.get("actions_extracted", [])) >= 1)

    def test_risk_management_agent(self):
        """Test Area 7: Risk Management Agent performs deterministic detection and stages remediation proposal."""
        # Create unowned task near deadline (2 days away)
        unowned_task = Task(
            event_id=self.event.id,
            title="Urgent Sound Check",
            status=TaskStatus.TODO,
            due_date=datetime.utcnow() + timedelta(days=2)
        )
        self.db.add(unowned_task)
        self.db.commit()

        res = analyze_and_resolve_risks.invoke({
            "event_id": self.event.id,
            "auto_stage_proposal": True,
            "user_id": self.admin.id
        })
        self.assertEqual(res.get("status"), "AWAITING_CONFIRMATION")
        self.assertIsNotNone(res.get("proposal_id"))
        self.assertTrue(res.get("total_risks_detected") >= 1)
        diff = res.get("diff_preview", {})
        self.assertTrue(len(diff.get("diffs", [])) >= 1)

    def test_next_event_query_and_demo_fallback(self):
        """Test asking 'What is the next event?' returns complete upcoming event details and demo fallback."""
        # 1. Ask when event exists in DB
        res = execute_command.invoke({
            "command": "What is the next event?",
            "user_id": self.admin.id
        })
        self.assertEqual(res.get("status"), "COMPLETED")
        self.assertEqual(res.get("type"), "NEXT_EVENT_DETAILS")
        self.assertIn("TechFest 2026", res.get("message", ""))
        self.assertIn("Main Auditorium", res.get("message", ""))
        self.assertIsNotNone(res.get("result"))
        self.assertEqual(res["result"]["title"], "TechFest 2026")

        # 2. Test fallback when no events exist
        self.db.query(TaskDependency).delete()
        self.db.query(TaskAssignment).delete()
        self.db.query(Task).delete()
        self.db.query(Event).delete()
        self.db.commit()

        res_empty = execute_command.invoke({
            "command": "When is the next upcoming event?",
            "user_id": self.admin.id
        })
        self.assertEqual(res_empty.get("status"), "COMPLETED")
        self.assertEqual(res_empty.get("type"), "NEXT_EVENT_DETAILS")
        self.assertIn("AI Odyssey Hackathon 2026", res_empty.get("message", ""))

    def test_feedback_api_endpoints(self):
        """Test submitting feedback and querying feedback analytics via HTTP endpoints."""
        proposal = proposal_service.create_proposal(
            db=self.db,
            user_id=self.admin.id,
            intent="API feedback proposal"
        )
        # 1. Submit positive feedback
        resp1 = self.client.post("/api/v1/ai/feedback", json={
            "proposal_id": proposal.proposal_id,
            "event_id": self.event.id,
            "rating": "GOOD",
            "feedback_type": "positive_execution",
            "comment": "Accurate assignments and realistic deadlines."
        })
        self.assertEqual(resp1.status_code, 200)
        fb_data = resp1.json()
        self.assertEqual(fb_data["rating"], "GOOD")
        self.assertEqual(fb_data["feedback_type"], "positive_execution")

        # 2. Submit negative feedback with reason code
        resp2 = self.client.post("/api/v1/ai/feedback", json={
            "proposal_id": proposal.proposal_id,
            "event_id": self.event.id,
            "rating": "POOR",
            "feedback_type": "wrong_volunteer",
            "comment": "Volunteer had conflicting exam schedule."
        })
        self.assertEqual(resp2.status_code, 200)

        # 3. List recent feedbacks
        list_resp = self.client.get(f"/api/v1/ai/feedback?event_id={self.event.id}")
        self.assertEqual(list_resp.status_code, 200)
        items = list_resp.json()
        self.assertTrue(len(items) >= 2)

        # 4. Analytics endpoint
        analytics_resp = self.client.get(f"/api/v1/ai/feedback/analytics?event_id={self.event.id}")
        self.assertEqual(analytics_resp.status_code, 200)
        analytics = analytics_resp.json()
        self.assertTrue(analytics["total_feedbacks"] >= 2)
        self.assertEqual(analytics["positive_count"], 1)
        self.assertEqual(analytics["negative_count"], 1)
        self.assertEqual(analytics["satisfaction_rate_percent"], 50.0)
        self.assertIn("wrong_volunteer", analytics["top_negative_reasons"])


if __name__ == "__main__":
    unittest.main()


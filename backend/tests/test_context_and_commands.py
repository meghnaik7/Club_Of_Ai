import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db.base
from app.db.base_class import Base
from app.models.user import User, UserRole
from app.models.event import Event, EventStatus
from app.models.task import Task, TaskStatus, TaskAssignment
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.announcement import Announcement
from app.models.document import Document
from app.models.audit_log import AuditLog
from ai.schemas.ai_proposal import AIProposal, AIProposalChange, ProposalStatus

import ai.tools.context_tools as context_tools
import ai.tools.command_tool as command_tool
import ai.tools.proposal_tools as proposal_tools


class TestContextAndCommandsModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

        # Patch SessionLocal across tools
        cls.orig_context_session = context_tools.SessionLocal
        cls.orig_command_session = command_tool.SessionLocal
        cls.orig_proposal_session = proposal_tools.SessionLocal

        context_tools.SessionLocal = cls.TestingSessionLocal
        command_tool.SessionLocal = cls.TestingSessionLocal
        proposal_tools.SessionLocal = cls.TestingSessionLocal

    @classmethod
    def tearDownClass(cls):
        context_tools.SessionLocal = cls.orig_context_session
        command_tool.SessionLocal = cls.orig_command_session
        proposal_tools.SessionLocal = cls.orig_proposal_session
        Base.metadata.drop_all(bind=cls.engine)

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.TestingSessionLocal()
        
        # Create Lead User
        self.lead_user = User(
            email="lead@clubofai.org",
            hashed_password="hashed_lead_pw",
            full_name="Alex Lead",
            role=UserRole.ADMIN,
            is_active=True
        )
        self.db.add(self.lead_user)

        # Create Volunteer User
        self.vol_user = User(
            email="arjun@clubofai.org",
            hashed_password="hashed_vol_pw",
            full_name="Arjun Patel",
            role=UserRole.VOLUNTEER,
            is_active=True
        )
        self.db.add(self.vol_user)
        self.db.commit()
        self.db.refresh(self.lead_user)
        self.db.refresh(self.vol_user)

        # Create Volunteer Profile
        self.volunteer = Volunteer(
            user_id=self.vol_user.id,
            skills="Python, Event Management, Public Speaking",
            availability="Weekends, Evenings",
            status=VolunteerStatus.ACTIVE
        )
        self.db.add(self.volunteer)

        # Create Event
        self.event = Event(
            title="Spring AI Symposium 2026",
            description="Annual technical symposium on machine intelligence and robotics.",
            date=datetime.utcnow() + timedelta(days=14),
            venue="Auditorium Main Hall",
            budget=3500.0,
            expected_attendance=250,
            status=EventStatus.PUBLISHED,
            created_by=self.lead_user.id
        )
        self.db.add(self.event)
        self.db.commit()
        self.db.refresh(self.volunteer)
        self.db.refresh(self.event)

        # Create Tasks
        self.task1 = Task(
            event_id=self.event.id,
            title="Sponsorship Outreach",
            description="Contact tech sponsors and secure booth partnerships.",
            status=TaskStatus.TODO
        )
        self.task2 = Task(
            event_id=self.event.id,
            title="AV System Calibration",
            description="Calibrate microphones and stage projectors.",
            status=TaskStatus.DONE
        )
        self.db.add_all([self.task1, self.task2])
        self.db.commit()
        self.db.refresh(self.task1)
        self.db.refresh(self.task2)

        # Create Task Assignment for task2
        self.assignment = TaskAssignment(
            task_id=self.task2.id,
            volunteer_id=self.volunteer.id
        )
        self.db.add(self.assignment)

        # Create Announcement
        self.announcement = Announcement(
            event_id=self.event.id,
            created_by=self.lead_user.id,
            title="Symposium Registration Open",
            content="Registrations are now live on the student portal!",
            target_audience="all",
            status="PUBLISHED"
        )
        self.db.add(self.announcement)

        # Create Document
        self.doc = Document(
            event_id=self.event.id,
            name="Symposium_Budget_Breakdown.pdf",
            filename="budget.pdf",
            file_path="/uploads/docs/budget.pdf",
            file_type="application/pdf",
            file_size=1024,
            category="BUDGET",
            raw_text="The total approved budget for the Spring Symposium is $3500.",
            uploaded_by=self.lead_user.id
        )
        self.db.add(self.doc)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_get_event_context_tool(self):
        """Test get_event_context returns all event data, task status breakdown, volunteers, announcements, and docs in one payload."""
        result = context_tools.get_event_context.invoke({"event_id": self.event.id})
        self.assertNotIn("error", result)
        self.assertEqual(result["title"], "Spring AI Symposium 2026")
        self.assertEqual(result["budget"], 3500.0)
        self.assertEqual(result["venue"], "Auditorium Main Hall")
        
        # Verify task metrics breakdown
        task_metrics = result["task_metrics"]
        self.assertEqual(task_metrics["total_tasks"], 2)
        self.assertEqual(task_metrics["status_breakdown"]["TODO"], 1)
        self.assertEqual(task_metrics["status_breakdown"]["DONE"], 1)

        # Verify volunteers, announcements, and documents
        self.assertEqual(len(result["assigned_volunteers"]), 1)
        self.assertEqual(result["assigned_volunteers"][0]["id"], self.volunteer.id)
        self.assertEqual(len(result["recent_announcements"]), 1)
        self.assertEqual(result["recent_announcements"][0]["title"], "Symposium Registration Open")
        self.assertEqual(len(result["attached_documents"]), 1)
        self.assertEqual(result["attached_documents"][0]["name"], "Symposium_Budget_Breakdown.pdf")

    def test_get_task_context_tool(self):
        """Test get_task_context returns task info, event title, and assigned volunteers."""
        # Unassigned task
        res1 = context_tools.get_task_context.invoke({"task_id": self.task1.id})
        self.assertFalse(res1["is_assigned"])
        self.assertEqual(res1["title"], "Sponsorship Outreach")
        self.assertEqual(res1["event_title"], "Spring AI Symposium 2026")

        # Assigned task
        res2 = context_tools.get_task_context.invoke({"task_id": self.task2.id})
        self.assertTrue(res2["is_assigned"])
        self.assertEqual(len(res2["assigned_volunteers"]), 1)
        self.assertEqual(res2["assigned_volunteers"][0]["name"], "Arjun Patel")

    def test_get_volunteer_context_tool(self):
        """Test get_volunteer_context returns parsed skills, availability, and active vs completed workload."""
        res = context_tools.get_volunteer_context.invoke({"volunteer_id": self.volunteer.id})
        self.assertEqual(res["name"], "Arjun Patel")
        self.assertIn("Python", res["skills"])
        self.assertIn("Public Speaking", res["skills"])
        self.assertEqual(res["availability"], "Weekends, Evenings")
        
        # Workload metrics
        workload = res["workload"]
        self.assertEqual(workload["active_tasks_count"], 0)
        self.assertEqual(workload["completed_tasks_count"], 1)

    def test_get_project_summary_tool(self):
        """Test get_project_summary returns high-level metrics across the club operations."""
        summary = context_tools.get_project_summary.invoke({})
        self.assertEqual(summary["total_events"], 1)
        self.assertEqual(summary["total_tasks"], 2)
        self.assertEqual(summary["active_tasks"], 1)
        self.assertEqual(summary["completed_tasks"], 1)
        self.assertEqual(summary["completion_rate_percent"], 50.0)
        self.assertEqual(summary["active_volunteers"], 1)

    def test_search_tasks_tool(self):
        """Test search_tasks semantic and text filtering."""
        # Search by title keyword
        matches = context_tools.search_tasks.invoke({"query": "Sponsorship"})
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["title"], "Sponsorship Outreach")

        # Search with status filter
        done_matches = context_tools.search_tasks.invoke({"query": "", "status": "DONE"})
        self.assertEqual(len(done_matches), 1)
        self.assertEqual(done_matches[0]["title"], "AV System Calibration")

    def test_search_volunteers_tool(self):
        """Test search_volunteers by skill and name."""
        # Search by skill
        by_skill = context_tools.search_volunteers.invoke({"query": "Event Management"})
        self.assertEqual(len(by_skill), 1)
        self.assertEqual(by_skill[0]["name"], "Arjun Patel")

        # Search by name
        by_name = context_tools.search_volunteers.invoke({"query": "Arjun"})
        self.assertEqual(len(by_name), 1)
        self.assertEqual(by_name[0]["id"], self.volunteer.id)

    def test_search_event_data_tool(self):
        """Test search_event_data unified search across tasks, announcements, and documents."""
        res = context_tools.search_event_data.invoke({"query": "Symposium", "event_id": self.event.id})
        self.assertGreaterEqual(res["total_results"], 2)
        self.assertTrue(any("Registration" in a["title"] for a in res["announcements"]))
        self.assertTrue(any("Budget" in d["name"] for d in res["documents"]))

    def test_execute_command_unassigned_tasks_lifecycle(self):
        """
        Test Module 10 Natural Language Command workflow:
        'Assign all unowned tasks to Arjun'
        1. AI interprets command and retrieves context
        2. Staged proposal created with diff preview
        3. Requires confirmation (production state remains untouched)
        4. User confirms proposal -> changes applied to production + audit log created
        """
        # Step 1 & 2: Run natural language command
        cmd = f"Assign all unowned tasks to Arjun"
        resp = command_tool.execute_command.invoke({
            "command": cmd,
            "active_event_id": self.event.id,
            "user_id": self.lead_user.id
        })

        self.assertEqual(resp["status"], "AWAITING_CONFIRMATION")
        self.assertTrue(resp["requires_confirmation"])
        self.assertIn("diff_preview", resp)
        proposal_id = resp["proposal_id"]

        # Verify production state has NOT been altered yet!
        task1_fresh = self.db.query(Task).filter(Task.id == self.task1.id).first()
        self.assertEqual(len(task1_fresh.assignments), 0)

        # Step 3: Confirm and Apply Proposal
        confirm_resp = command_tool.execute_command.invoke({
            "command": f"Confirm proposal #{proposal_id}",
            "user_id": self.lead_user.id
        })
        self.assertEqual(confirm_resp["status"], "APPLIED")
        self.assertEqual(confirm_resp["proposal_id"], proposal_id)

        # Verify audit log was created
        audit_records = self.db.query(AuditLog).filter(AuditLog.proposal_id == proposal_id).all()
        self.assertGreaterEqual(len(audit_records), 1)

    def test_execute_command_planning_and_read_queries(self):
        """Test execute_command for event planning and read-only project summary queries."""
        # 1. Read-only query
        read_resp = command_tool.execute_command.invoke({
            "command": "Give me the project summary",
            "user_id": self.lead_user.id
        })
        self.assertEqual(read_resp["status"], "COMPLETED")
        self.assertEqual(read_resp["type"], "PROJECT_SUMMARY")
        self.assertIn("completion_rate_percent", read_resp["result"])

        # 2. Planning command
        plan_resp = command_tool.execute_command.invoke({
            "command": "Generate tasks for AI Winter Workshop",
            "user_id": self.lead_user.id
        })
        self.assertEqual(plan_resp["status"], "AWAITING_CONFIRMATION")
        self.assertIn("diff_preview", plan_resp)
    def test_execute_command_reject_and_undo(self):
        """Test reject and undo commands through natural language execution."""
        # 1. Create and Reject proposal
        cmd = f"Assign task {self.task1.id} to Arjun"
        stage_resp = command_tool.execute_command.invoke({
            "command": cmd,
            "user_id": self.lead_user.id
        })
        self.assertEqual(stage_resp["status"], "AWAITING_CONFIRMATION")
        pid1 = stage_resp["proposal_id"]

        reject_resp = command_tool.execute_command.invoke({
            "command": f"Reject proposal #{pid1}",
            "user_id": self.lead_user.id
        })
        self.assertEqual(reject_resp["status"], "REJECTED")

        # 2. Create, Apply, and Undo proposal
        auto_resp = command_tool.execute_command.invoke({
            "command": f"Assign task {self.task1.id} to Arjun",
            "user_id": self.lead_user.id,
            "auto_confirm": True
        })
        self.assertEqual(auto_resp["status"], "APPLIED")
        pid2 = auto_resp["proposal_id"]

        undo_resp = command_tool.execute_command.invoke({
            "command": f"Undo proposal #{pid2}",
            "user_id": self.lead_user.id
        })
        self.assertEqual(undo_resp["status"], "UNDONE")
        self.assertEqual(undo_resp["proposal_id"], pid2)

    def test_api_execute_ai_command_endpoint(self):
        """Test the FastAPI endpoint execute_ai_command (Module 12 architecture: API -> AI Tool -> Service -> DB)."""
        from app.api.endpoints.ai_commands import execute_ai_command, AICommandRequest

        req = AICommandRequest(
            command="Give me the project summary",
            active_event_id=self.event.id
        )
        api_resp = execute_ai_command(request=req, current_user=self.lead_user)
        self.assertEqual(api_resp.status, "COMPLETED")
        self.assertIn("Retrieved project summary", api_resp.response)
        self.assertIsNotNone(api_resp.details)


if __name__ == "__main__":
    unittest.main()

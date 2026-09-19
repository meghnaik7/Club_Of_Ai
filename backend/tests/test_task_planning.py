import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db.base
from app.db.base_class import Base
from app.models.user import User, UserRole
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.event import Event, EventStatus
from app.models.task import Task, TaskAssignment, TaskStatus

from ai.workflows import task_planning_engine
import ai.tools.task_planning_tools as planning_tools

class TestTaskPlanningModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # In-memory SQLite for testing
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)
        cls.original_session_local = task_planning_engine.SessionLocal
        task_planning_engine.SessionLocal = cls.TestingSessionLocal

    @classmethod
    def tearDownClass(cls):
        task_planning_engine.SessionLocal = cls.original_session_local
        Base.metadata.drop_all(bind=cls.engine)

    def setUp(self):
        self.db = self.TestingSessionLocal()
        # Create users
        self.user1 = User(
            email="tech_lead@clubofai.org",
            hashed_password="pw1",
            full_name="Sam Rivera",
            role=UserRole.ADMIN,
            is_active=True
        )
        self.user2 = User(
            email="designer@clubofai.org",
            hashed_password="pw2",
            full_name="Dana Scully",
            role=UserRole.ADMIN,
            is_active=True
        )
        self.db.add_all([self.user1, self.user2])
        self.db.commit()
        self.db.refresh(self.user1)
        self.db.refresh(self.user2)

        # Create volunteers with specific skills
        self.vol1 = Volunteer(
            user_id=self.user1.id,
            skills="Audio/Visual, Technical Setup, Python",
            availability="Weekends, Evenings",
            status=VolunteerStatus.ACTIVE
        )
        self.vol2 = Volunteer(
            user_id=self.user2.id,
            skills="Graphic Design, Social Media, Copywriting",
            availability="Weekdays",
            status=VolunteerStatus.ACTIVE
        )
        self.db.add_all([self.vol1, self.vol2])
        self.db.commit()
        self.db.refresh(self.vol1)
        self.db.refresh(self.vol2)

        # Create event
        self.event = Event(
            title="Spring AI Symposium",
            description="A student AI conference with keynote speakers and workshops.",
            date=datetime.utcnow() + timedelta(days=20),
            venue="Auditorium Main",
            created_by=self.user1.id
        )
        self.db.add(self.event)
        self.db.commit()
        self.db.refresh(self.event)

    def tearDown(self):
        self.db.query(TaskAssignment).delete()
        self.db.query(Task).delete()
        self.db.query(Volunteer).delete()
        self.db.query(Event).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_generate_task_graph(self):
        """Test task graph generation from event brief."""
        graph = task_planning_engine.generate_task_graph(
            event_brief="Organize an AI Robotics Expo with 150 student attendees and 10 demo booths.",
            event_id=self.event.id
        )
        self.assertIn("tasks", graph)
        self.assertGreaterEqual(len(graph["tasks"]), 4)
        
        phases = {t["phase"] for t in graph["tasks"]}
        self.assertIn("PRE_EVENT", phases)
        self.assertIn("DAY_OF", phases)
        self.assertIn("POST_EVENT", phases)

        # Verify task schema completeness
        first_task = graph["tasks"][0]
        self.assertIn("title", first_task)
        self.assertIn("estimated_duration_hours", first_task)
        self.assertIn("subtasks", first_task)
        self.assertIn("dependencies", first_task)

    def test_split_task(self):
        """Test splitting a large task into smaller executable subtasks."""
        result = task_planning_engine.split_task(
            task_title="Coordinate Guest Speakers and Panelists",
            task_description="Invite 3 industry experts, book travel accommodations, and prep moderation questions.",
            num_subtasks=3,
            total_duration_hours=9
        )
        self.assertEqual(result["parent_task_title"], "Coordinate Guest Speakers and Panelists")
        self.assertEqual(len(result["subtasks"]), 3)
        self.assertEqual(result["subtasks"][1]["depends_on_subtask_index"], 0)
        self.assertIn("title", result["subtasks"][0])
        self.assertIn("suggested_skills", result["subtasks"][0])

    def test_suggest_task_owner(self):
        """Test recommending volunteers based on skill match and workload."""
        # 1. Test recommending AV specialist
        av_recs = task_planning_engine.suggest_task_owner(
            task_title="Setup Audio and Microphones for Stage",
            task_skills=["Audio/Visual", "Technical Setup"],
            db=self.db
        )
        self.assertGreaterEqual(len(av_recs["recommendations"]), 1)
        top_av = av_recs["recommendations"][0]
        self.assertEqual(top_av["volunteer_id"], self.vol1.id)
        self.assertEqual(top_av["name"], "Sam Rivera")

        # 2. Test recommending Graphic Designer
        design_recs = task_planning_engine.suggest_task_owner(
            task_title="Design Promotional Instagram Posters",
            task_skills=["Graphic Design", "Social Media"],
            db=self.db
        )
        top_design = design_recs["recommendations"][0]
        self.assertEqual(top_design["volunteer_id"], self.vol2.id)
        self.assertEqual(top_design["name"], "Dana Scully")

    def test_reschedule_task_and_clash_detection(self):
        """Test rescheduling task and verifying dependency clash checking."""
        sample_tasks = [
            {
                "id": 1,
                "title": "Task 1: Book Venue",
                "start_date": "2026-10-01 09:00:00",
                "deadline": "2026-10-03 17:00:00",
                "dependencies": []
            },
            {
                "id": 2,
                "title": "Task 2: Setup Stage",
                "start_date": "2026-10-04 09:00:00",
                "deadline": "2026-10-05 17:00:00",
                "dependencies": [1]
            }
        ]

        # Valid reschedule: Task 2 moved forward to Oct 6
        valid_res = task_planning_engine.reschedule_task(
            task_id=2,
            new_start_date="2026-10-06 09:00:00",
            new_deadline="2026-10-07 17:00:00",
            tasks_data=sample_tasks
        )
        self.assertTrue(valid_res["is_valid"])
        self.assertEqual(len(valid_res["conflicts_detected"]), 0)

        # Invalid reschedule: Task 2 moved to Oct 2 (before prerequisite Task 1 deadline on Oct 3!)
        invalid_res = task_planning_engine.reschedule_task(
            task_id=2,
            new_start_date="2026-10-02 09:00:00",
            new_deadline="2026-10-04 17:00:00",
            tasks_data=sample_tasks
        )
        self.assertFalse(invalid_res["is_valid"])
        self.assertGreater(len(invalid_res["conflicts_detected"]), 0)
        self.assertIn("finishes after new start date", invalid_res["conflicts_detected"][0]["conflict"])

    def test_cascade_reschedule(self):
        """Test cascading downstream shifts across dependent tasks."""
        sample_tasks = [
            {
                "id": 1,
                "title": "Task 1",
                "start_date": "2026-10-01 09:00:00",
                "deadline": "2026-10-02 17:00:00",
                "dependencies": []
            },
            {
                "id": 2,
                "title": "Task 2",
                "start_date": "2026-10-03 09:00:00",
                "deadline": "2026-10-04 17:00:00",
                "dependencies": [1]
            },
            {
                "id": 3,
                "title": "Task 3",
                "start_date": "2026-10-05 09:00:00",
                "deadline": "2026-10-06 17:00:00",
                "dependencies": [2]
            }
        ]

        # Shift Task 1 by 48 hours (2 days)
        res = task_planning_engine.cascade_reschedule(
            task_id=1,
            time_shift_hours=48,
            tasks_data=sample_tasks
        )

        self.assertEqual(res["total_tasks_affected"], 2)
        shifted_ids = [t["task_id"] for t in res["shifted_tasks"]]
        self.assertIn(2, shifted_ids)
        self.assertIn(3, shifted_ids)

        # Check shifted task 2 new start date
        t2_shifted = next(t for t in res["shifted_tasks"] if t["task_id"] == 2)
        self.assertEqual(t2_shifted["new_start"], "2026-10-05 09:00:00")

    def test_detect_dependency_conflicts(self):
        """Test detecting circular dependencies, date conflicts, and blocked chains."""
        # 1. Circular dependency test
        circular_tasks = [
            {"id": "A", "title": "Task A", "dependencies": ["B"]},
            {"id": "B", "title": "Task B", "dependencies": ["C"]},
            {"id": "C", "title": "Task C", "dependencies": ["A"]}
        ]
        conflicts_circ = task_planning_engine.detect_dependency_conflicts(circular_tasks)
        self.assertTrue(conflicts_circ["has_conflicts"])
        types = [c["type"] for c in conflicts_circ["conflicts"]]
        self.assertIn("CIRCULAR_DEPENDENCY", types)

        # 2. Date conflict test
        date_conflict_tasks = [
            {
                "id": 1,
                "title": "Prep Assets",
                "start_date": "2026-10-01 09:00:00",
                "deadline": "2026-10-05 17:00:00",
                "dependencies": []
            },
            {
                "id": 2,
                "title": "Print Flyers",
                "start_date": "2026-10-03 09:00:00",  # Starts BEFORE task 1 deadline!
                "deadline": "2026-10-06 17:00:00",
                "dependencies": [1]
            }
        ]
        conflicts_date = task_planning_engine.detect_dependency_conflicts(date_conflict_tasks)
        self.assertTrue(conflicts_date["has_conflicts"])
        types_date = [c["type"] for c in conflicts_date["conflicts"]]
        self.assertIn("DATE_CONFLICT", types_date)

        # 3. Blocked chain test
        blocked_tasks = [
            {"id": 1, "title": "Permits", "status": "BLOCKED", "dependencies": []},
            {"id": 2, "title": "Build Stage", "status": "TODO", "dependencies": [1]}
        ]
        conflicts_blocked = task_planning_engine.detect_dependency_conflicts(blocked_tasks)
        self.assertTrue(conflicts_blocked["has_conflicts"])
        types_blocked = [c["type"] for c in conflicts_blocked["conflicts"]]
        self.assertIn("BLOCKED_CHAIN", types_blocked)

    def test_explain_dependency_conflict(self):
        """Test translating dependency deadlocks into plain language explanations."""
        conflict_sample = {
            "type": "CIRCULAR_DEPENDENCY",
            "cycle": ["Task A", "Task B", "Task C", "Task A"],
            "details": "Circular dependency detected: Task A -> Task B -> Task C -> Task A"
        }
        explanation = task_planning_engine.explain_dependency_conflict(conflict_sample)
        self.assertIn("summary", explanation)
        self.assertIn("cause", explanation)
        self.assertIn("impact", explanation)
        self.assertIn("recommended_resolutions", explanation)
        self.assertGreaterEqual(len(explanation["recommended_resolutions"]), 1)

    def test_langchain_tools_invocation(self):
        """Test invoking all 7 LangChain tools via .invoke()."""
        # 1. generate_task_graph tool
        g_res = planning_tools.generate_task_graph.invoke({"event_brief": "Hackathon event"})
        self.assertIn("tasks", g_res)

        # 2. split_task tool
        s_res = planning_tools.split_task.invoke({"task_title": "Setup Catering"})
        self.assertIn("subtasks", s_res)

        # 3. suggest_task_owner tool
        o_res = planning_tools.suggest_task_owner.invoke({"task_title": "Audio Visual Support"})
        self.assertIn("recommendations", o_res)

        # 4. reschedule_task tool
        r_res = planning_tools.reschedule_task.invoke({
            "task_id": 1,
            "new_start_date": "2026-10-01 10:00:00",
            "new_deadline": "2026-10-01 14:00:00"
        })
        self.assertIn("is_valid", r_res)

        # 5. cascade_reschedule tool
        c_res = planning_tools.cascade_reschedule.invoke({
            "task_id": 1,
            "time_shift_hours": 24,
            "tasks_data": [
                {"id": 1, "dependencies": []},
                {"id": 2, "dependencies": [1]}
            ]
        })
        self.assertIn("shifted_tasks", c_res)

        # 6. detect_dependency_conflicts tool
        d_res = planning_tools.detect_dependency_conflicts.invoke({
            "tasks_data": [
                {"id": 1, "dependencies": [2]},
                {"id": 2, "dependencies": [1]}
            ]
        })
        self.assertTrue(d_res["has_conflicts"])

        # 7. explain_dependency_conflict tool
        e_res = planning_tools.explain_dependency_conflict.invoke({
            "conflict_data": {"type": "DATE_CONFLICT", "details": "Clash between task 1 and 2"}
        })
        self.assertIn("summary", e_res)

if __name__ == "__main__":
    unittest.main()

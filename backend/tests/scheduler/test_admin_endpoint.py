import unittest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.api import deps
from tests.scheduler.test_base import BaseSchedulerTestCase
from app.models.task import Task, TaskStatus, TaskAssignment


class TestAdminSchedulerEndpoint(BaseSchedulerTestCase):
    def setUp(self):
        super().setUp()
        self.client = TestClient(app)

    def test_admin_trigger_check_overdue_tasks_success(self):
        """Admin user can trigger manual check-overdue-tasks execution."""
        task = Task(
            title="Coordinate Judges",
            event_id=self.event.id,
            team_id=self.team.id,
            status=TaskStatus.IN_PROGRESS,
            due_date=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(TaskAssignment(task_id=task.id, volunteer_id=self.vol.id))
        self.db.commit()

        def override_get_db():
            yield self.db

        app.dependency_overrides[deps.get_db] = override_get_db
        app.dependency_overrides[deps.get_current_user] = lambda: self.admin

        try:
            response = self.client.post("/api/v1/admin/scheduler/check-overdue-tasks")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
            self.assertIn("summary", data)
            self.assertEqual(data["summary"]["team_leads_notified"], 1)
        finally:
            app.dependency_overrides.clear()

    def test_non_admin_forbidden(self):
        """Non-admin user (e.g. Volunteer) cannot trigger check-overdue-tasks endpoint."""
        def override_get_db():
            yield self.db

        app.dependency_overrides[deps.get_db] = override_get_db
        app.dependency_overrides[deps.get_current_user] = lambda: self.vol_user

        try:
            response = self.client.post("/api/v1/admin/scheduler/check-overdue-tasks")
            self.assertEqual(response.status_code, 403)
        finally:
            app.dependency_overrides.clear()

    def test_admin_view_scheduler_status(self):
        """Admin user can view scheduler status."""
        def override_get_db():
            yield self.db

        app.dependency_overrides[deps.get_db] = override_get_db
        app.dependency_overrides[deps.get_current_user] = lambda: self.admin

        try:
            response = self.client.get("/api/v1/admin/scheduler/status")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
            self.assertIn("scheduler", data)
            self.assertEqual(data["scheduler"]["interval_minutes"], 240)
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()

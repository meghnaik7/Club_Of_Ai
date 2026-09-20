import os
import sys
import uuid
from datetime import datetime, timedelta

# Ensure backend directory is on python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), 'clubops.db'))}"

from app.db.base import Base
from app.db.session import engine, SessionLocal
Base.metadata.create_all(bind=engine)

from app.models.user import User
from app.models.event import Event
from app.models.task import Task
from app.schemas.task import TaskCreate
from app.services.task_service import task_service

from app.ai.tools.volunteer_tools import (
    create_volunteer,
    get_volunteer,
    list_volunteers,
    update_volunteer,
    delete_volunteer,
    get_volunteer_tasks,
    tool_calculate_volunteer_load,
    get_overloaded_volunteers,
    suggest_task_owner,
    bulk_reassign_tasks
)
from app.ai.tools import ALL_AI_TOOLS


def run_tests():
    print("=" * 60)
    print("RUNNING UNIT TESTS FOR VOLUNTEER TOOLS (10 TOOLS)")
    print("=" * 60)

    # Test 0: Verify Catalog
    print("\n[Test 0] Checking Tool Registry...")
    assert len(ALL_AI_TOOLS) == 58, f"Expected 58 tools, got {len(ALL_AI_TOOLS)}"
    print(f"[OK] Tool registry has {len(ALL_AI_TOOLS)} tools registered in ALL_AI_TOOLS!")

    db = SessionLocal()
    suffix = uuid.uuid4().hex[:6]

    # Create users
    u1 = User(email=f"rohit.{suffix}@college.edu", full_name="Rohit Verma", hashed_password="pw")
    u2 = User(email=f"neha.{suffix}@college.edu", full_name="Neha Sharma", hashed_password="pw")
    u3 = User(email=f"temp.{suffix}@college.edu", full_name="Temp Volunteer", hashed_password="pw")
    db.add_all([u1, u2, u3])
    db.commit()

    u1_id = u1.id
    u2_id = u2.id
    u3_id = u3.id

    # Create Event for task assignments
    event = Event(
        title=f"Volunteer Conclave {suffix}",
        description="Testing volunteer tools",
        date=datetime.now() + timedelta(days=20),
        venue="Auditorium",
        budget=5000.0,
        expected_attendance=300
    )
    db.add(event)
    db.commit()
    event_id = event.id
    db.close()

    # 1. create_volunteer
    print("\n[Test 1] Testing create_volunteer...")
    v1_res = create_volunteer(user_id=u1_id, skills="Logistics, Stage Management", availability="Weekends", max_capacity=10)
    assert v1_res["success"], f"create_volunteer failed: {v1_res}"
    v1_id = v1_res["volunteer_id"]

    v2_res = create_volunteer(user_id=u2_id, skills="Design, Marketing", availability="Weekdays", max_capacity=10)
    assert v2_res["success"]
    v2_id = v2_res["volunteer_id"]

    v3_res = create_volunteer(user_id=u3_id, skills="General", availability="Flexible", max_capacity=5)
    assert v3_res["success"]
    v3_id = v3_res["volunteer_id"]
    print(f"[OK] Volunteers created: v1={v1_id}, v2={v2_id}, temp_v3={v3_id}")

    # 2. get_volunteer
    print("\n[Test 2] Testing get_volunteer...")
    v_get = get_volunteer(v1_id)
    assert v_get["success"]
    assert "Logistics" in v_get["volunteer"]["skills"]
    assert "load" in v_get["volunteer"]
    print(f"[OK] Retrieved volunteer profile with load metrics: {v_get['volunteer']['skills']}.")

    # 3. list_volunteers
    print("\n[Test 3] Testing list_volunteers...")
    v_list = list_volunteers(status="ACTIVE")
    assert v_list["success"]
    assert len(v_list["volunteers"]) >= 3
    print(f"[OK] list_volunteers returned {len(v_list['volunteers'])} active volunteers.")

    # 4. update_volunteer
    print("\n[Test 4] Testing update_volunteer...")
    up_res = update_volunteer(volunteer_id=v1_id, skills="Logistics, AV Production, Audio", max_capacity=12)
    assert up_res["success"]
    v_updated = get_volunteer(v1_id)
    assert "AV Production" in v_updated["volunteer"]["skills"]
    print("[OK] Updated volunteer skills and max capacity.")

    # Setup tasks for workload and reassignment testing
    db = SessionLocal()
    task_in1 = TaskCreate(title="AV Setup", event_id=event_id, owner_ids=[v1_id])
    task_in2 = TaskCreate(title="Stage Lighting", event_id=event_id, owner_ids=[v1_id])
    t1 = task_service.create_task(db, task_in1)
    t2 = task_service.create_task(db, task_in2)
    t1_id = t1.id
    t2_id = t2.id
    db.close()

    # 5. get_volunteer_tasks
    print("\n[Test 5] Testing get_volunteer_tasks...")
    tasks_res = get_volunteer_tasks(volunteer_id=v1_id)
    assert tasks_res["success"]
    assert len(tasks_res["tasks"]) == 2
    print(f"[OK] Retrieved {len(tasks_res['tasks'])} tasks assigned to volunteer #{v1_id}.")

    # 6. tool_calculate_volunteer_load
    print("\n[Test 6] Testing tool_calculate_volunteer_load...")
    load_res = tool_calculate_volunteer_load(volunteer_id=v1_id)
    assert load_res["success"]
    assert "utilization_percent" in load_res["load"]
    print(f"[OK] Calculated workload utilization: {load_res['load']['utilization_percent']}% ({load_res['load']['status']}).")

    # 7. get_overloaded_volunteers
    print("\n[Test 7] Testing get_overloaded_volunteers...")
    overloaded_res = get_overloaded_volunteers()
    assert overloaded_res["success"]
    print(f"[OK] Scanned overloaded volunteers ({len(overloaded_res['overloaded_volunteers'])} found).")

    # 8. suggest_task_owner
    print("\n[Test 8] Testing suggest_task_owner...")
    sugg_res = suggest_task_owner(task_id=t1_id)
    assert sugg_res["success"]
    assert "suggestions" in sugg_res
    print(f"[OK] suggest_task_owner returned candidate suggestions: {len(sugg_res['suggestions'])} candidates.")

    # 9. bulk_reassign_tasks
    print("\n[Test 9] Testing bulk_reassign_tasks...")
    reassign_res = bulk_reassign_tasks(from_volunteer_id=v1_id, to_volunteer_id=v2_id)
    assert reassign_res["success"]
    assert reassign_res["reassigned_count"] == 2
    
    # Verify tasks now belong to v2
    v1_remaining = get_volunteer_tasks(volunteer_id=v1_id)
    v2_now = get_volunteer_tasks(volunteer_id=v2_id)
    assert len(v1_remaining["tasks"]) == 0
    assert len(v2_now["tasks"]) == 2
    print(f"[OK] bulk_reassign_tasks moved 2 tasks from volunteer #{v1_id} to #{v2_id}.")

    # 10. delete_volunteer
    print("\n[Test 10] Testing delete_volunteer...")
    del_res = delete_volunteer(volunteer_id=v3_id)
    assert del_res["success"]
    assert not get_volunteer(v3_id)["success"]
    print(f"[OK] delete_volunteer cleanly removed disposable volunteer #{v3_id}.")

    print("\n" + "=" * 60)
    print("ALL 10 VOLUNTEER TOOLS VERIFIED AND PASSING SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()

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
from app.models.volunteer import Volunteer
from app.models.event import Event
from app.models.task import Task

from app.ai.tools.task_tools import (
    create_task,
    get_task,
    list_tasks,
    update_task,
    delete_task,
    assign_task,
    unassign_task,
    change_task_status,
    create_subtask,
    list_subtasks,
    add_task_dependency,
    remove_task_dependency,
    get_task_dependencies,
    add_task_comment,
    get_task_activity,
    bulk_update_tasks,
    tool_calculate_critical_path,
    get_overdue_tasks
)
from app.ai.tools import ALL_AI_TOOLS


def run_tests():
    print("=" * 60)
    print("RUNNING UNIT TESTS FOR TASK TOOLS (18 TOOLS)")
    print("=" * 60)

    # Test 0: Verify Catalog
    print("\n[Test 0] Checking Tool Registry...")
    assert len(ALL_AI_TOOLS) == 58, f"Expected 58 tools, got {len(ALL_AI_TOOLS)}"
    print(f"[OK] Tool registry has {len(ALL_AI_TOOLS)} tools registered in ALL_AI_TOOLS!")

    db = SessionLocal()
    suffix = uuid.uuid4().hex[:6]

    # Prerequisite Event & Volunteer
    user = User(email=f"tasklead.{suffix}@college.edu", full_name="Task Lead", hashed_password="pw")
    db.add(user)
    db.commit()

    vol = Volunteer(user_id=user.id, skills="Operations, Planning", max_capacity=10)
    event = Event(
        title=f"Task Conclave {suffix}",
        description="Testing task tools",
        date=datetime.now() + timedelta(days=15),
        venue="Hall A",
        budget=4000.0,
        expected_attendance=200
    )
    db.add_all([vol, event])
    db.commit()
    user_id = user.id
    event_id = event.id
    vol_id = vol.id
    db.close()

    # 1. create_task
    print("\n[Test 1] Testing create_task...")
    due_1 = (datetime.now() + timedelta(days=5)).isoformat()
    t1_res = create_task(
        title="Setup Stage Lighting",
        event_id=event_id,
        description="Install floodlights and DMX console",
        priority="HIGH",
        status="TODO",
        phase="PLANNING",
        due_date=due_1,
        owner_ids=[vol_id]
    )
    assert t1_res["success"], f"create_task failed: {t1_res}"
    t1_id = t1_res["task_id"]
    print(f"[OK] Task created with ID: {t1_id}")

    due_2 = (datetime.now() + timedelta(days=7)).isoformat()
    t2_res = create_task(
        title="Sound Check and Rehearsal",
        event_id=event_id,
        priority="MEDIUM",
        status="TODO",
        due_date=due_2
    )
    assert t2_res["success"]
    t2_id = t2_res["task_id"]

    # 2. get_task
    print("\n[Test 2] Testing get_task...")
    t_get = get_task(t1_id)
    assert t_get["success"]
    assert t_get["task"]["title"] == "Setup Stage Lighting"
    assert vol_id in t_get["task"]["assignments"]
    print(f"[OK] Retrieved task '{t_get['task']['title']}' with verified assignment.")

    # 3. list_tasks
    print("\n[Test 3] Testing list_tasks...")
    tasks_list = list_tasks(event_id=event_id)
    assert tasks_list["success"]
    assert len(tasks_list["tasks"]) >= 2
    print(f"[OK] list_tasks returned {len(tasks_list['tasks'])} task(s) for event {event_id}.")

    # 4. update_task
    print("\n[Test 4] Testing update_task...")
    up_res = update_task(task_id=t1_id, title="Setup Stage Lighting & Visuals", priority="URGENT")
    assert up_res["success"]
    print("[OK] Task updated title and priority to URGENT.")

    # 5. change_task_status
    print("\n[Test 5] Testing change_task_status...")
    st_res = change_task_status(task_id=t1_id, status="IN_PROGRESS")
    assert st_res["success"]
    t_check = get_task(t1_id)
    assert t_check["task"]["status"] == "IN_PROGRESS"
    print("[OK] Task status successfully changed to IN_PROGRESS.")

    # 6. assign_task
    print("\n[Test 6] Testing assign_task...")
    as_res = assign_task(task_id=t2_id, volunteer_ids=[vol_id])
    assert as_res["success"]
    print(f"[OK] Assigned volunteer #{vol_id} to task #{t2_id}.")

    # 7. unassign_task
    print("\n[Test 7] Testing unassign_task...")
    unas_res = unassign_task(task_id=t2_id, volunteer_ids=[vol_id])
    assert unas_res["success"]
    print(f"[OK] Unassigned volunteer #{vol_id} from task #{t2_id}.")

    # 8. create_subtask
    print("\n[Test 8] Testing create_subtask...")
    sub_res = create_subtask(parent_id=t1_id, title="Run Power Extension Cables", event_id=event_id)
    assert sub_res["success"]
    sub_id = sub_res["task_id"]
    print(f"[OK] Created subtask #{sub_id} under parent task #{t1_id}.")

    # 9. list_subtasks
    print("\n[Test 9] Testing list_subtasks...")
    subs = list_subtasks(parent_id=t1_id)
    assert subs["success"]
    assert len(subs["subtasks"]) >= 1
    print(f"[OK] list_subtasks returned {len(subs['subtasks'])} subtask(s).")

    # 10. add_task_dependency
    print("\n[Test 10] Testing add_task_dependency...")
    dep_res = add_task_dependency(dependent_task_id=t2_id, prerequisite_task_id=t1_id)
    assert dep_res["success"]
    print(f"[OK] Added dependency: Task #{t2_id} depends on Task #{t1_id}.")

    # 11. get_task_dependencies
    print("\n[Test 11] Testing get_task_dependencies...")
    deps = get_task_dependencies(task_id=t2_id)
    assert deps["success"]
    assert any(b["id"] == t1_id for b in deps["blocked_by"])
    print(f"[OK] Verified Task #{t2_id} is blocked by Task #{t1_id}.")

    # 12. remove_task_dependency
    print("\n[Test 12] Testing remove_task_dependency...")
    rm_dep = remove_task_dependency(dependent_task_id=t2_id, prerequisite_task_id=t1_id)
    assert rm_dep["success"]
    print("[OK] Successfully removed dependency.")

    # 13. add_task_comment
    print("\n[Test 13] Testing add_task_comment...")
    cmt_res = add_task_comment(task_id=t1_id, user_id=user_id, content="Extension cables acquired from AV lab.")
    assert cmt_res["success"]
    print("[OK] Task comment added.")

    # 14. get_task_activity
    print("\n[Test 14] Testing get_task_activity...")
    act_res = get_task_activity(task_id=t1_id)
    assert act_res["success"]
    assert len(act_res["activity"]) >= 1
    print(f"[OK] Retrieved {len(act_res['activity'])} activity record(s).")

    # 15. bulk_update_tasks
    print("\n[Test 15] Testing bulk_update_tasks...")
    bulk_res = bulk_update_tasks(task_ids=[t1_id, t2_id], priority="URGENT")
    assert bulk_res["success"]
    print(f"[OK] bulk_update_tasks updated tasks to URGENT.")

    # 16. tool_calculate_critical_path
    print("\n[Test 16] Testing tool_calculate_critical_path...")
    # Re-add dependency for critical path
    add_task_dependency(dependent_task_id=t2_id, prerequisite_task_id=t1_id)
    cp_res = tool_calculate_critical_path(event_id=event_id)
    assert cp_res["success"]
    print(f"[OK] Critical path calculated successfully: {cp_res.get('critical_path', [])}")

    # 17. get_overdue_tasks
    print("\n[Test 17] Testing get_overdue_tasks...")
    # Create overdue task
    past_due = (datetime.now() - timedelta(days=2)).isoformat()
    t_overdue = create_task(title="Past Deadline Task", event_id=event_id, due_date=past_due)
    assert t_overdue["success"]
    overdue_res = get_overdue_tasks(event_id=event_id)
    assert overdue_res["success"]
    assert any(t["id"] == t_overdue["task_id"] for t in overdue_res["tasks"])
    print(f"[OK] get_overdue_tasks identified overdue task #{t_overdue['task_id']}.")

    # 18. delete_task
    print("\n[Test 18] Testing delete_task...")
    del_res = delete_task(task_id=t_overdue["task_id"])
    assert del_res["success"]
    assert not get_task(t_overdue["task_id"])["success"]
    print(f"[OK] delete_task cleanly deleted task #{t_overdue['task_id']}.")

    print("\n" + "=" * 60)
    print("ALL 18 TASK TOOLS VERIFIED AND PASSING SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()

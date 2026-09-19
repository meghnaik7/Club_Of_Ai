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
from app.models.meeting import Meeting
from app.models.risk import EventRisk

# AI Tools Central Registry
from app.ai.tools import ALL_AI_TOOLS


def run_master_test_suite():
    print("=" * 75)
    print("CLUBOPS AI - MASTER VERIFICATION SUITE FOR ALL 5 MODULES (58 TOOLS)")
    print("=" * 75)

    # -------------------------------------------------------------
    # SECTION 0: Catalog Integrity Check
    # -------------------------------------------------------------
    print("\n[SECTION 0] Validating Central Tool Catalog...")
    assert len(ALL_AI_TOOLS) == 58, f"Expected 58 registered tools, found {len(ALL_AI_TOOLS)}"
    print(f"[OK] ALL_AI_TOOLS catalog validated: exactly {len(ALL_AI_TOOLS)} tools active.")

    db = SessionLocal()
    suffix = uuid.uuid4().hex[:6]

    # Create users for volunteers
    u1 = User(email=f"ananya.{suffix}@college.edu", full_name="Ananya Roy", hashed_password="pw")
    u2 = User(email=f"vikram.{suffix}@college.edu", full_name="Vikram Seth", hashed_password="pw")
    u_disp = User(email=f"disp.{suffix}@college.edu", full_name="Disposable Volunteer", hashed_password="pw")
    db.add_all([u1, u2, u_disp])
    db.commit()
    u1_id = u1.id
    u2_id = u2.id
    u_disp_user_id = u_disp.id
    db.close()

    # =============================================================
    # MODULE 3: EVENT TOOLS (11 TOOLS)
    # =============================================================
    print("\n" + "=" * 60)
    print("TESTING MODULE 3: EVENT TOOLS (11 TOOLS)")
    print("=" * 60)

    # 1. create_event
    print(" 1. Testing 'create_event'...")
    res = ALL_AI_TOOLS["create_event"](
        name=f"AI Grand Conclave {suffix}",
        date=(datetime.now() + timedelta(days=22)).isoformat(),
        venue="Main Auditorium",
        budget=7500.0,
        expected_attendance=200,
        description="Flagship annual technical summit featuring industry keynotes."
    )
    assert res["success"] is True, f"Failed create_event: {res}"
    event_id = res["event_id"]
    print(f"    -> [OK] Event created: ID #{event_id}")

    # 2. get_event
    print(" 2. Testing 'get_event'...")
    res = ALL_AI_TOOLS["get_event"](event_id=event_id)
    assert res["success"] is True
    assert res["event"]["budget"] == 7500.0
    print(f"    -> [OK] Retrieved event: '{res['event']['title']}'")

    # 3. list_events
    print(" 3. Testing 'list_events'...")
    res = ALL_AI_TOOLS["list_events"]()
    assert res["success"] is True
    assert any(e["id"] == event_id for e in res["events"])
    print(f"    -> [OK] list_events returned {res['count']} event(s)")

    # 4. update_event
    print(" 4. Testing 'update_event'...")
    res = ALL_AI_TOOLS["update_event"](event_id=event_id, venue="Main Auditorium & Exhibition Hall")
    assert res["success"] is True
    assert res["venue"] == "Main Auditorium & Exhibition Hall"
    print("    -> [OK] update_event updated venue successfully")

    # 5. update_budget_allocation
    print(" 5. Testing 'update_budget_allocation'...")
    res = ALL_AI_TOOLS["update_budget_allocation"](
        event_id=event_id,
        category_allocations={"Venue": 3000.0, "Catering": 2500.0, "Guest Speaker": 2000.0}
    )
    assert res["success"] is True
    cat_names = [c["name"] for c in res["categories"]]
    print(f"    -> [OK] Budget categories allocated: {cat_names}")

    # 6. record_expense
    print(" 6. Testing 'record_expense'...")
    res = ALL_AI_TOOLS["record_expense"](
        event_id=event_id,
        category="Catering",
        amount=520.0,
        description="Advance for lunch boxes and beverages",
        recorded_by="Treasurer"
    )
    assert res["success"] is True
    print(f"    -> [OK] Expense recorded: ${res['amount']}")

    # 7. get_event_budget
    print(" 7. Testing 'get_event_budget'...")
    res = ALL_AI_TOOLS["get_event_budget"](event_id=event_id)
    assert res["success"] is True
    assert res["budget_summary"]["total_spent"] == 520.0
    print(f"    -> [OK] Confirmed spent budget: ${res['budget_summary']['total_spent']}")

    # 8. generate_event_plan
    print(" 8. Testing 'generate_event_plan' (Club Memory powered)...")
    res = ALL_AI_TOOLS["generate_event_plan"](
        event_brief="Annual campus hackathon with 200 participants focusing on autonomous AI agents and web dev.",
        event_title=f"Autonomous Agent Sprint {suffix}",
        estimated_budget=4000.0,
        target_date=(datetime.now() + timedelta(days=18)).isoformat()
    )
    assert res["success"] is True
    assert len(res["plan"]["phases"]) >= 3
    print(f"    -> [OK] Plan generated with {len(res['plan']['phases'])} operational phases")

    # 9. get_event_timeline
    print(" 9. Testing 'get_event_timeline'...")
    res = ALL_AI_TOOLS["get_event_timeline"](event_id=event_id)
    assert res["success"] is True
    print(f"    -> [OK] Timeline loaded with {len(res['timeline'])} task nodes")

    # 10. get_event_dashboard
    print("10. Testing 'get_event_dashboard'...")
    res = ALL_AI_TOOLS["get_event_dashboard"](event_id=event_id)
    assert res["success"] is True
    assert "task_stats" in res["dashboard"]
    print("    -> [OK] Dashboard metrics retrieved")

    # 11. delete_event
    print("11. Testing 'delete_event'...")
    disp_ev = ALL_AI_TOOLS["create_event"](name=f"Temp Event {suffix}", date=(datetime.now() + timedelta(days=1)).isoformat())
    res = ALL_AI_TOOLS["delete_event"](event_id=disp_ev["event_id"])
    assert res["success"] is True
    print(f"    -> [OK] Temporary event #{disp_ev['event_id']} deleted successfully")


    # =============================================================
    # MODULE 2: VOLUNTEER TOOLS (10 TOOLS)
    # =============================================================
    print("\n" + "=" * 60)
    print("TESTING MODULE 2: VOLUNTEER TOOLS (10 TOOLS)")
    print("=" * 60)

    # 1. create_volunteer
    print(" 1. Testing 'create_volunteer'...")
    res_v1 = ALL_AI_TOOLS["create_volunteer"](user_id=u1_id, skills="Design, Marketing, Social Media", max_capacity=5)
    assert res_v1["success"] is True
    v1_id = res_v1["volunteer_id"]

    res_v2 = ALL_AI_TOOLS["create_volunteer"](user_id=u2_id, skills="Audio, Lighting, Logistics", max_capacity=6)
    assert res_v2["success"] is True
    v2_id = res_v2["volunteer_id"]

    res_v_disp = ALL_AI_TOOLS["create_volunteer"](user_id=u_disp_user_id, skills="General Support", max_capacity=2)
    assert res_v_disp["success"] is True
    v_disp_id = res_v_disp["volunteer_id"]
    print(f"    -> [OK] Volunteers created: v1={v1_id}, v2={v2_id}, disposable={v_disp_id}")

    # 2. get_volunteer
    print(" 2. Testing 'get_volunteer'...")
    res = ALL_AI_TOOLS["get_volunteer"](volunteer_id=v1_id)
    assert res["success"] is True
    assert "Design" in res["volunteer"]["skills"]
    print(f"    -> [OK] Retrieved volunteer #{v1_id} profile")

    # 3. list_volunteers
    print(" 3. Testing 'list_volunteers'...")
    res = ALL_AI_TOOLS["list_volunteers"]()
    assert res["success"] is True
    assert res["success"] is True and len(res["volunteers"]) >= 2
    print(f"    -> [OK] list_volunteers returned {len(res['volunteers'])} volunteers")

    # 4. update_volunteer
    print(" 4. Testing 'update_volunteer'...")
    res = ALL_AI_TOOLS["update_volunteer"](volunteer_id=v1_id, max_capacity=7, skills="Design, Marketing, PR")
    assert res["success"] is True
    print("    -> [OK] update_volunteer updated skills & capacity")

    # 5. get_volunteer_tasks
    print(" 5. Testing 'get_volunteer_tasks'...")
    res = ALL_AI_TOOLS["get_volunteer_tasks"](volunteer_id=v1_id)
    assert res["success"] is True
    print(f"    -> [OK] Retrieved tasks for volunteer #{v1_id}")

    # 6. calculate_volunteer_load
    print(" 6. Testing 'calculate_volunteer_load'...")
    res = ALL_AI_TOOLS["calculate_volunteer_load"](volunteer_id=v1_id)
    assert res["success"] is True
    assert "utilization_percent" in res["load"]
    print(f"    -> [OK] Calculated workload utilization: {res['load']['utilization_percent']}%")

    # 7. get_overloaded_volunteers
    print(" 7. Testing 'get_overloaded_volunteers'...")
    res = ALL_AI_TOOLS["get_overloaded_volunteers"]()
    assert res["success"] is True
    print(f"    -> [OK] Scanned overloaded volunteers ({len(res['overloaded_volunteers'])} currently overloaded)")

    # 8. delete_volunteer (testing with disposable volunteer)
    print(" 8. Testing 'delete_volunteer'...")
    res = ALL_AI_TOOLS["delete_volunteer"](volunteer_id=v_disp_id)
    assert res["success"] is True
    print(f"    -> [OK] Successfully removed disposable volunteer #{v_disp_id}")


    # =============================================================
    # MODULE 1: TASK TOOLS (18 TOOLS)
    # =============================================================
    print("\n" + "=" * 60)
    print("TESTING MODULE 1: TASK TOOLS (18 TOOLS)")
    print("=" * 60)

    # 1. create_task
    print(" 1. Testing 'create_task'...")
    res1 = ALL_AI_TOOLS["create_task"](
        title=f"Design Main Stage Banner {suffix}",
        event_id=event_id,
        phase="PLANNING",
        priority="HIGH",
        due_date=(datetime.now() + timedelta(days=6)).isoformat(),
        owner_ids=[v1_id],
        description="Design wide-format print banner."
    )
    assert res1["success"] is True
    t1_id = res1["task_id"]

    res2 = ALL_AI_TOOLS["create_task"](
        title=f"Setup Sound System & Mics {suffix}",
        event_id=event_id,
        phase="EXECUTION",
        priority="MEDIUM",
        due_date=(datetime.now() + timedelta(days=10)).isoformat(),
        description="Verify audio channels."
    )
    assert res2["success"] is True
    t2_id = res2["task_id"]
    print(f"    -> [OK] Tasks created: Task #{t1_id}, Task #{t2_id}")

    # Volunteer Tool #9: suggest_task_owner
    print("    * Testing Volunteer Tool 'suggest_task_owner'...")
    sug_res = ALL_AI_TOOLS["suggest_task_owner"](task_id=t2_id)
    assert sug_res["success"] is True
    print(f"    -> [OK] suggest_task_owner returned candidate suggestions")

    # 2. get_task
    print(" 2. Testing 'get_task'...")
    res = ALL_AI_TOOLS["get_task"](task_id=t1_id)
    assert res["success"] is True
    assert res["task"]["id"] == t1_id
    print(f"    -> [OK] Retrieved task: '{res['task']['title']}'")

    # 3. list_tasks
    print(" 3. Testing 'list_tasks'...")
    res = ALL_AI_TOOLS["list_tasks"](event_id=event_id)
    assert res["success"] is True
    assert len(res["tasks"]) >= 2
    print(f"    -> [OK] list_tasks returned {len(res['tasks'])} task(s)")

    # 4. update_task
    print(" 4. Testing 'update_task'...")
    res = ALL_AI_TOOLS["update_task"](task_id=t1_id, description="Updated flyer dimensions to 300dpi format.")
    assert res["success"] is True
    print("    -> [OK] update_task modified description")

    # 5. change_task_status
    print(" 5. Testing 'change_task_status'...")
    res = ALL_AI_TOOLS["change_task_status"](task_id=t1_id, status="IN_PROGRESS")
    assert res["success"] is True
    print("    -> [OK] change_task_status changed status to IN_PROGRESS")

    # 6. assign_task
    print(" 6. Testing 'assign_task'...")
    res = ALL_AI_TOOLS["assign_task"](task_id=t2_id, volunteer_ids=[v2_id])
    assert res["success"] is True
    print(f"    -> [OK] assign_task assigned volunteer #{v2_id} to task #{t2_id}")

    # 7. unassign_task
    print(" 7. Testing 'unassign_task'...")
    res = ALL_AI_TOOLS["unassign_task"](task_id=t2_id, volunteer_ids=[v2_id])
    assert res["success"] is True
    print("    -> [OK] unassign_task unassigned volunteer successfully")

    # Reassign for subsequent steps
    ALL_AI_TOOLS["assign_task"](task_id=t2_id, volunteer_ids=[v2_id])

    # 8. create_subtask
    print(" 8. Testing 'create_subtask'...")
    res = ALL_AI_TOOLS["create_subtask"](parent_id=t1_id, title=f"Vector Asset Export {suffix}", event_id=event_id)
    assert res["success"] is True
    sub_id = res["task_id"]
    print(f"    -> [OK] Subtask #{sub_id} created under parent #{t1_id}")

    # 9. list_subtasks
    print(" 9. Testing 'list_subtasks'...")
    res = ALL_AI_TOOLS["list_subtasks"](parent_id=t1_id)
    assert res["success"] is True
    assert len(res["subtasks"]) >= 1
    print(f"    -> [OK] list_subtasks confirmed {len(res['subtasks'])} subtask(s)")

    # 10. add_task_dependency
    print("10. Testing 'add_task_dependency'...")
    res = ALL_AI_TOOLS["add_task_dependency"](dependent_task_id=t2_id, prerequisite_task_id=t1_id)
    assert res["success"] is True
    print(f"    -> [OK] Dependency added: Task #{t2_id} depends on #{t1_id}")

    # 11. get_task_dependencies
    print("11. Testing 'get_task_dependencies'...")
    res = ALL_AI_TOOLS["get_task_dependencies"](task_id=t2_id)
    assert res["success"] is True
    assert len(res["blocked_by"]) >= 1
    print(f"    -> [OK] Verified dependencies: blocked by {len(res['blocked_by'])} task(s)")

    # 12. remove_task_dependency
    print("12. Testing 'remove_task_dependency'...")
    res = ALL_AI_TOOLS["remove_task_dependency"](dependent_task_id=t2_id, prerequisite_task_id=t1_id)
    assert res["success"] is True
    print("    -> [OK] Dependency removed cleanly")

    # 13. add_task_comment
    print("13. Testing 'add_task_comment'...")
    res = ALL_AI_TOOLS["add_task_comment"](task_id=t1_id, user_id=u1_id, content="First draft review scheduled.")
    assert res["success"] is True
    print("    -> [OK] Comment added to task")

    # 14. get_task_activity
    print("14. Testing 'get_task_activity'...")
    res = ALL_AI_TOOLS["get_task_activity"](task_id=t1_id)
    assert res["success"] is True
    assert len(res["activity"]) >= 1
    print(f"    -> [OK] Retrieved {len(res['activity'])} task activity entry/entries")

    # 15. bulk_update_tasks
    print("15. Testing 'bulk_update_tasks'...")
    res = ALL_AI_TOOLS["bulk_update_tasks"](task_ids=[t1_id, t2_id], priority="URGENT")
    assert res["success"] is True
    print("    -> [OK] bulk_update_tasks set priority to URGENT across tasks")

    # 16. calculate_critical_path
    print("16. Testing 'calculate_critical_path'...")
    res = ALL_AI_TOOLS["calculate_critical_path"](event_id=event_id)
    assert res["success"] is True
    print("    -> [OK] calculate_critical_path executed successfully")

    # 17. get_overdue_tasks
    print("17. Testing 'get_overdue_tasks'...")
    res = ALL_AI_TOOLS["get_overdue_tasks"](event_id=event_id)
    assert res["success"] is True
    print(f"    -> [OK] get_overdue_tasks checked ({len(res['tasks'])} overdue tasks)")

    # 18. delete_task (using disposable task)
    print("18. Testing 'delete_task'...")
    disp_t = ALL_AI_TOOLS["create_task"](title=f"Disposable Task {suffix}", event_id=event_id)
    res = ALL_AI_TOOLS["delete_task"](task_id=disp_t["task_id"])
    assert res["success"] is True
    print(f"    -> [OK] delete_task deleted Task #{disp_t['task_id']}")

    # Volunteer Tool #10: bulk_reassign_tasks
    print("    * Testing Volunteer Tool 'bulk_reassign_tasks'...")
    res = ALL_AI_TOOLS["bulk_reassign_tasks"](from_volunteer_id=v1_id, to_volunteer_id=v2_id)
    assert res["success"] is True
    print(f"    -> [OK] bulk_reassign_tasks moved {res['reassigned_count']} task(s) from v1 to v2")


    # =============================================================
    # MODULE 4: MEETING TOOLS (8 TOOLS)
    # =============================================================
    print("\n" + "=" * 60)
    print("TESTING MODULE 4: MEETING TOOLS (8 TOOLS)")
    print("=" * 60)

    # 1. create_meeting
    print(" 1. Testing 'create_meeting'...")
    transcript = """
    Attendees: Ananya Roy, Vikram Seth
    Discussion:
    - Reviewed venue setup progress and stage lighting.
    - ACTION: Vikram Seth to verify stage lighting and microphones by Friday.
    - ACTION: Ananya Roy to publish teaser video and press release by tomorrow.
    - ACTION: Order extra participant badges from college print shop.
    """
    res = ALL_AI_TOOLS["create_meeting"](
        event_id=event_id,
        title=f"Operations Alignment Meeting {suffix}",
        date=datetime.now().isoformat(),
        attendees=["Ananya Roy", "Vikram Seth"],
        raw_notes=transcript
    )
    assert res["success"] is True
    meeting_id = res["meeting_id"]
    print(f"    -> [OK] Meeting logged: ID #{meeting_id}")

    # 2. get_meeting
    print(" 2. Testing 'get_meeting'...")
    res = ALL_AI_TOOLS["get_meeting"](meeting_id=meeting_id)
    assert res["success"] is True
    assert res["meeting"]["id"] == meeting_id
    print(f"    -> [OK] Retrieved meeting: '{res['meeting']['title']}'")

    # 3. list_meetings
    print(" 3. Testing 'list_meetings'...")
    res = ALL_AI_TOOLS["list_meetings"](event_id=event_id)
    assert res["success"] is True
    assert any(m["id"] == meeting_id for m in res["meetings"])
    print(f"    -> [OK] list_meetings returned {res['count']} meeting(s)")

    # 4. update_meeting
    print(" 4. Testing 'update_meeting'...")
    res = ALL_AI_TOOLS["update_meeting"](meeting_id=meeting_id, title=f"Operations Standup - Finalized {suffix}")
    assert res["success"] is True
    assert "Finalized" in res["title"]
    print("    -> [OK] update_meeting updated meeting title")

    # 5. extract_action_items
    print(" 5. Testing 'extract_action_items'...")
    res = ALL_AI_TOOLS["extract_action_items"](meeting_id=meeting_id)
    assert res["success"] is True
    assert res["extracted_count"] >= 2
    print(f"    -> [OK] Extracted {res['extracted_count']} action item(s)")

    # 6. resolve_action_item_references
    print(" 6. Testing 'resolve_action_item_references'...")
    res = ALL_AI_TOOLS["resolve_action_item_references"](meeting_id=meeting_id)
    assert res["success"] is True
    print(f"    -> [OK] Resolved references: {res['resolved_count']}")

    # 7. review_extracted_actions
    print(" 7. Testing 'review_extracted_actions'...")
    res = ALL_AI_TOOLS["review_extracted_actions"](meeting_id=meeting_id)
    assert res["success"] is True
    sample_action_id = res["action_items"][0]["action_item_id"]
    print(f"    -> [OK] review_extracted_actions returned items (Sample Action ID: {sample_action_id})")

    # 8. apply_extracted_actions
    print(" 8. Testing 'apply_extracted_actions'...")
    res = ALL_AI_TOOLS["apply_extracted_actions"](meeting_id=meeting_id, action_item_ids=[sample_action_id])
    assert res["success"] is True
    assert res["applied_count"] >= 1
    print(f"    -> [OK] apply_extracted_actions created {res['applied_count']} formal Task(s)!")


    # =============================================================
    # MODULE 5: RISK TOOLS (11 TOOLS)
    # =============================================================
    print("\n" + "=" * 60)
    print("TESTING MODULE 5: RISK TOOLS (11 TOOLS)")
    print("=" * 60)

    # 1. get_unowned_tasks_near_deadline
    print(" 1. Testing 'get_unowned_tasks_near_deadline'...")
    unowned_t = ALL_AI_TOOLS["create_task"](
        title=f"Emergency Evacuation Plan {suffix}",
        event_id=event_id,
        due_date=(datetime.now() + timedelta(days=2)).isoformat(),
        priority="URGENT"
    )
    res = ALL_AI_TOOLS["get_unowned_tasks_near_deadline"](event_id=event_id, days_threshold=7)
    assert res["success"] is True
    assert res["unowned_count"] >= 1
    print(f"    -> [OK] get_unowned_tasks_near_deadline found {res['unowned_count']} task(s)")

    # 2. get_overload_risks
    print(" 2. Testing 'get_overload_risks'...")
    ALL_AI_TOOLS["create_task"](title=f"Heavy Task 1 {suffix}", event_id=event_id, owner_ids=[v2_id])
    ALL_AI_TOOLS["create_task"](title=f"Heavy Task 2 {suffix}", event_id=event_id, owner_ids=[v2_id])
    ALL_AI_TOOLS["create_task"](title=f"Heavy Task 3 {suffix}", event_id=event_id, owner_ids=[v2_id])
    res = ALL_AI_TOOLS["get_overload_risks"](event_id=event_id)
    assert res["success"] is True
    print(f"    -> [OK] get_overload_risks detected {res['overload_risk_count']} workload risk(s)")

    # 3. get_dependency_conflicts
    print(" 3. Testing 'get_dependency_conflicts'...")
    early_dep = ALL_AI_TOOLS["create_task"](title=f"Early Dep {suffix}", event_id=event_id, due_date=(datetime.now() + timedelta(days=2)).isoformat())
    late_prereq = ALL_AI_TOOLS["create_task"](title=f"Late Prereq {suffix}", event_id=event_id, due_date=(datetime.now() + timedelta(days=9)).isoformat())
    ALL_AI_TOOLS["add_task_dependency"](dependent_task_id=early_dep["task_id"], prerequisite_task_id=late_prereq["task_id"])
    res = ALL_AI_TOOLS["get_dependency_conflicts"](event_id=event_id)
    assert res["success"] is True, f"get_dependency_conflicts failed: {res}"
    assert res["conflict_count"] >= 1
    print(f"    -> [OK] get_dependency_conflicts detected {res['conflict_count']} conflict(s)")

    # 4. get_missing_activity_risks
    print(" 4. Testing 'get_missing_activity_risks'...")
    res = ALL_AI_TOOLS["get_missing_activity_risks"](event_id=event_id)
    assert res["success"] is True
    assert res["missing_activity_count"] >= 1
    print(f"    -> [OK] get_missing_activity_risks found {res['missing_activity_count']} missing activity domain(s)")

    # 5. detect_event_risks (Unified Orchestrator)
    print(" 5. Testing 'detect_event_risks' (Unified Orchestrator)...")
    res = ALL_AI_TOOLS["detect_event_risks"](event_id=event_id, persist=True)
    assert res["success"] is True
    summary = res["summary"]
    assert summary["total_active_risks"] >= 3
    print(f"    -> [OK] detect_event_risks aggregated {summary['total_active_risks']} total risks across categories: {list(summary['by_category'].keys())}")

    # 6. list_risks
    print(" 6. Testing 'list_risks'...")
    res = ALL_AI_TOOLS["list_risks"](event_id=event_id)
    assert res["success"] is True
    assert res["count"] >= 1
    sample_risk_id = res["risks"][0]["id"]
    print(f"    -> [OK] list_risks retrieved {res['count']} risk(s). Sample Risk ID: #{sample_risk_id}")

    # 7. get_risk
    print(" 7. Testing 'get_risk'...")
    res = ALL_AI_TOOLS["get_risk"](risk_id=sample_risk_id)
    assert res["success"] is True
    assert res["risk"]["id"] == sample_risk_id
    print(f"    -> [OK] Retrieved risk #{sample_risk_id}: [{res['risk']['severity']}] {res['risk']['title']}")

    # 8. detect_task_risks
    print(" 8. Testing 'detect_task_risks'...")
    res = ALL_AI_TOOLS["detect_task_risks"](task_id=early_dep["task_id"])
    assert res["success"] is True
    assert res["risk_count"] >= 1
    print(f"    -> [OK] detect_task_risks surfaced {res['risk_count']} risk(s) for task #{early_dep['task_id']}")

    # 9. explain_risk
    print(" 9. Testing 'explain_risk'...")
    res = ALL_AI_TOOLS["explain_risk"](risk_id=sample_risk_id)
    assert res["success"] is True
    assert len(res["explanation"]["why_it_exists"]) > 0
    print(f"    -> [OK] explain_risk generated explanation: '{res['explanation']['potential_impact'][:45]}...'")

    # 10. suggest_risk_fix
    print("10. Testing 'suggest_risk_fix'...")
    res = ALL_AI_TOOLS["suggest_risk_fix"](risk_id=sample_risk_id)
    assert res["success"] is True
    assert len(res["fix_suggestion"]["actionable_steps"]) > 0
    print(f"    -> [OK] suggest_risk_fix proposed fix type: {res['fix_suggestion']['fix_type']}")

    # 11. resolve_risk
    print("11. Testing 'resolve_risk'...")
    res = ALL_AI_TOOLS["resolve_risk"](risk_id=sample_risk_id, resolution_notes="Resolved in master verification suite.")
    assert res["success"] is True
    assert res["status"] == "RESOLVED"
    print(f"    -> [OK] resolve_risk resolved Risk #{sample_risk_id}")

    print("\n" + "=" * 75)
    print("COMPLETE SUCCESS: ALL 5 MODULES AND ALL 58 AI TOOLS WORKING FLAWLESSLY!")
    print("=" * 75)


if __name__ == "__main__":
    run_master_test_suite()

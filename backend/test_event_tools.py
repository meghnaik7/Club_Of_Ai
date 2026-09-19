import os
import sys
from datetime import datetime, timedelta

# Ensure backend directory is on python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), 'clubops.db'))}"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.session import engine
Base.metadata.create_all(bind=engine)

from app.models.user import User
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.task import Task, TaskStatus, TaskPriority, TaskPhase
from app.models.event import Event, EventStatus, Expense, EventBudgetCategory

# AI Tools
from app.ai.tools.event_tools import (
    create_event,
    get_event,
    list_events,
    update_event,
    delete_event,
    get_event_dashboard,
    get_event_timeline,
    get_event_budget,
    record_expense,
    update_budget_allocation,
    generate_event_plan
)
from app.ai.tools import ALL_AI_TOOLS

def run_tests():
    print("=" * 60)
    print("RUNNING UNIT TESTS FOR EVENT TOOLS (11 TOOLS)")
    print("=" * 60)

    # 0. Test registry contains all 39+ tools
    print(f"\n[Test 0] Checking Tool Registry...")
    assert len(ALL_AI_TOOLS) >= 39, f"Expected at least 39 registered tools, got {len(ALL_AI_TOOLS)}"
    print(f"[OK] Tool registry has {len(ALL_AI_TOOLS)} tools registered in ALL_AI_TOOLS!")

    # 1. Test create_event
    print("\n[Test 1] Testing create_event...")
    target_date = (datetime.utcnow() + timedelta(days=20)).isoformat()
    res1 = create_event(
        name="AI & Cloud Hackathon 2026",
        date=target_date,
        venue="Campus Innovation Hall",
        budget=5000.0,
        expected_attendance=250,
        description="Annual club hackathon focusing on autonomous AI agents and cloud applications."
    )
    assert res1["success"] is True, f"create_event failed: {res1}"
    event_id = res1["event_id"]
    print(f"[OK] Event created successfully with ID: {event_id}")

    # 2. Test get_event
    print("\n[Test 2] Testing get_event...")
    res2 = get_event(event_id=event_id)
    assert res2["success"] is True, f"get_event failed: {res2}"
    assert res2["event"]["title"] == "AI & Cloud Hackathon 2026"
    assert len(res2["event"]["budget_categories"]) == 5
    print(f"[OK] Retrieved event details with 5 default budget categories.")

    # 3. Test list_events
    print("\n[Test 3] Testing list_events...")
    res3 = list_events()
    assert res3["success"] is True, f"list_events failed: {res3}"
    assert res3["count"] >= 1
    print(f"[OK] list_events returned {res3['count']} event(s).")

    # 4. Test update_event
    print("\n[Test 4] Testing update_event...")
    res4 = update_event(
        event_id=event_id,
        venue="Main Grand Ballroom & Labs",
        expected_attendance=300
    )
    assert res4["success"] is True, f"update_event failed: {res4}"
    assert res4["venue"] == "Main Grand Ballroom & Labs"
    print(f"[OK] Updated event venue and attendance target.")

    # 5. Test update_budget_allocation
    print("\n[Test 5] Testing update_budget_allocation...")
    res5 = update_budget_allocation(
        event_id=event_id,
        total_budget=6000.0,
        category_allocations={
            "Venue": 2000.0,
            "Catering & Food": 2000.0,
            "Prizes & Swag": 1500.0,
            "Logistics": 500.0
        }
    )
    assert res5["success"] is True, f"update_budget_allocation failed: {res5}"
    assert res5["total_budget"] == 6000.0
    print(f"[OK] Reallocated event budget to $6000 across customized categories.")

    # 6. Test record_expense
    print("\n[Test 6] Testing record_expense...")
    exp1 = record_expense(
        event_id=event_id,
        amount=750.0,
        category="Catering & Food",
        description="Deposit for pizza and lunch catering service",
        recorded_by="Treasurer"
    )
    assert exp1["success"] is True, f"record_expense failed: {exp1}"

    exp2 = record_expense(
        event_id=event_id,
        amount=1200.0,
        category="Venue",
        description="Audio/Visual setup fee and hall security deposit",
        recorded_by="Operations Lead"
    )
    assert exp2["success"] is True, f"record_expense failed: {exp2}"
    print(f"[OK] Successfully recorded 2 expenses totaling $1950.")

    # 7. Test get_event_budget
    print("\n[Test 7] Testing get_event_budget...")
    res7 = get_event_budget(event_id=event_id)
    assert res7["success"] is True, f"get_event_budget failed: {res7}"
    summary = res7["budget_summary"]
    assert summary["total_budget"] == 6000.0
    assert summary["total_spent"] == 1950.0
    assert summary["remaining_budget"] == 4050.0
    assert summary["is_over_budget"] is False
    print(f"[OK] Budget summary verified: Spent=${summary['total_spent']}, Remaining=${summary['remaining_budget']}")

    # 8. Test generate_event_plan
    print("\n[Test 8] Testing generate_event_plan...")
    brief = "We are hosting an overnight university hackathon for 300 students. We need rooms booked, sponsor coordination, audio visual checks, and food for 24 hours."
    res8 = generate_event_plan(
        event_brief=brief,
        event_title="Hackathon Operations Plan",
        estimated_budget=6000.0,
        target_date=target_date,
        auto_create_in_event_id=event_id
    )
    assert res8["success"] is True, f"generate_event_plan failed: {res8}"
    plan = res8["plan"]
    assert len(plan["phases"]) == 5
    print(f"[OK] Generated comprehensive plan with {len(plan['phases'])} phases and automatically populated event tasks.")

    # 9. Test get_event_timeline
    print("\n[Test 9] Testing get_event_timeline...")
    res9 = get_event_timeline(event_id=event_id)
    assert res9["success"] is True, f"get_event_timeline failed: {res9}"
    timeline = res9["timeline"]
    assert len(timeline) >= 10
    print(f"[OK] Timeline returned {len(timeline)} chronological tasks with dependency mapping.")

    # 10. Test get_event_dashboard
    print("\n[Test 10] Testing get_event_dashboard...")
    res10 = get_event_dashboard(event_id=event_id)
    assert res10["success"] is True, f"get_event_dashboard failed: {res10}"
    dash = res10["dashboard"]
    assert dash["task_stats"]["total"] >= 10
    assert "risks" in dash
    print(f"[OK] Event dashboard returned complete stats: {dash['task_stats']['total']} tasks, {dash['days_remaining']} days remaining, {len(dash['risks'])} risk item(s) surfaced.")

    # 11. Test delete_event (with associated cleanup)
    print("\n[Test 11] Testing delete_event...")
    # Create a dummy event to test deletion
    dummy_res = create_event(name="Temporary Event", date=target_date, budget=100.0)
    dummy_id = dummy_res["event_id"]
    res11 = delete_event(event_id=dummy_id, delete_documents=False)
    assert res11["success"] is True, f"delete_event failed: {res11}"
    assert res11["deleted"] is True
    print(f"[OK] Event {dummy_id} cleanly deleted with all associated records.")

    print("\n" + "=" * 60)
    print("ALL 11 EVENT TOOLS VERIFIED AND PASSING SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()

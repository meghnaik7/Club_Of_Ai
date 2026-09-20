import os
import sys
from datetime import datetime, timedelta

# Ensure backend directory is on python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), 'clubops.db'))}"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.session import engine, SessionLocal
Base.metadata.create_all(bind=engine)

from app.models.user import User
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.event import Event, EventStatus
from app.models.meeting import Meeting, MeetingActionItem
from app.models.task import Task

# AI Tools
from app.ai.tools.meeting_tools import (
    create_meeting,
    get_meeting,
    list_meetings,
    update_meeting,
    extract_action_items,
    resolve_action_item_references,
    review_extracted_actions,
    apply_extracted_actions
)
from app.ai.tools.event_tools import create_event
from app.ai.tools.volunteer_tools import create_volunteer
from app.ai.tools import ALL_AI_TOOLS


def run_tests():
    print("=" * 60)
    print("RUNNING UNIT TESTS FOR MEETING TOOLS (8 TOOLS)")
    print("=" * 60)

    # 0. Check Tool Registry
    print(f"\n[Test 0] Checking Tool Registry...")
    assert len(ALL_AI_TOOLS) >= 47, f"Expected at least 47 registered tools, got {len(ALL_AI_TOOLS)}"
    print(f"[OK] Tool registry has {len(ALL_AI_TOOLS)} tools registered in ALL_AI_TOOLS!")

    db = SessionLocal()

    # 1. Setup prerequisite Event & Volunteers (including Riya)
    print("\n[Test 1] Setting up prerequisite Event & Volunteers...")
    event_res = create_event(
        name="TechFest Planning Summit",
        date=(datetime.now() + timedelta(days=15)).isoformat(),
        venue="Conference Room B",
        budget=4000.0
    )
    event_id = event_res["event_id"]

    # Create user & volunteer for Riya Sharma
    existing_user = db.query(User).filter(User.email == "riya.sharma@college.edu").first()
    if not existing_user:
        riya_user = User(
            email="riya.sharma@college.edu",
            full_name="Riya Sharma",
            hashed_password="mockpassword123"
        )
        db.add(riya_user)
        db.commit()
        db.refresh(riya_user)
    else:
        riya_user = existing_user

    existing_vol = db.query(Volunteer).filter(Volunteer.user_id == riya_user.id).first()
    if not existing_vol:
        vol_res = create_volunteer(
            user_id=riya_user.id,
            skills="Sponsorship, Corporate Outreach, Budgeting",
            availability="Weekdays"
        )
        riya_vol_id = vol_res["volunteer_id"]
    else:
        riya_vol_id = existing_vol.id

    print(f"[OK] Event {event_id} and Volunteer Riya Sharma (ID: {riya_vol_id}) configured.")

    # 2. Test create_meeting
    print("\n[Test 2] Testing create_meeting...")
    notes_content = """# Core Organizing Committee Weekly Sync
Attendees: Riya Sharma, Aryan Verma, Devanshi Patel
Meeting Goal: Finalize logistics and sponsor coordination for TechFest.

Discussion Points:
- Overall timeline is on track.
- Sponsor outreach requires immediate follow-up.

Action Items:
Riya will handle sponsors by Friday.
Aryan to coordinate venue setup before Wednesday.
Devanshi will finalize food catering menu by tomorrow.
"""
    m_res = create_meeting(
        event_id=event_id,
        title="TechFest Logistics & Sponsorship Sync",
        date=datetime.now().isoformat(),
        location="Student Center Room 204",
        attendees=["Riya Sharma", "Aryan Verma", "Devanshi Patel"],
        raw_notes=notes_content
    )
    assert m_res["success"] is True, f"create_meeting failed: {m_res}"
    meeting_id = m_res["meeting_id"]
    print(f"[OK] Meeting created successfully with ID: {meeting_id}")

    # 3. Test get_meeting
    print("\n[Test 3] Testing get_meeting...")
    g_res = get_meeting(meeting_id=meeting_id)
    assert g_res["success"] is True, f"get_meeting failed: {g_res}"
    assert g_res["meeting"]["title"] == "TechFest Logistics & Sponsorship Sync"
    assert len(g_res["meeting"]["attendees"]) == 3
    print(f"[OK] Successfully retrieved meeting details and attendees.")

    # 4. Test list_meetings
    print("\n[Test 4] Testing list_meetings...")
    l_res = list_meetings(event_id=event_id)
    assert l_res["success"] is True, f"list_meetings failed: {l_res}"
    assert l_res["count"] >= 1
    print(f"[OK] list_meetings returned {l_res['count']} meeting(s) for event {event_id}.")

    # 5. Test update_meeting
    print("\n[Test 5] Testing update_meeting...")
    u_res = update_meeting(
        meeting_id=meeting_id,
        location="Campus Innovation Center & Zoom Hybrid"
    )
    assert u_res["success"] is True, f"update_meeting failed: {u_res}"
    assert u_res["location"] == "Campus Innovation Center & Zoom Hybrid"
    print(f"[OK] Updated meeting location to hybrid.")

    # 6. Test extract_action_items
    print("\n[Test 6] Testing extract_action_items...")
    ext_res = extract_action_items(meeting_id=meeting_id)
    assert ext_res["success"] is True, f"extract_action_items failed: {ext_res}"
    assert ext_res["extracted_count"] >= 3, f"Expected at least 3 action items, got {ext_res['extracted_count']}"
    
    # Check specific example from user prompt: "Riya will handle sponsors by Friday."
    riya_action = next(
        (item for item in ext_res["action_items"] if "sponsors" in item["title"].lower()),
        None
    )
    assert riya_action is not None, "Did not extract 'handle sponsors' action item"
    assert riya_action["owner"] == "Riya"
    assert "Friday" in (riya_action["due_date_raw"] or "")
    assert riya_action["confidence"] >= 0.90
    print(f"[OK] Extracted {ext_res['extracted_count']} action items:")
    for item in ext_res["action_items"]:
        print(f"     * Action: '{item['title']}', Owner: '{item['owner']}', Due: '{item['due_date_raw']}', Confidence: {item['confidence']}")

    # 7. Test resolve_action_item_references
    print("\n[Test 7] Testing resolve_action_item_references...")
    res_res = resolve_action_item_references(meeting_id=meeting_id)
    assert res_res["success"] is True, f"resolve_action_item_references failed: {res_res}"
    
    # Verify Riya resolved to volunteer ID
    resolved_riya = next(
        (r for r in res_res["resolutions"] if r["owner_reference"].lower() == "riya"),
        None
    )
    assert resolved_riya is not None, "Did not find resolution for Riya"
    assert resolved_riya["matched_volunteer_id"] == riya_vol_id
    assert resolved_riya["matched_volunteer_name"] == "Riya Sharma"
    print(f"[OK] Successfully resolved informal reference 'Riya' -> Volunteer {riya_vol_id} ('Riya Sharma') with confidence {resolved_riya['match_confidence']}.")

    # 8. Test review_extracted_actions
    print("\n[Test 8] Testing review_extracted_actions...")
    rev_res = review_extracted_actions(meeting_id=meeting_id)
    assert rev_res["success"] is True, f"review_extracted_actions failed: {rev_res}"
    assert rev_res["pending_count"] >= 3
    print(f"[OK] Reviewed {len(rev_res['action_items'])} action items before applying.")

    # 9. Test apply_extracted_actions (converts approved items to real Tasks)
    print("\n[Test 9] Testing apply_extracted_actions...")
    app_res = apply_extracted_actions(meeting_id=meeting_id)
    assert app_res["success"] is True, f"apply_extracted_actions failed: {app_res}"
    assert app_res["applied_count"] >= 3
    created_tasks = app_res["created_tasks"]
    print(f"[OK] Successfully converted {app_res['applied_count']} action items into real event tasks:")
    for ct in created_tasks:
        print(f"     * Created Task #{ct['task_id']}: '{ct['title']}', Assigned Volunteers: {ct['assigned_volunteer_ids']}")

    # Verify task in DB
    riya_task_info = next(
        (t for t in created_tasks if "sponsors" in t["title"].lower()),
        None
    )
    assert riya_task_info is not None
    assert riya_vol_id in riya_task_info["assigned_volunteer_ids"]
    db_task = db.query(Task).filter(Task.id == riya_task_info["task_id"]).first()
    assert db_task is not None
    assert db_task.event_id == event_id

    # Verify status changed to APPLIED
    g_after = get_meeting(meeting_id=meeting_id)
    for it in g_after["meeting"]["action_items"]:
        assert it["status"] == "APPLIED"
        assert it["applied_task_id"] is not None

    print(f"[OK] Verified task persistence and action item status updated to APPLIED.")
    db.close()

    print("\n" + "=" * 60)
    print("ALL 8 MEETING TOOLS VERIFIED AND PASSING SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()

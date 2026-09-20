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
from app.models.volunteer import Volunteer
from app.models.event import Event
from app.models.task import Task, TaskStatus, TaskPriority, TaskPhase
from app.models.risk import EventRisk

# AI Tools
from app.ai.tools.risk_tools import (
    list_risks,
    get_risk,
    detect_event_risks,
    detect_task_risks,
    explain_risk,
    suggest_risk_fix,
    resolve_risk,
    get_unowned_tasks_near_deadline,
    get_overload_risks,
    get_dependency_conflicts,
    get_missing_activity_risks,
)
from app.ai.tools.event_tools import create_event
from app.ai.tools.task_tools import create_task, add_task_dependency, assign_task
from app.ai.tools.volunteer_tools import create_volunteer
from app.ai.tools import ALL_AI_TOOLS


def run_tests():
    print("=" * 60)
    print("RUNNING UNIT TESTS FOR RISK TOOLS (11 TOOLS)")
    print("=" * 60)

    # 0. Check Tool Registry (Total 58 tools)
    print(f"\n[Test 0] Checking Tool Registry...")
    assert len(ALL_AI_TOOLS) == 58, f"Expected 58 registered tools, got {len(ALL_AI_TOOLS)}"
    print(f"[OK] All 58 tools successfully registered in ALL_AI_TOOLS registry!")

    db = SessionLocal()

    # 1. Setup Event and Test Risk Scenarios
    print("\n[Test 1] Setting up Event and scenario tasks/dependencies...")
    event_res = create_event(
        name="Annual RoboWars Championship 2026",
        date=(datetime.now() + timedelta(days=25)).isoformat(),
        venue="Engineering Arena",
        budget=8000.0,
        expected_attendance=150
    )
    event_id = event_res["event_id"]

    # Scenario A: Unowned task near deadline (due in 2 days)
    t_unowned = create_task(
        title="Safety Goggles and Fire Extinguisher Inspection",
        event_id=event_id,
        due_date=(datetime.now() + timedelta(days=2)).isoformat(),
        priority="URGENT"
    )
    task_unowned_id = t_unowned["task_id"]

    # Create user & volunteer with low capacity
    import uuid
    u_vol = User(email=f"overloaded.lead.{uuid.uuid4().hex[:6]}@college.edu", full_name="Tanvi Desai", hashed_password="pw")
    db.add(u_vol)
    db.commit()
    db.refresh(u_vol)
    v_res = create_volunteer(user_id=u_vol.id, max_capacity=4, skills="Robotics, Hardware")
    vol_id = v_res["volunteer_id"]

    t_b1 = create_task(title="Arena Combat Ring Fabrication", event_id=event_id, owner_ids=[vol_id])
    t_b2 = create_task(title="Pneumatics and Power Distribution", event_id=event_id, owner_ids=[vol_id])
    t_b3 = create_task(title="Telemetry Dashboard Integration", event_id=event_id, owner_ids=[vol_id])

    # Scenario C: Inverted Dependency Timeline
    # Task Prereq is due in 12 days, but Task Dependent is due in 6 days!
    t_prereq = create_task(
        title="Procure Heavy Duty Motors",
        event_id=event_id,
        due_date=(datetime.now() + timedelta(days=12)).isoformat()
    )
    prereq_id = t_prereq["task_id"]

    t_dependent = create_task(
        title="Assemble Bot Drive Chassis",
        event_id=event_id,
        due_date=(datetime.now() + timedelta(days=6)).isoformat()
    )
    dep_id = t_dependent["task_id"]

    # Add dependency: t_dependent depends on t_prereq
    add_task_dependency(dependent_task_id=dep_id, prerequisite_task_id=prereq_id)

    print(f"[OK] Test scenarios configured in Event #{event_id}:")
    print(f"     * Unowned near-deadline Task #{task_unowned_id}")
    print(f"     * Overloaded Volunteer #{vol_id} with 3 heavy tasks")
    print(f"     * Inverted dependency chain (Task #{dep_id} due before prerequisite Task #{prereq_id})")

    # 2. Test Specialized Detector: get_unowned_tasks_near_deadline
    print("\n[Test 2] Testing get_unowned_tasks_near_deadline...")
    unowned_res = get_unowned_tasks_near_deadline(event_id=event_id, days_threshold=5)
    assert unowned_res["success"] is True, f"Failed: {unowned_res}"
    assert unowned_res["unowned_count"] >= 1
    found_unowned = any(u["task_id"] == task_unowned_id for u in unowned_res["unowned_tasks"])
    assert found_unowned is True, "Did not detect unowned near-deadline task"
    print(f"[OK] Successfully detected {unowned_res['unowned_count']} unowned task(s) near deadline.")

    # 3. Test Specialized Detector: get_overload_risks
    print("\n[Test 3] Testing get_overload_risks...")
    overload_res = get_overload_risks(event_id=event_id)
    assert overload_res["success"] is True, f"Failed: {overload_res}"
    assert overload_res["overload_risk_count"] >= 1
    found_vol = any(o["volunteer_id"] == vol_id for o in overload_res["overload_risks"])
    assert found_vol is True, f"Did not detect overload for volunteer #{vol_id}"
    print(f"[OK] Successfully detected workload overload for Volunteer #{vol_id} ({overload_res['overload_risks'][0]['description']}).")

    # 4. Test Specialized Detector: get_dependency_conflicts
    print("\n[Test 4] Testing get_dependency_conflicts...")
    dep_conflicts_res = get_dependency_conflicts(event_id=event_id)
    assert dep_conflicts_res["success"] is True, f"Failed: {dep_conflicts_res}"
    assert dep_conflicts_res["conflict_count"] >= 1
    inversion = next((c for c in dep_conflicts_res["dependency_conflicts"] if c.get("task_id") == dep_id), None)
    assert inversion is not None, "Did not detect timeline inversion"
    assert "Timeline Inversion" in inversion["description"]
    print(f"[OK] Successfully detected timeline inversion: '{inversion['description']}'")

    # 5. Test Specialized Detector: get_missing_activity_risks
    print("\n[Test 5] Testing get_missing_activity_risks...")
    missing_res = get_missing_activity_risks(event_id=event_id)
    assert missing_res["success"] is True, f"Failed: {missing_res}"
    assert missing_res["missing_activity_count"] >= 2
    domains = [m["missing_domain"] for m in missing_res["missing_activities"]]
    print(f"[OK] Detected {missing_res['missing_activity_count']} missing essential activities: {domains}")

    # 6. Test Unified Orchestrator: detect_event_risks
    print("\n[Test 6] Testing detect_event_risks (Unified Orchestrator)...")
    event_risks_res = detect_event_risks(event_id=event_id, persist=True)
    assert event_risks_res["success"] is True, f"detect_event_risks failed: {event_risks_res}"
    summary = event_risks_res["summary"]
    assert summary["total_active_risks"] >= 4
    assert summary["critical_count"] >= 1
    print(f"[OK] detect_event_risks successfully aggregated internal detectors:")
    print(f"     * Total Active Risks: {summary['total_active_risks']}")
    print(f"     * Critical: {summary['critical_count']}, High: {summary['high_count']}, Medium: {summary['medium_count']}")
    print(f"     * By Category: {summary['by_category']}")

    # 7. Test list_risks
    print("\n[Test 7] Testing list_risks...")
    list_res = list_risks(event_id=event_id)
    assert list_res["success"] is True, f"list_risks failed: {list_res}"
    assert list_res["count"] >= 4
    sample_risk_id = list_res["risks"][0]["id"]
    print(f"[OK] list_risks retrieved {list_res['count']} active risk item(s). Sample Risk ID: {sample_risk_id}")

    # 8. Test get_risk
    print("\n[Test 8] Testing get_risk...")
    get_res = get_risk(risk_id=sample_risk_id)
    assert get_res["success"] is True, f"get_risk failed: {get_res}"
    assert get_res["risk"]["id"] == sample_risk_id
    assert get_res["risk"]["status"] == "ACTIVE"
    print(f"[OK] Retrieved risk: [{get_res['risk']['severity']}] {get_res['risk']['title']}")

    # 9. Test detect_task_risks (Single Task Analysis)
    print("\n[Test 9] Testing detect_task_risks for Task #{dep_id}...")
    task_risk_res = detect_task_risks(task_id=dep_id)
    assert task_risk_res["success"] is True, f"detect_task_risks failed: {task_risk_res}"
    assert task_risk_res["risk_count"] >= 1
    print(f"[OK] Single task risk detector surfaced {task_risk_res['risk_count']} risk(s) on Task #{dep_id}.")

    # 10. Test explain_risk
    print("\n[Test 10] Testing explain_risk...")
    exp_res = explain_risk(risk_id=sample_risk_id)
    assert exp_res["success"] is True, f"explain_risk failed: {exp_res}"
    expl = exp_res["explanation"]
    assert len(expl["why_it_exists"]) > 0
    assert len(expl["potential_impact"]) > 0
    print(f"[OK] Generated in-depth risk explanation:")
    print(f"     * Why it exists: {expl['why_it_exists']}")
    print(f"     * Potential impact: {expl['potential_impact']}")
    print(f"     * Recommended action: {expl['recommended_action']}")

    # 11. Test suggest_risk_fix
    print("\n[Test 11] Testing suggest_risk_fix...")
    fix_res = suggest_risk_fix(risk_id=sample_risk_id)
    assert fix_res["success"] is True, f"suggest_risk_fix failed: {fix_res}"
    fix = fix_res["fix_suggestion"]
    assert len(fix["actionable_steps"]) >= 2
    print(f"[OK] Generated concrete fix suggestion:")
    print(f"     * Fix Type: {fix['fix_type']}")
    print(f"     * Steps: {fix['actionable_steps']}")

    # 12. Test resolve_risk
    print("\n[Test 12] Testing resolve_risk...")
    resolve_res = resolve_risk(
        risk_id=sample_risk_id,
        resolution_notes="Volunteer assigned and timeline buffers confirmed with team.",
        resolved_by="Safety Lead"
    )
    assert resolve_res["success"] is True, f"resolve_risk failed: {resolve_res}"
    assert resolve_res["status"] == "RESOLVED"
    print(f"[OK] Risk #{sample_risk_id} successfully marked as RESOLVED.")

    db.close()
    print("\n" + "=" * 60)
    print("ALL 11 RISK TOOLS VERIFIED AND PASSING SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()

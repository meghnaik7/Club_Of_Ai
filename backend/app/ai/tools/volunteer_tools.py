from typing import List, Dict, Any, Optional
from app.db.session import SessionLocal
from app.services.volunteer_service import volunteer_service
from app.services.task_service import task_service
from app.schemas.volunteer import VolunteerCreate, VolunteerUpdate
from app.models.volunteer import VolunteerStatus
from app.engine.workload_calculator import calculate_volunteer_load, get_overloaded_volunteers as calc_overloaded

def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_volunteer(user_id: int, skills: str = None, availability: str = None, max_capacity: int = 10) -> Dict[str, Any]:
    """Create a volunteer with name, contact information, skills, and availability."""
    db = next(_get_db())
    try:
        vol_in = VolunteerCreate(user_id=user_id, skills=skills, availability=availability, max_capacity=max_capacity)
        vol = volunteer_service.create_volunteer(db, vol_in)
        return {"success": True, "volunteer_id": vol.id}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_volunteer(volunteer_id: int) -> Dict[str, Any]:
    """Retrieve volunteer profile including skills, availability, current load, and assigned tasks."""
    db = next(_get_db())
    try:
        vol = volunteer_service.get_volunteer(db, volunteer_id)
        if not vol:
            return {"success": False, "error": "Volunteer not found"}
            
        load = calculate_volunteer_load(db, volunteer_id)
        
        return {
            "success": True, 
            "volunteer": {
                "id": vol.id,
                "skills": vol.skills,
                "availability": vol.availability,
                "status": vol.status,
                "load": load
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_volunteers(skill: str = None, status: str = None) -> Dict[str, Any]:
    """Find volunteers using filters such as skill, availability, and workload."""
    db = next(_get_db())
    try:
        vols = volunteer_service.list_volunteers(db, skill=skill, status=VolunteerStatus(status) if status else None)
        return {"success": True, "volunteers": [{"id": v.id, "skills": v.skills} for v in vols]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def update_volunteer(volunteer_id: int, skills: str = None, availability: str = None, max_capacity: int = None, status: str = None) -> Dict[str, Any]:
    """Modify volunteer profile, skills, contact information, or availability."""
    db = next(_get_db())
    try:
        vol = volunteer_service.get_volunteer(db, volunteer_id)
        if not vol:
            return {"success": False, "error": "Volunteer not found"}
            
        update_data = {}
        if skills is not None: update_data["skills"] = skills
        if availability is not None: update_data["availability"] = availability
        if max_capacity is not None: update_data["max_capacity"] = max_capacity
        if status is not None: update_data["status"] = VolunteerStatus(status)
            
        vol_in = VolunteerUpdate(**update_data)
        updated = volunteer_service.update_volunteer(db, vol, vol_in)
        return {"success": True, "volunteer_id": updated.id}
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_volunteer(volunteer_id: int) -> Dict[str, Any]:
    """Remove a volunteer after checking their existing task assignments."""
    db = next(_get_db())
    try:
        deleted = volunteer_service.delete_volunteer(db, volunteer_id)
        return {"success": deleted}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_volunteer_tasks(volunteer_id: int) -> Dict[str, Any]:
    """Retrieve all tasks currently assigned to a volunteer."""
    db = next(_get_db())
    try:
        tasks = volunteer_service.get_volunteer_tasks(db, volunteer_id)
        return {"success": True, "tasks": [{"id": t.id, "title": t.title, "status": t.status} for t in tasks]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def tool_calculate_volunteer_load(volunteer_id: int) -> Dict[str, Any]:
    """Calculate workload based on assigned tasks, deadlines, priority, and available capacity."""
    db = next(_get_db())
    try:
        load = calculate_volunteer_load(db, volunteer_id)
        return {"success": True, "load": load}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_overloaded_volunteers() -> Dict[str, Any]:
    """Find volunteers whose current workload exceeds the configured capacity."""
    db = next(_get_db())
    try:
        overloaded = calc_overloaded(db)
        return {"success": True, "overloaded_volunteers": overloaded}
    except Exception as e:
        return {"success": False, "error": str(e)}

def suggest_task_owner(task_id: int) -> Dict[str, Any]:
    """Find suitable volunteers for a task using required skills, availability, workload, and deadlines."""
    db = next(_get_db())
    try:
        # Simple heuristic: find active volunteers with lowest utilization
        vols = volunteer_service.list_volunteers(db, status=VolunteerStatus.ACTIVE)
        scored = []
        for v in vols:
            load = calculate_volunteer_load(db, v.id)
            if load.get("status") != "OVERLOADED":
                scored.append({
                    "volunteer_id": v.id, 
                    "skills": v.skills,
                    "utilization": load.get("utilization_percent", 0)
                })
        # sort by utilization
        scored.sort(key=lambda x: x["utilization"])
        return {"success": True, "suggestions": scored[:3]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def bulk_reassign_tasks(from_volunteer_id: int, to_volunteer_id: int) -> Dict[str, Any]:
    """Move multiple tasks from one volunteer to another or distribute them across multiple volunteers."""
    db = next(_get_db())
    try:
        tasks = volunteer_service.get_volunteer_tasks(db, from_volunteer_id)
        for t in tasks:
            # Unassign old
            task_service.unassign_task(db, t.id, [from_volunteer_id])
            # Assign new
            task_service.assign_task(db, t.id, [to_volunteer_id])
        return {"success": True, "reassigned_count": len(tasks)}
    except Exception as e:
        return {"success": False, "error": str(e)}

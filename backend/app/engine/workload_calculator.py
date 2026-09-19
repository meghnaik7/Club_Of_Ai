from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.task import TaskAssignment, TaskStatus, Task

def calculate_volunteer_load(db: Session, volunteer_id: int) -> Dict[str, Any]:
    """
    Calculate the current workload of a volunteer.
    """
    volunteer = db.query(Volunteer).filter(Volunteer.id == volunteer_id).first()
    if not volunteer:
        return {"error": "Volunteer not found"}
        
    active_assignments = db.query(TaskAssignment).join(Task).filter(
        TaskAssignment.volunteer_id == volunteer_id,
        Task.status != TaskStatus.DONE
    ).all()
    
    task_count = len(active_assignments)
    # Simple metric: 1 task = 2 hours for example, or if we had duration, sum durations.
    # We use task_count and max_capacity
    estimated_load = task_count * 2 # Mock estimation
    
    capacity = volunteer.max_capacity
    utilization = (estimated_load / capacity * 100) if capacity > 0 else 0
    
    status = "OK"
    if utilization > 100:
        status = "OVERLOADED"
    elif utilization > 80:
        status = "HIGH"
        
    return {
        "volunteer_id": volunteer.id,
        "active_tasks": task_count,
        "estimated_hours": estimated_load,
        "capacity_hours": capacity,
        "utilization_percent": round(utilization, 2),
        "status": status
    }

def get_overloaded_volunteers(db: Session) -> List[Dict[str, Any]]:
    volunteers = db.query(Volunteer).filter(Volunteer.status == VolunteerStatus.ACTIVE).all()
    overloaded = []
    for v in volunteers:
        load = calculate_volunteer_load(db, v.id)
        if load.get("status") == "OVERLOADED":
            overloaded.append(load)
    return overloaded

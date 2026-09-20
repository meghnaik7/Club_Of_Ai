from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.task import Task, TaskAssignment, TaskStatus
from app.schemas.volunteer import VolunteerCreate, VolunteerUpdate

class VolunteerService:
    def create_volunteer(self, db: Session, obj_in: VolunteerCreate) -> Volunteer:
        db_obj = Volunteer(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_volunteer(self, db: Session, volunteer_id: int) -> Optional[Volunteer]:
        return db.query(Volunteer).filter(Volunteer.id == volunteer_id).first()

    def list_volunteers(
        self, db: Session, 
        skill: Optional[str] = None,
        status: Optional[VolunteerStatus] = None
    ) -> List[Volunteer]:
        query = db.query(Volunteer)
        if status:
            query = query.filter(Volunteer.status == status)
        if skill:
            query = query.filter(Volunteer.skills.ilike(f"%{skill}%"))
        return query.all()

    def update_volunteer(self, db: Session, db_obj: Volunteer, obj_in: VolunteerUpdate) -> Volunteer:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete_volunteer(self, db: Session, volunteer_id: int) -> bool:
        # Check existing tasks
        db_obj = self.get_volunteer(db, volunteer_id)
        if not db_obj:
            return False
            
        active_tasks = db.query(TaskAssignment).join(Task).filter(
            TaskAssignment.volunteer_id == volunteer_id,
            Task.status != TaskStatus.DONE
        ).count()
        
        if active_tasks > 0:
            raise ValueError(f"Cannot delete volunteer with {active_tasks} active tasks")
            
        db.delete(db_obj)
        db.commit()
        return True

    def get_volunteer_tasks(self, db: Session, volunteer_id: int) -> List[Task]:
        assignments = db.query(TaskAssignment).filter(TaskAssignment.volunteer_id == volunteer_id).all()
        return [a.task for a in assignments]

volunteer_service = VolunteerService()

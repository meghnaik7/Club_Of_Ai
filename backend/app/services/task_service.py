from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.task import Task, TaskAssignment, TaskDependency, TaskComment, TaskStatus, TaskPriority, TaskPhase
from app.models.volunteer import Volunteer
from app.schemas.task import TaskCreate, TaskUpdate, TaskCommentCreate

class TaskService:
    def create_task(self, db: Session, obj_in: TaskCreate) -> Task:
        task_data = obj_in.model_dump(exclude={"owner_ids"})
        db_obj = Task(**task_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        if obj_in.owner_ids:
            for owner_id in obj_in.owner_ids:
                assignment = TaskAssignment(task_id=db_obj.id, volunteer_id=owner_id)
                db.add(assignment)
            db.commit()
            db.refresh(db_obj)
            
        return db_obj

    def get_task(self, db: Session, task_id: int) -> Optional[Task]:
        return db.query(Task).filter(Task.id == task_id).first()

    def list_tasks(
        self, db: Session, event_id: int, 
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        phase: Optional[TaskPhase] = None,
        owner_id: Optional[int] = None
    ) -> List[Task]:
        query = db.query(Task).filter(Task.event_id == event_id)
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
        if phase:
            query = query.filter(Task.phase == phase)
        if owner_id:
            query = query.join(TaskAssignment).filter(TaskAssignment.volunteer_id == owner_id)
        return query.all()

    def update_task(self, db: Session, db_obj: Task, obj_in: TaskUpdate) -> Task:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete_task(self, db: Session, task_id: int) -> bool:
        db_obj = db.query(Task).filter(Task.id == task_id).first()
        if not db_obj:
            return False
        db.delete(db_obj)
        db.commit()
        return True

    def assign_task(self, db: Session, task_id: int, volunteer_ids: List[int]) -> Task:
        task = self.get_task(db, task_id)
        if not task:
            raise ValueError("Task not found")
            
        existing_assignments = [a.volunteer_id for a in task.assignments]
        for vid in volunteer_ids:
            if vid not in existing_assignments:
                assignment = TaskAssignment(task_id=task_id, volunteer_id=vid)
                db.add(assignment)
        db.commit()
        db.refresh(task)
        return task

    def unassign_task(self, db: Session, task_id: int, volunteer_ids: List[int]) -> Task:
        task = self.get_task(db, task_id)
        if not task:
            raise ValueError("Task not found")
            
        assignments_to_delete = db.query(TaskAssignment).filter(
            TaskAssignment.task_id == task_id,
            TaskAssignment.volunteer_id.in_(volunteer_ids)
        ).all()
        
        for a in assignments_to_delete:
            db.delete(a)
        db.commit()
        db.refresh(task)
        return task

    def change_task_status(self, db: Session, task_id: int, status: TaskStatus) -> Task:
        task = self.get_task(db, task_id)
        if not task:
            raise ValueError("Task not found")
        task.status = status
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def create_subtask(self, db: Session, parent_id: int, obj_in: TaskCreate) -> Task:
        parent = self.get_task(db, parent_id)
        if not parent:
            raise ValueError("Parent task not found")
            
        obj_in.parent_id = parent_id
        return self.create_task(db, obj_in)

    def list_subtasks(self, db: Session, parent_id: int) -> List[Task]:
        return db.query(Task).filter(Task.parent_id == parent_id).all()

    def add_task_dependency(self, db: Session, dependent_task_id: int, prerequisite_task_id: int) -> TaskDependency:
        # Check if already exists
        existing = db.query(TaskDependency).filter(
            TaskDependency.dependent_task_id == dependent_task_id,
            TaskDependency.prerequisite_task_id == prerequisite_task_id
        ).first()
        if existing:
            return existing
            
        dep = TaskDependency(
            dependent_task_id=dependent_task_id,
            prerequisite_task_id=prerequisite_task_id
        )
        db.add(dep)
        db.commit()
        db.refresh(dep)
        return dep

    def remove_task_dependency(self, db: Session, dependent_task_id: int, prerequisite_task_id: int) -> bool:
        dep = db.query(TaskDependency).filter(
            TaskDependency.dependent_task_id == dependent_task_id,
            TaskDependency.prerequisite_task_id == prerequisite_task_id
        ).first()
        if not dep:
            return False
        db.delete(dep)
        db.commit()
        return True

    def get_task_dependencies(self, db: Session, task_id: int) -> Dict[str, List[Task]]:
        task = self.get_task(db, task_id)
        if not task:
            raise ValueError("Task not found")
            
        # These need to access the related tasks correctly
        blocks = [d.dependent_task for d in task.dependencies_in] 
        # Wait, if task is prerequisite_task, it's dependencies_in on the DEPENDENT side, so for the task itself, dependencies_in is what blocks IT.
        # Actually in task.py:
        # dependencies_out = relationship("TaskDependency", foreign_keys="TaskDependency.dependent_task_id", back_populates="dependent_task")
        # dependencies_in = relationship("TaskDependency", foreign_keys="TaskDependency.prerequisite_task_id", back_populates="prerequisite_task")
        
        # So dependencies_out means this task IS the dependent_task. So it depends on prerequisite_task.
        blocked_by = [d.prerequisite_task for d in task.dependencies_out]
        
        # dependencies_in means this task IS the prerequisite_task. So it blocks dependent_task.
        blocks = [d.dependent_task for d in task.dependencies_in]
        
        return {
            "blocks": blocks,
            "blocked_by": blocked_by
        }

    def add_task_comment(self, db: Session, obj_in: TaskCommentCreate) -> TaskComment:
        comment = TaskComment(**obj_in.model_dump())
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment

    def get_task_activity(self, db: Session, task_id: int) -> List[TaskComment]:
        return db.query(TaskComment).filter(TaskComment.task_id == task_id).order_by(TaskComment.created_at.desc()).all()
        
    def get_overdue_tasks(self, db: Session, event_id: int) -> List[Task]:
        return db.query(Task).filter(
            Task.event_id == event_id,
            Task.status != TaskStatus.DONE,
            Task.due_date < datetime.utcnow()
        ).all()

task_service = TaskService()

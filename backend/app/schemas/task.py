from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from app.models.task import TaskStatus, TaskPriority, TaskPhase

# Task Comment Schemas
class TaskCommentBase(BaseModel):
    content: str

class TaskCommentCreate(TaskCommentBase):
    task_id: int
    user_id: int

class TaskCommentInDBBase(TaskCommentBase):
    id: int
    task_id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TaskComment(TaskCommentInDBBase):
    pass

# Task Assignment Schemas
class TaskAssignmentBase(BaseModel):
    volunteer_id: int

class TaskAssignmentCreate(TaskAssignmentBase):
    task_id: int

class TaskAssignmentInDBBase(TaskAssignmentBase):
    id: int
    task_id: int

    model_config = ConfigDict(from_attributes=True)

class TaskAssignment(TaskAssignmentInDBBase):
    pass

# Task Dependency Schemas
class TaskDependencyBase(BaseModel):
    prerequisite_task_id: int

class TaskDependencyCreate(TaskDependencyBase):
    dependent_task_id: int

class TaskDependencyInDBBase(TaskDependencyBase):
    id: int
    dependent_task_id: int

    model_config = ConfigDict(from_attributes=True)

class TaskDependency(TaskDependencyInDBBase):
    pass

# Task Schemas
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[TaskStatus] = TaskStatus.TODO
    priority: Optional[TaskPriority] = TaskPriority.MEDIUM
    phase: Optional[TaskPhase] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    parent_id: Optional[int] = None
    team_id: Optional[int] = None

class TaskCreate(TaskBase):
    event_id: int
    owner_ids: Optional[List[int]] = [] # Volunteer IDs to assign right away

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    phase: Optional[TaskPhase] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    parent_id: Optional[int] = None
    team_id: Optional[int] = None

class TaskInDBBase(TaskBase):
    id: int
    event_id: int
    created_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class Task(TaskInDBBase):
    assignments: List[TaskAssignment] = []
    dependencies_out: List[TaskDependency] = []
    dependencies_in: List[TaskDependency] = []
    comments: List[TaskComment] = []

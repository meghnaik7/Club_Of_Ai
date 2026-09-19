from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship, backref
import enum
from datetime import datetime

from app.db.base_class import Base

class TaskStatus(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    BLOCKED = "BLOCKED"

class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class TaskPhase(str, enum.Enum):
    PLANNING = "PLANNING"
    EXECUTION = "EXECUTION"
    POST_EVENT = "POST_EVENT"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO, nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    phase = Column(Enum(TaskPhase), nullable=True)
    start_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    parent_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    
    # Relationships
    assignments = relationship("TaskAssignment", back_populates="task", cascade="all, delete-orphan")
    subtasks = relationship("Task", backref=backref('parent', remote_side=[id]))
    dependencies_out = relationship("TaskDependency", foreign_keys="TaskDependency.dependent_task_id", back_populates="dependent_task", cascade="all, delete-orphan")
    dependencies_in = relationship("TaskDependency", foreign_keys="TaskDependency.prerequisite_task_id", back_populates="prerequisite_task", cascade="all, delete-orphan")
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")


class TaskAssignment(Base):
    __tablename__ = "task_assignments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    volunteer_id = Column(Integer, ForeignKey("volunteers.id"), nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="assignments")
    volunteer = relationship("Volunteer", back_populates="task_assignments")


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    dependent_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    prerequisite_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)

    dependent_task = relationship("Task", foreign_keys=[dependent_task_id], back_populates="dependencies_out")
    prerequisite_task = relationship("Task", foreign_keys=[prerequisite_task_id], back_populates="dependencies_in")


class TaskComment(Base):
    __tablename__ = "task_comments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="comments")
    user = relationship("User")

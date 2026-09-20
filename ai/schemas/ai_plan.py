"""
Strict Pydantic models for validating LLM-generated event plan output.
The LLM output is parsed through these models before any DB operation.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class GeneratedSubtask(BaseModel):
    title: str = Field(..., description="Short, actionable subtask title")
    is_completed: bool = Field(default=False)


class GeneratedDependency(BaseModel):
    depends_on_task_index: int = Field(
        ..., description="0-based index of the task this task depends on"
    )


class GeneratedTask(BaseModel):
    title: str = Field(..., description="Short, actionable task title")
    description: Optional[str] = Field(None, description="Detailed task description")
    phase: str = Field(
        default="PRE_EVENT",
        description="Event phase: PRE_EVENT, DAY_OF, or POST_EVENT"
    )
    priority: str = Field(
        default="MEDIUM",
        description="Task priority: LOW, MEDIUM, HIGH, or CRITICAL"
    )
    estimated_duration_hours: int = Field(
        default=4,
        description="Estimated hours to complete this task",
        ge=1
    )
    suggested_skills: List[str] = Field(
        default_factory=list,
        description="Skills recommended for the volunteer handling this task"
    )
    dependencies: List[GeneratedDependency] = Field(
        default_factory=list,
        description="List of other tasks this task depends on (by 0-based index)"
    )
    subtasks: List[GeneratedSubtask] = Field(
        default_factory=list,
        description="List of smaller subtasks under this task"
    )


class EventPlan(BaseModel):
    event_title: str = Field(..., description="Name of the event")
    event_description: str = Field(default="", description="Brief description of the event")
    venue: Optional[str] = Field(None, description="Venue or location of the event")
    expected_attendance: int = Field(default=0, ge=0)
    budget: float = Field(default=0.0, ge=0.0)
    tasks: List[GeneratedTask] = Field(
        ...,
        min_length=1,
        description="Complete ordered list of tasks to run this event"
    )

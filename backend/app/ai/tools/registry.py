"""
Tool Registry Configuration for ClubOps AI.
Populates ToolGuard._REGISTRY with strict classifications and validation schemas.
"""
from app.guardrails.tool_guard import ToolGuard, ToolClassification
from app.ai.tools import ALL_AI_TOOLS
from app.ai.schemas.guardrails import (
    CreateTaskSchema,
    UpdateTaskSchema,
    AssignTaskSchema,
    DependencySchema,
    CreateEventSchema,
)

TOOL_CLASSIFICATIONS = {
    # Tasks - Reads
    "get_task": ToolClassification.READ,
    "list_tasks": ToolClassification.READ,
    "list_subtasks": ToolClassification.READ,
    "get_task_dependencies": ToolClassification.READ,
    "get_task_activity": ToolClassification.READ,
    "calculate_critical_path": ToolClassification.READ,
    "get_overdue_tasks": ToolClassification.READ,
    
    # Tasks - Writes
    "create_task": ToolClassification.WRITE,
    "update_task": ToolClassification.WRITE,
    "assign_task": ToolClassification.WRITE,
    "unassign_task": ToolClassification.WRITE,
    "change_task_status": ToolClassification.WRITE,
    "create_subtask": ToolClassification.WRITE,
    "add_task_dependency": ToolClassification.WRITE,
    "remove_task_dependency": ToolClassification.WRITE,
    "add_task_comment": ToolClassification.WRITE,
    
    # Tasks - High Risk
    "delete_task": ToolClassification.HIGH_RISK_WRITE,
    "bulk_update_tasks": ToolClassification.HIGH_RISK_WRITE,

    # Volunteers - Reads
    "get_volunteer": ToolClassification.READ,
    "list_volunteers": ToolClassification.READ,
    "get_volunteer_tasks": ToolClassification.READ,
    "calculate_volunteer_load": ToolClassification.READ,
    "get_overloaded_volunteers": ToolClassification.READ,
    "suggest_task_owner": ToolClassification.READ,

    # Volunteers - Writes
    "create_volunteer": ToolClassification.WRITE,
    "update_volunteer": ToolClassification.WRITE,
    
    # Volunteers - High Risk
    "delete_volunteer": ToolClassification.HIGH_RISK_WRITE,
    "bulk_reassign_tasks": ToolClassification.HIGH_RISK_WRITE,

    # Events - Reads
    "get_event": ToolClassification.READ,
    "list_events": ToolClassification.READ,
    "get_event_dashboard": ToolClassification.READ,
    "get_event_timeline": ToolClassification.READ,
    "get_event_budget": ToolClassification.READ,

    # Events - Writes
    "create_event": ToolClassification.WRITE,
    "update_event": ToolClassification.WRITE,
    "record_expense": ToolClassification.WRITE,
    "update_budget_allocation": ToolClassification.WRITE,
    "generate_event_plan": ToolClassification.WRITE,

    # Events - High Risk
    "delete_event": ToolClassification.HIGH_RISK_WRITE,

    # Meetings - Reads
    "get_meeting": ToolClassification.READ,
    "list_meetings": ToolClassification.READ,
    "extract_action_items": ToolClassification.READ,
    "resolve_action_item_references": ToolClassification.READ,
    "review_extracted_actions": ToolClassification.READ,

    # Meetings - Writes
    "create_meeting": ToolClassification.WRITE,
    "update_meeting": ToolClassification.WRITE,
    "apply_extracted_actions": ToolClassification.WRITE,

    # Risks - Reads
    "list_risks": ToolClassification.READ,
    "get_risk": ToolClassification.READ,
    "detect_event_risks": ToolClassification.READ,
    "detect_task_risks": ToolClassification.READ,
    "explain_risk": ToolClassification.READ,
    "suggest_risk_fix": ToolClassification.READ,
    "get_unowned_tasks_near_deadline": ToolClassification.READ,
    "get_overload_risks": ToolClassification.READ,
    "get_dependency_conflicts": ToolClassification.READ,
    "get_missing_activity_risks": ToolClassification.READ,

    # Risks - Writes
    "resolve_risk": ToolClassification.WRITE,
}

TOOL_SCHEMAS = {
    "create_task": CreateTaskSchema,
    "update_task": UpdateTaskSchema,
    "assign_task": AssignTaskSchema,
    "add_task_dependency": DependencySchema,
    "create_event": CreateEventSchema,
}

def init_tool_registry():
    """Initializes and registers all approved tools in ToolGuard."""
    for name, handler in ALL_AI_TOOLS.items():
        classification = TOOL_CLASSIFICATIONS.get(name, ToolClassification.READ)
        schema = TOOL_SCHEMAS.get(name, None)
        ToolGuard.register_tool(
            name=name,
            description=f"ClubOps tool: {name}",
            classification=classification,
            handler=handler,
            input_schema=schema,
            requires_confirmation=classification in (ToolClassification.WRITE, ToolClassification.HIGH_RISK_WRITE)
        )

# Automatically initialize on import
init_tool_registry()

import json
from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from ai.schemas.state import AgentState
from ai.prompts.system_prompt import SUPERVISOR_PROMPT
from ai.tools.proposal_tools import (
    propose_event_plan,
    create_action_proposal,
    get_action_proposal,
    preview_action_diff,
    apply_action_proposal,
    reject_action_proposal,
    undo_action,
    get_action_audit_log
)
from ai.tools.document_tools import (
    search_documents,
    ask_documents,
    extract_document_actions,
    extract_document_decisions,
    find_relevant_past_lessons
)
from ai.tools.announcement_tools import (
    create_announcement,
    generate_announcement,
    generate_announcement_variants,
    get_announcement,
    list_announcements,
    update_announcement,
    delete_announcement
)
from ai.tools.task_planning_tools import (
    generate_task_graph,
    split_task,
    suggest_task_owner,
    reschedule_task,
    cascade_reschedule,
    detect_dependency_conflicts,
    explain_dependency_conflict
)
from ai.tools.context_tools import (
    get_event_context,
    get_task_context,
    get_volunteer_context,
    get_project_summary,
    search_tasks,
    search_volunteers,
    search_event_data
)
from ai.tools.command_tool import execute_command
try:
    from app.core.config import settings
except ImportError:
    from backend.app.core.config import settings
from langchain_openai import ChatOpenAI

# Initialize tools
tools = [
    propose_event_plan,
    create_action_proposal,
    get_action_proposal,
    preview_action_diff,
    apply_action_proposal,
    reject_action_proposal,
    undo_action,
    get_action_audit_log,
    search_documents,
    ask_documents,
    extract_document_actions,
    extract_document_decisions,
    find_relevant_past_lessons,
    create_announcement,
    generate_announcement,
    generate_announcement_variants,
    get_announcement,
    list_announcements,
    update_announcement,
    delete_announcement,
    generate_task_graph,
    split_task,
    suggest_task_owner,
    reschedule_task,
    cascade_reschedule,
    detect_dependency_conflicts,
    explain_dependency_conflict,
    get_event_context,
    get_task_context,
    get_volunteer_context,
    get_project_summary,
    search_tasks,
    search_volunteers,
    search_event_data,
    execute_command
]

tool_node = ToolNode(tools)

def _get_llm():
    if settings.OPENAI_API_KEY:
        return ChatOpenAI(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL).bind_tools(tools)
    # Mock LLM for offline testing if no key is provided
    from langchain_core.language_models import FakeListChatModel
    return FakeListChatModel(responses=["I am an offline mock assistant. Please configure OPENAI_API_KEY."]).bind_tools(tools)

def call_model(state: AgentState):
    messages = state["messages"]
    
    # Ensure system prompt is present
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + list(messages)
        
    llm = _get_llm()
    response = llm.invoke(messages)
    
    return {"messages": [response]}

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    
    if last_message.tool_calls:
        return "tools"
    return "__end__"

workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "__end__": END})
workflow.add_edge("tools", "agent")

# Compile graph statically (stateless execution)
compiled_graph = workflow.compile()

import re
import json
import logging
from typing import Literal, Optional, List, Sequence, Dict, Any

from ai.tools.compat import HumanMessage, SystemMessage, BaseMessage, AIMessage, ToolMessage

try:
    from langgraph.graph import StateGraph, START, END  # type: ignore
    from langgraph.prebuilt import ToolNode  # type: ignore
    HAS_LANGGRAPH = True
except (ImportError, Exception):
    StateGraph = None
    START = None
    END = None
    ToolNode = None
    HAS_LANGGRAPH = False

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

try:
    from app.core.config import settings
    from app.ai.llm_service import llm_service
    from app.ai.errors import classify_exception, AIError
except ImportError:
    from backend.app.core.config import settings  # type: ignore
    from backend.app.ai.llm_service import llm_service  # type: ignore
    from backend.app.ai.errors import classify_exception, AIError  # type: ignore

logger = logging.getLogger(__name__)

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
    search_event_data
]

base_tool_node = ToolNode(tools) if (HAS_LANGGRAPH and ToolNode is not None) else None


def safe_tool_node(state: AgentState) -> Dict[str, Any]:
    """Protected tool execution node catching exceptions and returning controlled state."""
    if base_tool_node is None:
        return {"messages": []}
    try:
        return base_tool_node.invoke(state)
    except Exception as exc:
        classified = classify_exception(exc)
        messages = state.get("messages") or []
        last_msg = messages[-1] if messages else None
        tool_messages = []
        tool_calls = getattr(last_msg, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                call_id = tc.get("id") or "call_err"

                tool_messages.append(ToolMessage(
                    content=f"Error executing tool: {classified.user_message}",
                    tool_call_id=call_id
                ))

        return {
            "messages": tool_messages,
            "error": {
                "code": classified.code,
                "message": classified.user_message,
                "retryable": classified.retryable,
            }
        }


def trim_messages_for_short_term_memory(messages: Sequence[BaseMessage], max_recent: int = 10) -> List[BaseMessage]:
    """
    Context Trimming: Keeps context bounded to prevent unlimited conversation growth.
    Retains the SystemMessage, a summary placeholder of trimmed messages if any,
    and the most recent turns.
    """
    if len(messages) <= max_recent:
        return list(messages)

    sys_messages = [m for m in messages if isinstance(m, SystemMessage)]
    non_sys = [m for m in messages if not isinstance(m, SystemMessage)]

    if len(non_sys) > max_recent:
        trimmed_count = len(non_sys) - max_recent
        summary_msg = SystemMessage(
            content=f"[Context Summary: {trimmed_count} earlier turn(s) trimmed for conciseness. Retaining recent active context.]"
        )
        recent_turns = non_sys[-max_recent:]
        return sys_messages + [summary_msg] + recent_turns

    return list(messages)


def resolve_context_references(user_text: str, event_name: Optional[str]) -> str:
    """
    Pronoun / reference resolution for multi-turn short-term memory.
    e.g. 'Set its budget to ₹50,000' or 'Now create tasks for it'
    resolves 'it' / 'its' to the active event name.
    """
    if not event_name or not user_text:
        return user_text

    resolved = user_text
    # Check for pronoun references: "for it", "its budget", "about it"
    resolved = re.sub(r"(?i)\bfor\s+it\b", f"for {event_name}", resolved)
    resolved = re.sub(r"(?i)\bits\s+", f"{event_name}'s ", resolved)
    resolved = re.sub(r"(?i)\bto\s+it\b", f"to {event_name}", resolved)
    return resolved


def call_model(state: AgentState) -> Dict[str, Any]:
    messages = list(state.get("messages") or [])
    user_id = state.get("user_id")
    event_id = state.get("active_event_id")
    event_name = state.get("active_event_name")
    club_id = state.get("club_id")
    iter_count = state.get("iteration_count", 0) or 0
    max_iters = int(getattr(settings, "MAX_AGENT_ITERATIONS", 10))

    # Guardrail 16 & Section 14: Agent Loop Protection
    if iter_count >= max_iters:
        err_msg = AIMessage(content="I couldn't safely complete the operation within the allowed number of steps.")
        return {
            "messages": [err_msg],
            "error": {
                "code": "AGENT_MAX_ITERATIONS",
                "message": "Maximum agent reasoning iterations reached.",
                "retryable": False,
                "fallback_used": False,
            },
            "iteration_count": iter_count + 1
        }

    # 1. Pronoun and entity reference resolution across turns
    last_human_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            last_human_idx = i
            break

    detected_event_name = event_name
    if last_human_idx >= 0:
        latest_text = messages[last_human_idx].content
        # Detect if user is creating or referencing a named event:
        ev_match = re.search(r"(?i)(?:create|plan|organize|schedule)\s+(?:an?\s+)?event\s+(?:called\s+|named\s+)?['\"]?([A-Za-z0-9_\s]+?)['\"]?(?:\.|$|,|\s+with)", latest_text)
        if ev_match:
            detected_event_name = ev_match.group(1).strip()

        if detected_event_name:
            resolved_text = resolve_context_references(latest_text, detected_event_name)
            if resolved_text != latest_text:
                # Update last human message with resolved reference
                new_msg = HumanMessage(content=resolved_text)
                messages = list(messages[:last_human_idx]) + [new_msg] + list(messages[last_human_idx+1:])

    # 2. Context Trimming (Short-Term Memory bounded growth)
    trimmed_messages = trim_messages_for_short_term_memory(messages, max_recent=10)

    # 3. Long-Term Memory Injection (pre-turn scoped retrieval)
    memory_context = ""
    try:
        try:
            from app.db.session import SessionLocal
            from app.agents.memory_manager import MemoryManager
        except ImportError:
            from backend.app.db.session import SessionLocal  # type: ignore
            from backend.app.agents.memory_manager import MemoryManager  # type: ignore

        db = SessionLocal()
        try:
            query_str = messages[last_human_idx].content if last_human_idx >= 0 else ""
            if query_str:
                memory_context = MemoryManager.get_scoped_memory_context(
                    db=db,
                    query=query_str,
                    user_id=user_id,
                    club_id=club_id,
                    event_id=event_id,
                    top_k=3
                )
        finally:
            db.close()
    except Exception:
        # Memory retrieval failure does NOT crash the agent
        memory_context = ""

    # Ensure system prompt is present with long-term memory facts if available
    sys_prompt = SUPERVISOR_PROMPT
    if memory_context:
        sys_prompt += "\n" + memory_context

    if not any(isinstance(m, SystemMessage) for m in trimmed_messages):
        trimmed_messages = [SystemMessage(content=sys_prompt)] + list(trimmed_messages)
    else:
        # Update existing system message
        for i, m in enumerate(trimmed_messages):
            if isinstance(m, SystemMessage):
                trimmed_messages[i] = SystemMessage(content=sys_prompt)
                break

    # 4. Centralized LLM Service Invocation
    try:
        llm_resp = llm_service.invoke(
            prompt=trimmed_messages,
            tools=tools,
            correlation_id=state.get("thread_id"),
            user_id=user_id,
            event_id=event_id,
        )
        response = llm_resp.to_chat_message()
        fallback_used = llm_resp.fallback_used
        error_info = None
    except Exception as exc:
        classified = classify_exception(exc)
        response = AIMessage(content=classified.user_message)
        fallback_used = False
        error_info = {
            "code": classified.code,
            "message": classified.user_message,
            "retryable": classified.retryable,
            "fallback_used": False,
        }

    return {
        "messages": [response],
        "active_event_name": detected_event_name,
        "fallback_used": fallback_used,
        "error": error_info,
        "iteration_count": iter_count + 1
    }


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    # Stop immediately if an unrecoverable error occurred
    if state.get("error"):
        return "__end__"

    iter_count = state.get("iteration_count", 0) or 0
    max_iters = int(getattr(settings, "MAX_AGENT_ITERATIONS", 10))
    if iter_count >= max_iters:
        return "__end__"

    messages = state.get("messages") or []
    last_message = messages[-1] if messages else None

    tool_calls = getattr(last_message, "tool_calls", None)
    if tool_calls:
        return "tools"
    return "__end__"



if HAS_LANGGRAPH and StateGraph is not None and START is not None and END is not None:
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", safe_tool_node)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "__end__": END})
    workflow.add_edge("tools", "agent")

    try:
        from langgraph.checkpoint.memory import MemorySaver  # type: ignore
        memory_checkpointer = MemorySaver()
    except (ImportError, Exception):
        memory_checkpointer = None

    if memory_checkpointer is not None:
        compiled_graph = workflow.compile(checkpointer=memory_checkpointer)
    else:
        compiled_graph = workflow.compile()
else:
    class FallbackCompiledGraph:
        def __init__(self):
            self._threads: Dict[str, Any] = {}

        def get_state(self, config: Optional[Dict[str, Any]]):
            thread_id = (config or {}).get("configurable", {}).get("thread_id", "default")
            class CheckpointState:
                def __init__(self, values):
                    self.values = values
            return CheckpointState(self._threads.get(thread_id, {"messages": []}))

        def invoke(self, state: Dict[str, Any], *args, config: Optional[Dict[str, Any]] = None, **kwargs):
            thread_id = (config or {}).get("configurable", {}).get("thread_id") or state.get("thread_id", "default")
            existing = self._threads.get(thread_id, {"messages": []})
            all_messages = list(existing.get("messages", [])) + list(state.get("messages", []))
            curr_state: Dict[str, Any] = dict(state)
            curr_state["messages"] = all_messages

            result = call_model(curr_state)  # type: ignore

            out_messages = all_messages + list(result.get("messages", []))
            saved_state = dict(curr_state)
            saved_state.update(result)
            saved_state["messages"] = out_messages
            self._threads[thread_id] = saved_state
            return saved_state

    compiled_graph = FallbackCompiledGraph()
    memory_checkpointer = None


def get_thread_config(thread_id: str, user_id: Optional[int] = None):
    """Returns runtime execution config for thread checkpointer persistence."""
    cfg = {"configurable": {"thread_id": str(thread_id)}}
    if user_id is not None:
        cfg["configurable"]["user_id"] = str(user_id)
    return cfg

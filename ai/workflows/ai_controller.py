from typing import Optional
try:
    from langchain_core.messages import HumanMessage
except ImportError:
    from ai.tools.compat import HumanMessage
from ai.agents.graph import compiled_graph, get_thread_config
from ai.observability import traceable


@traceable(name="run_ai_command", run_type="chain")
def run_ai_command(
    user_id: int,
    command: str,
    active_event_id: Optional[int] = None,
    thread_id: Optional[str] = None,
    club_id: Optional[int] = None
) -> dict:
    """
    Entry point to run the AI agent given a user command with short-term thread persistence,
    LangSmith observability, and long-term memory extraction.
    """
    effective_thread_id = thread_id or f"user-thread-{user_id}"
    config = get_thread_config(thread_id=effective_thread_id, user_id=user_id)

    # Attach observability metadata
    config["run_name"] = f"AI Command (User {user_id})"
    config["tags"] = ["agent", "clubops", f"user:{user_id}"]
    config["metadata"] = {
        "user_id": user_id,
        "active_event_id": active_event_id,
        "command": command,
        "thread_id": effective_thread_id
    }

    initial_state = {
        "messages": [HumanMessage(content=command)],
        "user_id": user_id,
        "proposal_ids": [],
        "active_event_id": active_event_id,
        "active_event_name": None,
        "active_task_id": None,
        "club_id": club_id,
        "thread_id": effective_thread_id,
        "retrieved_memories": []
    }

    # Run the graph with checkpointer and observability config
    result = compiled_graph.invoke(initial_state, config=config)

    messages = result.get("messages", [])
    response_text = "No response generated."

    if messages:
        last_message = messages[-1]
        response_text = last_message.content

    # Post-execution Long-Term Memory extraction
    try:
        from app.db.session import SessionLocal
        from app.agents.memory_manager import MemoryManager
        db = SessionLocal()
        try:
            MemoryManager.process_turn(
                db=db,
                user_message=command,
                assistant_message=response_text,
                user_id=user_id,
                event_id=active_event_id,
                club_id=club_id
            )
        finally:
            db.close()
    except Exception:
        pass

    return {
        "response": response_text,
        "proposals": result.get("proposal_ids", []),
        "thread_id": effective_thread_id,
        "active_event_name": result.get("active_event_name")
    }


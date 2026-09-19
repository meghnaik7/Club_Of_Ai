try:
    from langchain_core.messages import HumanMessage
except ImportError:
    from ai.tools.compat import HumanMessage
from ai.agents.graph import compiled_graph
from ai.observability import traceable

@traceable(name="run_ai_command", run_type="chain")
def run_ai_command(user_id: int, command: str, active_event_id: int = None) -> dict:
    """
    Entry point to run the AI agent given a user command.
    Stateless execution with LangSmith observability.
    """
    initial_state = {
        "messages": [HumanMessage(content=command)],
        "user_id": user_id,
        "proposal_ids": [],
        "active_event_id": active_event_id
    }
    
    config = {
        "run_name": f"AI Command (User {user_id})",
        "tags": ["agent", "clubops", f"user:{user_id}"],
        "metadata": {
            "user_id": user_id,
            "active_event_id": active_event_id,
            "command": command
        }
    }
    
    # Run the graph with LangSmith observability config
    result = compiled_graph.invoke(initial_state, config=config)
    
    messages = result.get("messages", [])
    response_text = "No response generated."
    
    if messages:
        last_message = messages[-1]
        response_text = last_message.content
        
    return {
        "response": response_text,
        "proposals": result.get("proposal_ids", [])
    }

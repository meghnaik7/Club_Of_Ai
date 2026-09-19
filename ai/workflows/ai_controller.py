try:
    from langchain_core.messages import HumanMessage
except ImportError:
    from ai.tools.compat import HumanMessage
from ai.agents.graph import compiled_graph

def run_ai_command(user_id: int, command: str, active_event_id: int = None) -> dict:
    """
    Entry point to run the AI agent given a user command.
    Stateless execution.
    """
    initial_state = {
        "messages": [HumanMessage(content=command)],
        "user_id": user_id,
        "proposal_ids": [],
        "active_event_id": active_event_id
    }
    
    # Run the graph
    result = compiled_graph.invoke(initial_state)
    
    messages = result.get("messages", [])
    response_text = "No response generated."
    
    if messages:
        last_message = messages[-1]
        response_text = last_message.content
        
    return {
        "response": response_text,
        "proposals": result.get("proposal_ids", [])
    }

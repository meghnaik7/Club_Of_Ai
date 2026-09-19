from typing import TypedDict, Annotated, Sequence, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage
from operator import add
from pydantic import BaseModel, Field


class AgentError(BaseModel):
    """Normalized structured error representation within AgentState."""
    code: str
    message: str
    retryable: bool = False
    fallback_used: bool = False
    details: Optional[Dict[str, Any]] = None


class AgentState(TypedDict, total=False):
    """
    State for the ClubOps AI Agent (Short-Term Memory).
    - messages: Conversation history and turns.
    - user_id: The ID of the user executing the command.
    - proposal_ids: List of AIProposal IDs generated during this execution.
    - active_event_id: The ID of the event currently in context.
    - active_event_name: The name of the event in context (for pronoun resolution).
    - active_task_id: Current task ID in context.
    - club_id: Current club ID context.
    - thread_id: Conversation / thread ID for session persistence.
    - retrieved_memories: Long-term memory facts retrieved for the current turn.
    - error: Controlled agent error status if any step encounters issues.
    - fallback_used: Whether a fallback model was used during this workflow turn.
    - iteration_count: Current count of agent loop cycles.
    - tool_call_count: Number of tool calls invoked in this execution.
    """
    messages: Annotated[Sequence[BaseMessage], add]
    user_id: int
    proposal_ids: Annotated[list[int], add]
    active_event_id: Optional[int]
    active_event_name: Optional[str]
    active_task_id: Optional[int]
    club_id: Optional[int]
    thread_id: Optional[str]
    retrieved_memories: Optional[List[Dict[str, Any]]]
    error: Optional[Dict[str, Any]]
    fallback_used: Optional[bool]
    iteration_count: Optional[int]
    tool_call_count: Optional[int]

from typing import TypedDict, Annotated, Sequence
try:
    from langchain_core.messages import BaseMessage
except ImportError:
    from ai.tools.compat import BaseMessage
from operator import add

class AgentState(TypedDict):
    """
    State for the ClubOps AI Agent.
    - messages: Holds the conversation history and current command.
    - user_id: The ID of the user executing the command.
    - proposal_ids: List of AIProposal IDs generated during this execution.
    - active_event_id: The ID of the event currently in context (if any).
    """
    messages: Annotated[Sequence[BaseMessage], add]
    user_id: int
    proposal_ids: Annotated[list[int], add]
    active_event_id: int | None

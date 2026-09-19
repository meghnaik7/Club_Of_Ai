from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Optional, List, Dict
from pydantic import BaseModel

from app.api import deps
from app.models.user import User

router = APIRouter()

class AICommandRequest(BaseModel):
    command: str
    active_event_id: Optional[int] = None
    confirm_proposal_id: Optional[int] = None
    auto_confirm: Optional[bool] = False

class AICommandResponse(BaseModel):
    response: str
    proposals: List[int] = []
    status: Optional[str] = "COMPLETED"
    details: Optional[Dict[str, Any]] = None

@router.post("/", response_model=AICommandResponse)
def execute_ai_command(
    request: AICommandRequest,
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """
    Execute a natural language command via the AI Agent.
    Interprets user intent, retrieves context, stages proposals, and applies changes upon confirmation.
    """
    try:
        from ai.tools.command_tool import execute_command
        user_id = current_user.id if current_user else 1
        result = execute_command.invoke({
            "command": request.command,
            "active_event_id": request.active_event_id,
            "user_id": user_id,
            "confirm_proposal_id": request.confirm_proposal_id,
            "auto_confirm": request.auto_confirm or False
        })
        
        proposals = []
        if result.get("proposal_id"):
            proposals.append(result["proposal_id"])
        elif result.get("result") and isinstance(result["result"], dict) and result["result"].get("proposals"):
            proposals = result["result"]["proposals"]
            
        return AICommandResponse(
            response=result.get("message") or str(result.get("result", "Command executed successfully.")),
            proposals=proposals,
            status=result.get("status", "COMPLETED"),
            details=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

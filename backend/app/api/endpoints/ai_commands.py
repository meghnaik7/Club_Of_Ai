from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Optional, List, Dict
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.models.chat_history import RAGChatHistory
from app.ai.errors import classify_exception

router = APIRouter()

class AICommandRequest(BaseModel):
    command: str
    active_event_id: Optional[int] = None
    confirm_proposal_id: Optional[int] = None
    auto_confirm: Optional[bool] = False
    thread_id: Optional[str] = None

class AICommandResponse(BaseModel):
    response: str
    proposals: List[int] = []
    status: Optional[str] = "COMPLETED"
    details: Optional[Dict[str, Any]] = None
    thread_id: Optional[str] = None
    fallback_used: Optional[bool] = False

@router.get("/history")
def get_chat_history(
    active_event_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """Returns past asked questions and answers for the user / active event."""
    query = db.query(RAGChatHistory)
    if current_user:
        query = query.filter(RAGChatHistory.user_id == current_user.id)
    if active_event_id is not None:
        query = query.filter(RAGChatHistory.event_id == active_event_id)
    records = query.order_by(RAGChatHistory.created_at.asc()).limit(limit).all()
    return {
        "items": [
            {
                "id": str(r.id),
                "question": r.question,
                "answer": r.answer,
                "citations": r.citations or [],
                "status": r.status,
                "proposals": r.proposal_ids or [],
                "event_id": r.event_id,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in records
        ],
        "total": len(records)
    }

@router.delete("/history")
def clear_chat_history(
    active_event_id: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """Clears past chat history for the user."""
    query = db.query(RAGChatHistory)
    if current_user:
        query = query.filter(RAGChatHistory.user_id == current_user.id)
    if active_event_id is not None:
        query = query.filter(RAGChatHistory.event_id == active_event_id)
    count = query.delete(synchronize_session=False)
    db.commit()
    return {"ok": True, "deleted_count": count}

@router.post("/", response_model=AICommandResponse)
def execute_ai_command(
    request: AICommandRequest,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """
    Execute a natural language command via the AI Agent.
    Interprets user intent, retrieves context, stages proposals, applies changes upon confirmation,
    and persists chat turn history.
    """
    try:
        from ai.tools.command_tool import execute_command
        user_id = current_user.id if current_user else 1
        result = execute_command.invoke({
            "command": request.command,
            "active_event_id": request.active_event_id,
            "user_id": user_id,
            "confirm_proposal_id": request.confirm_proposal_id,
            "auto_confirm": request.auto_confirm or False,
            "thread_id": request.thread_id
        })
        
        proposals = []
        if result.get("proposal_id"):
            proposals.append(result["proposal_id"])
        elif result.get("result") and isinstance(result["result"], dict) and result["result"].get("proposals"):
            proposals = result["result"]["proposals"]
            
        answer_text = result.get("message") or str(result.get("result", "Command executed successfully."))
        status_val = result.get("status", "COMPLETED")
        effective_thread_id = result.get("thread_id") or request.thread_id
        fallback_used = bool(result.get("fallback_used", False))

        # Persist Q&A turn into RAGChatHistory safely
        if hasattr(db, "add") and hasattr(db, "commit"):
            try:
                history_entry = RAGChatHistory(
                    user_id=current_user.id if current_user else None,
                    event_id=request.active_event_id,
                    question=request.command,
                    answer=answer_text,
                    status=status_val,
                    proposal_ids=proposals
                )
                db.add(history_entry)
                db.commit()
            except Exception:
                if hasattr(db, "rollback"):
                    db.rollback()

        return AICommandResponse(
            response=answer_text,
            proposals=proposals,
            status=status_val,
            details=result,
            thread_id=effective_thread_id,
            fallback_used=fallback_used
        )
    except Exception as e:
        ai_err = classify_exception(e)
        raise HTTPException(
            status_code=ai_err.status_code,
            detail=ai_err.to_user_dict()["error"]
        )


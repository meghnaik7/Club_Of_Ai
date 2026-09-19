from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.memory.schemas import (
    MemoryResponse, MemoryListResponse, MemoryCreate, MemoryUpdate, MemoryCandidate
)
from app.memory.repository import MemoryRepository
from app.memory.service import MemoryService

router = APIRouter()

@router.get("/", response_model=MemoryListResponse)
def list_memories(
    club_id: Optional[int] = None,
    event_id: Optional[int] = None,
    memory_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """
    List long-term memories strictly scoped to the authenticated user and event/club context.
    """
    user_id = current_user.id if current_user else None
    records, total = MemoryRepository.list_scoped(
        db=db,
        user_id=user_id,
        club_id=club_id,
        event_id=event_id,
        memory_type=memory_type,
        limit=limit,
        offset=offset
    )
    return {
        "items": records,
        "total": total
    }

@router.get("/preferences", response_model=MemoryListResponse)
def get_user_preferences(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get active user preferences and working preferences for the current authenticated user.
    """
    records, total = MemoryRepository.list_scoped(
        db=db,
        user_id=current_user.id,
        memory_type=None,
        limit=100
    )
    # Filter preferences
    pref_items = [
        r for r in records
        if r.memory_type in ("USER_PREFERENCE", "WORKING_PREFERENCE")
    ]
    return {
        "items": pref_items,
        "total": len(pref_items)
    }

@router.get("/relevant", response_model=List[dict])
def get_relevant_memories(
    query: str = Query(..., min_length=1),
    club_id: Optional[int] = None,
    event_id: Optional[int] = None,
    top_k: int = Query(5, ge=1, le=20),
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """
    Retrieve top relevant memories for a query using hybrid scoring and strict scoping.
    """
    user_id = current_user.id if current_user else None
    return MemoryService.retrieve_relevant_memories(
        db=db,
        query=query,
        user_id=user_id,
        club_id=club_id,
        event_id=event_id,
        top_k=top_k
    )

@router.post("/", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
def create_memory(
    candidate: MemoryCandidate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Explicitly request candidate memory storage. Passes through validation and guardrails.
    """
    result = MemoryService.process_candidate(
        db=db,
        candidate=candidate,
        user_id=current_user.id
    )
    if result.get("action") == "IGNORE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Memory rejected by policy: {result.get('reason')}"
        )
    return result["memory"]

@router.put("/{memory_id}", response_model=MemoryResponse)
def update_memory(
    memory_id: int,
    obj_in: MemoryUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update or correct an existing memory. User can only edit their own memories unless admin.
    """
    mem = MemoryRepository.get_by_id(db, memory_id)
    if not mem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    # Authorization check
    if mem.user_id and mem.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this memory")

    # Validate updated content if provided
    if obj_in.content:
        from app.memory.guardrails import MemoryGuardrails
        is_valid, err = MemoryGuardrails.validate_candidate(obj_in.content)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    embedding = None
    if obj_in.content:
        from ai.rag.embeddings import generate_embedding
        embedding = generate_embedding(obj_in.content)

    return MemoryRepository.update(db, mem, obj_in, embedding)

@router.delete("/{memory_id}")
def delete_memory(
    memory_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Delete a stored memory.
    """
    mem = MemoryRepository.get_by_id(db, memory_id)
    if not mem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    # Authorization check
    if mem.user_id and mem.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this memory")

    success = MemoryRepository.delete(db, memory_id)
    return {"ok": success, "deleted_id": memory_id}

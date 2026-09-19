from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from app.memory.models import Memory
from app.memory.schemas import MemoryCreate, MemoryUpdate

class MemoryRepository:
    """Repository handling CRUD operations for the Memory database model."""

    @staticmethod
    def get_by_id(db: Session, memory_id: int) -> Optional[Memory]:
        return db.query(Memory).filter(Memory.id == memory_id).first()

    @staticmethod
    def create(db: Session, obj_in: MemoryCreate, embedding: Optional[List[float]] = None) -> Memory:
        db_obj = Memory(
            user_id=obj_in.user_id,
            club_id=obj_in.club_id,
            event_id=obj_in.event_id,
            memory_type=obj_in.memory_type,
            scope=obj_in.scope,
            content=obj_in.content,
            structured_data=obj_in.structured_data,
            importance=obj_in.importance,
            confidence=obj_in.confidence,
            source=obj_in.source,
            embedding=embedding,
            expires_at=obj_in.expires_at
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def update(db: Session, db_obj: Memory, obj_in: MemoryUpdate, embedding: Optional[List[float]] = None) -> Memory:
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        if embedding is not None:
            db_obj.embedding = embedding
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def delete(db: Session, memory_id: int) -> bool:
        db_obj = db.query(Memory).filter(Memory.id == memory_id).first()
        if db_obj:
            db.delete(db_obj)
            db.commit()
            return True
        return False

    @staticmethod
    def list_scoped(
        db: Session,
        user_id: Optional[int] = None,
        club_id: Optional[int] = None,
        event_id: Optional[int] = None,
        memory_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Memory], int]:
        query = db.query(Memory)

        filters = []
        if user_id is not None:
            filters.append(Memory.user_id == user_id)
        if club_id is not None:
            filters.append(Memory.club_id == club_id)
        if event_id is not None:
            filters.append(Memory.event_id == event_id)

        if filters:
            query = query.filter(or_(*filters))

        if memory_type:
            query = query.filter(Memory.memory_type == memory_type)

        total = query.count()
        records = query.order_by(desc(Memory.updated_at)).offset(offset).limit(limit).all()
        return records, total

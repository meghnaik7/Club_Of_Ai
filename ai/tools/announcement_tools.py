try:
    from langchain_core.tools import tool
except ImportError:
    from ai.tools.compat import tool
from typing import Optional, List, Dict, Any
import json

try:
    from app.db.session import SessionLocal
    from app.services import announcement_service
except ImportError:
    from backend.app.db.session import SessionLocal
    from backend.app.services import announcement_service

@tool
def create_announcement(title: str, content: str, event_id: Optional[int] = None, target_audience: Optional[str] = None) -> dict:
    """Create an announcement draft for an event."""
    db = SessionLocal()
    try:
        announcement = announcement_service.create_announcement(
            db=db,
            title=title,
            content=content,
            event_id=event_id,
            target_audience=target_audience
        )
        return {
            "id": announcement.id,
            "title": announcement.title,
            "content": announcement.content,
            "event_id": announcement.event_id,
            "status": announcement.status,
            "target_audience": announcement.target_audience,
            "created_at": str(announcement.created_at)
        }
    finally:
        db.close()

@tool
def generate_announcement(event_id: int, tone: Optional[str] = "engaging", target_audience: Optional[str] = None) -> dict:
    """Generate announcement content using live event information."""
    db = SessionLocal()
    try:
        return announcement_service.generate_announcement(
            db=db,
            event_id=event_id,
            tone=tone or "engaging",
            target_audience=target_audience
        )
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@tool
def generate_announcement_variants(announcement_id: Optional[int] = None, content: Optional[str] = None, event_id: Optional[int] = None) -> dict:
    """Generate variants for WhatsApp, email, and Instagram."""
    db = SessionLocal()
    try:
        return announcement_service.generate_announcement_variants(
            db=db,
            content=content,
            event_id=event_id,
            announcement_id=announcement_id
        )
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@tool
def get_announcement(announcement_id: int) -> dict:
    """Retrieve an announcement draft."""
    db = SessionLocal()
    try:
        announcement = announcement_service.get_announcement(db, announcement_id)
        if not announcement:
            return {"error": f"Announcement with ID {announcement_id} not found"}
        variants_data = None
        if announcement.variants:
            try:
                variants_data = json.loads(announcement.variants)
            except Exception:
                variants_data = announcement.variants
        return {
            "id": announcement.id,
            "title": announcement.title,
            "content": announcement.content,
            "event_id": announcement.event_id,
            "target_audience": announcement.target_audience,
            "status": announcement.status,
            "variants": variants_data,
            "created_at": str(announcement.created_at),
            "updated_at": str(announcement.updated_at)
        }
    finally:
        db.close()

@tool
def list_announcements(event_id: Optional[int] = None) -> list:
    """Retrieve previous announcements for an event."""
    db = SessionLocal()
    try:
        announcements = announcement_service.list_announcements(db, event_id=event_id)
        return [
            {
                "id": a.id,
                "title": a.title,
                "content": a.content[:100] + "..." if len(a.content) > 100 else a.content,
                "event_id": a.event_id,
                "status": a.status,
                "target_audience": a.target_audience,
                "created_at": str(a.created_at)
            }
            for a in announcements
        ]
    finally:
        db.close()

@tool
def update_announcement(announcement_id: int, title: Optional[str] = None, content: Optional[str] = None, status: Optional[str] = None) -> dict:
    """Modify announcement content before sending/copying."""
    db = SessionLocal()
    try:
        announcement = announcement_service.update_announcement(
            db=db,
            announcement_id=announcement_id,
            title=title,
            content=content,
            status=status
        )
        if not announcement:
            return {"error": f"Announcement with ID {announcement_id} not found"}
        return {
            "id": announcement.id,
            "title": announcement.title,
            "content": announcement.content,
            "status": announcement.status,
            "updated_at": str(announcement.updated_at)
        }
    finally:
        db.close()

@tool
def delete_announcement(announcement_id: int) -> dict:
    """Delete an announcement draft."""
    db = SessionLocal()
    try:
        success = announcement_service.delete_announcement(db, announcement_id)
        if not success:
            return {"error": f"Announcement with ID {announcement_id} not found"}
        return {"success": True, "message": f"Announcement {announcement_id} deleted successfully"}
    finally:
        db.close()

from typing import List, Dict, Any, Optional
from datetime import datetime
from app.db.session import SessionLocal
from app.services.meeting_service import meeting_service
from app.schemas.meeting import MeetingCreate, MeetingUpdate

def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_meeting(
    event_id: int,
    title: str,
    date: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    raw_notes: Optional[str] = None,
    transcript: Optional[str] = None
) -> Dict[str, Any]:
    """Create a meeting record with date, event, attendees, and raw notes/transcript."""
    db = next(_get_db())
    try:
        parsed_date = datetime.fromisoformat(date) if date else datetime.utcnow()
        meeting_in = MeetingCreate(
            event_id=event_id,
            title=title,
            date=parsed_date,
            location=location,
            attendees=attendees or [],
            raw_notes=raw_notes,
            transcript=transcript
        )
        meeting = meeting_service.create_meeting(db, meeting_in)
        return {
            "success": True,
            "meeting_id": meeting.id,
            "event_id": meeting.event_id,
            "title": meeting.title,
            "date": meeting.date.isoformat() if meeting.date else None,
            "location": meeting.location,
            "attendees": meeting.attendees,
            "has_notes": bool(meeting.raw_notes),
            "has_transcript": bool(meeting.transcript)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_meeting(meeting_id: int) -> Dict[str, Any]:
    """Retrieve meeting details, notes, attendees, and extracted action items."""
    db = next(_get_db())
    try:
        meeting = meeting_service.get_meeting(db, meeting_id)
        if not meeting:
            return {"success": False, "error": f"Meeting {meeting_id} not found"}

        return {
            "success": True,
            "meeting": {
                "id": meeting.id,
                "event_id": meeting.event_id,
                "title": meeting.title,
                "date": meeting.date.isoformat() if meeting.date else None,
                "location": meeting.location,
                "attendees": meeting.attendees,
                "raw_notes": meeting.raw_notes,
                "transcript": meeting.transcript,
                "action_items": [
                    {
                        "id": item.id,
                        "title": item.title,
                        "raw_text": item.raw_text,
                        "owner": item.suggested_owner_name,
                        "resolved_volunteer_id": item.resolved_volunteer_id,
                        "due_date_raw": item.due_date_raw,
                        "confidence": item.confidence,
                        "status": item.status,
                        "applied_task_id": item.applied_task_id
                    }
                    for item in meeting.action_items
                ]
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_meetings(event_id: int) -> Dict[str, Any]:
    """Retrieve meetings associated with an event."""
    db = next(_get_db())
    try:
        meetings = meeting_service.list_meetings(db, event_id)
        return {
            "success": True,
            "event_id": event_id,
            "count": len(meetings),
            "meetings": [
                {
                    "id": m.id,
                    "title": m.title,
                    "date": m.date.isoformat() if m.date else None,
                    "location": m.location,
                    "attendee_count": len(m.attendees) if m.attendees else 0,
                    "action_item_count": len(m.action_items)
                }
                for m in meetings
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def update_meeting(
    meeting_id: int,
    title: Optional[str] = None,
    date: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    raw_notes: Optional[str] = None,
    transcript: Optional[str] = None
) -> Dict[str, Any]:
    """Modify meeting date, attendees, notes, or transcript."""
    db = next(_get_db())
    try:
        meeting = meeting_service.get_meeting(db, meeting_id)
        if not meeting:
            return {"success": False, "error": f"Meeting {meeting_id} not found"}

        update_dict = {}
        if title is not None: update_dict["title"] = title
        if date is not None: update_dict["date"] = datetime.fromisoformat(date)
        if location is not None: update_dict["location"] = location
        if attendees is not None: update_dict["attendees"] = attendees
        if raw_notes is not None: update_dict["raw_notes"] = raw_notes
        if transcript is not None: update_dict["transcript"] = transcript

        meeting_in = MeetingUpdate(**update_dict)
        updated = meeting_service.update_meeting(db, meeting, meeting_in)
        return {
            "success": True,
            "meeting_id": updated.id,
            "title": updated.title,
            "date": updated.date.isoformat() if updated.date else None,
            "location": updated.location
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def extract_action_items(
    meeting_id: int,
    raw_notes: Optional[str] = None,
    transcript: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze meeting notes/transcript and identify potential action items, owners, and deadlines."""
    db = next(_get_db())
    try:
        items = meeting_service.extract_action_items(
            db=db,
            meeting_id=meeting_id,
            raw_notes=raw_notes,
            transcript=transcript
        )
        return {
            "success": True,
            "meeting_id": meeting_id,
            "extracted_count": len(items),
            "action_items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "raw_text": item.raw_text,
                    "owner": item.suggested_owner_name,
                    "due_date_raw": item.due_date_raw,
                    "suggested_due_date": item.suggested_due_date.isoformat() if item.suggested_due_date else None,
                    "confidence": item.confidence,
                    "status": item.status
                }
                for item in items
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def resolve_action_item_references(meeting_id: int) -> Dict[str, Any]:
    """Match informal references such as 'Riya will handle sponsors' to actual volunteers and tasks."""
    db = next(_get_db())
    try:
        resolved = meeting_service.resolve_action_item_references(db, meeting_id)
        return {
            "success": True,
            "meeting_id": meeting_id,
            "resolved_count": len(resolved),
            "resolutions": [item.model_dump() for item in resolved]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def review_extracted_actions(meeting_id: int) -> Dict[str, Any]:
    """Return extracted action items with confidence scores before applying them."""
    db = next(_get_db())
    try:
        items = meeting_service.review_extracted_actions(db, meeting_id)
        return {
            "success": True,
            "meeting_id": meeting_id,
            "pending_count": sum(1 for i in items if i["status"] == "PENDING"),
            "action_items": items
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def apply_extracted_actions(
    meeting_id: int,
    action_item_ids: Optional[List[int]] = None
) -> Dict[str, Any]:
    """Convert approved extracted action items into real event tasks."""
    db = next(_get_db())
    try:
        res = meeting_service.apply_extracted_actions(
            db=db,
            meeting_id=meeting_id,
            action_item_ids=action_item_ids
        )
        return {
            "success": True,
            "meeting_id": meeting_id,
            "applied_count": res.applied_count,
            "created_tasks": res.created_tasks
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

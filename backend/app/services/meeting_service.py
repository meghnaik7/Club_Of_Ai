import re
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.meeting import Meeting, MeetingActionItem
from app.models.event import Event
from app.models.volunteer import Volunteer
from app.models.user import User
from app.models.task import Task, TaskPriority, TaskStatus, TaskPhase
from app.schemas.meeting import (
    MeetingCreate,
    MeetingUpdate,
    MeetingActionItemCreate,
    MeetingActionItemUpdate,
    ActionItemExtractionResponse,
    ResolvedReferenceItem,
    ApplyActionItemsResponse
)
from app.services.task_service import task_service
from app.schemas.task import TaskCreate
from app.core.config import settings

genai_client = None
if getattr(settings, "GEMINI_API_KEY", None):
    try:
        from google import genai
        genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception:
        genai_client = None


def parse_relative_date(raw_date_str: str, base_date: Optional[datetime] = None) -> Optional[datetime]:
    """Parse relative date words (e.g., 'Friday', 'tomorrow', 'next Monday', or YYYY-MM-DD)."""
    if not raw_date_str:
        return None
    base = base_date or datetime.utcnow()
    raw = raw_date_str.strip().lower()

    # Try ISO or standard format first
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass

    if "today" in raw:
        return base
    if "tomorrow" in raw:
        return base + timedelta(days=1)
    if "end of week" in raw or "eow" in raw:
        days_ahead = 4 - base.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return base + timedelta(days=days_ahead)

    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }
    for day_name, day_num in weekdays.items():
        if day_name in raw:
            days_ahead = day_num - base.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return base + timedelta(days=days_ahead)

    return base + timedelta(days=3) # Default conservative due date estimate


class MeetingService:
    def create_meeting(self, db: Session, obj_in: MeetingCreate) -> Meeting:
        event = db.query(Event).filter(Event.id == obj_in.event_id).first()
        if not event:
            raise ValueError(f"Event with ID {obj_in.event_id} not found")

        meeting = Meeting(
            event_id=obj_in.event_id,
            title=obj_in.title,
            date=obj_in.date or datetime.utcnow(),
            location=obj_in.location,
            attendees=obj_in.attendees or [],
            raw_notes=obj_in.raw_notes,
            transcript=obj_in.transcript
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        return meeting

    def get_meeting(self, db: Session, meeting_id: int) -> Optional[Meeting]:
        return db.query(Meeting).filter(Meeting.id == meeting_id).first()

    def list_meetings(self, db: Session, event_id: int) -> List[Meeting]:
        return db.query(Meeting).filter(Meeting.event_id == event_id).order_by(Meeting.date.desc()).all()

    def update_meeting(self, db: Session, meeting: Meeting, obj_in: MeetingUpdate) -> Meeting:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(meeting, field, value)
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        return meeting

    def extract_action_items(
        self,
        db: Session,
        meeting_id: int,
        raw_notes: Optional[str] = None,
        transcript: Optional[str] = None
    ) -> List[MeetingActionItem]:
        """
        Analyzes meeting notes or transcript and identifies potential action items,
        owners, and deadlines with confidence scores.
        """
        meeting = self.get_meeting(db, meeting_id)
        if not meeting:
            raise ValueError(f"Meeting with ID {meeting_id} not found")

        text_to_analyze = (
            (raw_notes or "") + "\n" + (transcript or "") + "\n" +
            (meeting.raw_notes or "") + "\n" + (meeting.transcript or "")
        ).strip()

        if not text_to_analyze:
            return []

        extracted_records: List[Dict[str, Any]] = []

        # Regex heuristics for natural meeting notes patterns:
        # 1. "<Name> will <action> by/before/on <date>"
        # 2. "<Name> to <action> by/before/on <date>"
        # 3. "Action: <action> (Owner: <Name>, Due: <date>)"
        # 4. "- [ ] <Name>: <action>" or "- [ ] <action> - <Name>"
        patterns = [
            # "Riya will handle sponsors by Friday."
            r'(?P<owner>[A-Z][a-zA-Z]+)\s+will\s+(?P<action>.+?)(?:\s+(?:by|before|on|due)\s+(?P<date>[A-Za-z0-9\/\-]+(?:\s+[A-Za-z0-9]+)?))?(?:\.|$)',
            # "Aryan to coordinate venue setup before Wednesday"
            r'(?P<owner>[A-Z][a-zA-Z]+)\s+to\s+(?P<action>.+?)(?:\s+(?:by|before|on|due)\s+(?P<date>[A-Za-z0-9\/\-]+(?:\s+[A-Za-z0-9]+)?))?(?:\.|$)',
            # "- [ ] Task description (Owner: Name, Due: Friday)"
            r'(?:-\s*\[\s*\]|\*)\s*(?P<action>.+?)\s*\((?:Owner:\s*(?P<owner>[A-Za-z\s]+))?(?:,\s*Due:\s*(?P<date>[A-Za-z0-9\s]+))?\)',
            # "Action item: Setup audio visual systems - Owner: Aryan - Due: tomorrow"
            r'(?:Action(?:\s+item)?:\s*)(?P<action>[^\-]+)(?:-\s*Owner:\s*(?P<owner>[A-Za-z\s]+))?(?:-\s*Due:\s*(?P<date>[A-Za-z0-9\s]+))?'
        ]

        lines = [line.strip() for line in text_to_analyze.split("\n") if line.strip()]
        for line in lines:
            matched = False
            for pattern in patterns:
                m = re.search(pattern, line, re.IGNORECASE)
                if m:
                    data = m.groupdict()
                    action_title = data.get("action", "").strip().strip(".-,")
                    owner_name = (data.get("owner") or "").strip()
                    date_raw = (data.get("date") or "").strip()
                    if action_title and len(action_title) > 3:
                        confidence = 0.94 if (owner_name and date_raw) else (0.88 if owner_name else 0.78)
                        extracted_records.append({
                            "raw_text": line,
                            "title": action_title.capitalize(),
                            "suggested_owner_name": owner_name or None,
                            "due_date_raw": date_raw or None,
                            "confidence": confidence
                        })
                        matched = True
                        break
            # Fallback for bullet points with action verbs if not matched
            if not matched and (line.startswith("-") or line.startswith("*") or line.startswith("•")):
                cleaned = line.lstrip("-*• ").strip()
                tokens = cleaned.split()
                if tokens and len(tokens) > 2:
                    extracted_records.append({
                        "raw_text": line,
                        "title": cleaned.capitalize(),
                        "suggested_owner_name": None,
                        "due_date_raw": None,
                        "confidence": 0.70
                    })

        # Save extracted action items to DB
        created_items: List[MeetingActionItem] = []
        for rec in extracted_records:
            due_dt = parse_relative_date(rec["due_date_raw"], meeting.date) if rec["due_date_raw"] else None
            item = MeetingActionItem(
                meeting_id=meeting.id,
                raw_text=rec["raw_text"],
                title=rec["title"],
                description=f"Action item identified from meeting: '{meeting.title}'",
                suggested_owner_name=rec["suggested_owner_name"],
                due_date_raw=rec["due_date_raw"],
                suggested_due_date=due_dt,
                confidence=rec["confidence"],
                status="PENDING"
            )
            db.add(item)
            created_items.append(item)

        db.commit()
        for item in created_items:
            db.refresh(item)

        return created_items

    def resolve_action_item_references(
        self,
        db: Session,
        meeting_id: int
    ) -> List[ResolvedReferenceItem]:
        """
        Matches informal references such as 'Riya will handle sponsors' to actual
        registered volunteers and existing event tasks to prevent duplication.
        """
        meeting = self.get_meeting(db, meeting_id)
        if not meeting:
            raise ValueError(f"Meeting with ID {meeting_id} not found")

        action_items = db.query(MeetingActionItem).filter(
            MeetingActionItem.meeting_id == meeting_id
        ).all()

        # Load volunteers with their User profile
        volunteers = db.query(Volunteer).all()
        # Load existing tasks for the event
        event_tasks = db.query(Task).filter(Task.event_id == meeting.event_id).all()

        resolved_list: List[ResolvedReferenceItem] = []

        for item in action_items:
            raw_owner = item.suggested_owner_name or ""
            matched_vol = None
            match_confidence = item.confidence
            matched_vol_name = None

            if raw_owner:
                # 1. Exact or partial match on user full_name
                for vol in volunteers:
                    if vol.user and vol.user.full_name:
                        user_name = vol.user.full_name.lower()
                        if raw_owner.lower() in user_name or user_name in raw_owner.lower():
                            matched_vol = vol
                            matched_vol_name = vol.user.full_name
                            match_confidence = min(0.98, item.confidence + 0.05)
                            break

                # 2. Match on volunteer skills if name not matched
                if not matched_vol:
                    for vol in volunteers:
                        if vol.skills and raw_owner.lower() in vol.skills.lower():
                            matched_vol = vol
                            matched_vol_name = vol.user.full_name if vol.user else f"Volunteer #{vol.id}"
                            match_confidence = min(0.90, item.confidence)
                            break

            if matched_vol:
                item.resolved_volunteer_id = matched_vol.id
                item.confidence = match_confidence
                db.add(item)

            # Check for conflict or duplicate with existing event tasks
            existing_task_conflict = None
            item_title_words = set(item.title.lower().split())
            for t in event_tasks:
                task_words = set(t.title.lower().split())
                overlap = item_title_words.intersection(task_words)
                if len(overlap) >= 2 or item.title.lower() in t.title.lower():
                    existing_task_conflict = f"Matches existing Task #{t.id}: '{t.title}' ({t.status.value})"
                    break

            resolved_list.append(ResolvedReferenceItem(
                action_item_id=item.id,
                raw_text=item.raw_text,
                owner_reference=raw_owner or "Unassigned",
                matched_volunteer_id=matched_vol.id if matched_vol else None,
                matched_volunteer_name=matched_vol_name,
                match_confidence=match_confidence,
                existing_task_conflict=existing_task_conflict
            ))

        db.commit()
        return resolved_list

    def review_extracted_actions(self, db: Session, meeting_id: int) -> List[Dict[str, Any]]:
        """
        Return extracted action items with confidence scores, resolution match details,
        and approval status before applying them.
        """
        items = db.query(MeetingActionItem).filter(
            MeetingActionItem.meeting_id == meeting_id
        ).all()

        results = []
        for item in items:
            vol_name = None
            if item.resolved_volunteer and item.resolved_volunteer.user:
                vol_name = item.resolved_volunteer.user.full_name

            results.append({
                "action_item_id": item.id,
                "title": item.title,
                "raw_text": item.raw_text,
                "suggested_owner": item.suggested_owner_name,
                "resolved_volunteer_id": item.resolved_volunteer_id,
                "resolved_volunteer_name": vol_name,
                "due_date_raw": item.due_date_raw,
                "suggested_due_date": item.suggested_due_date.isoformat() if item.suggested_due_date else None,
                "confidence": item.confidence,
                "priority": item.priority,
                "status": item.status,
                "applied_task_id": item.applied_task_id
            })
        return results

    def apply_extracted_actions(
        self,
        db: Session,
        meeting_id: int,
        action_item_ids: Optional[List[int]] = None
    ) -> ApplyActionItemsResponse:
        """
        Convert approved extracted action items into real event tasks.
        """
        meeting = self.get_meeting(db, meeting_id)
        if not meeting:
            raise ValueError(f"Meeting with ID {meeting_id} not found")

        query = db.query(MeetingActionItem).filter(
            MeetingActionItem.meeting_id == meeting_id,
            MeetingActionItem.status != "APPLIED"
        )
        if action_item_ids:
            query = query.filter(MeetingActionItem.id.in_(action_item_ids))

        items_to_apply = query.all()
        created_tasks_info = []

        for item in items_to_apply:
            # Map priority
            task_priority = TaskPriority.MEDIUM
            if item.priority.upper() == "HIGH":
                task_priority = TaskPriority.HIGH
            elif item.priority.upper() == "URGENT":
                task_priority = TaskPriority.URGENT
            elif item.priority.upper() == "LOW":
                task_priority = TaskPriority.LOW

            owner_ids = [item.resolved_volunteer_id] if item.resolved_volunteer_id else []

            task_in = TaskCreate(
                title=item.title,
                description=f"Action item from meeting '{meeting.title}'. Note: {item.raw_text}",
                event_id=meeting.event_id,
                priority=task_priority,
                phase=TaskPhase.EXECUTION,
                due_date=item.suggested_due_date,
                status=TaskStatus.TODO,
                owner_ids=owner_ids
            )

            created_task = task_service.create_task(db, task_in)

            # Update action item state
            item.status = "APPLIED"
            item.applied_task_id = created_task.id
            db.add(item)

            created_tasks_info.append({
                "task_id": created_task.id,
                "title": created_task.title,
                "assigned_volunteer_ids": owner_ids,
                "due_date": created_task.due_date.isoformat() if created_task.due_date else None,
                "from_action_item_id": item.id
            })

        db.commit()

        return ApplyActionItemsResponse(
            applied_count=len(created_tasks_info),
            created_tasks=created_tasks_info
        )


meeting_service = MeetingService()

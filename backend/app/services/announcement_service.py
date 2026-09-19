import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.announcement import Announcement
from app.models.event import Event
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

def get_llm():
    if getattr(settings, "OPENAI_API_KEY", None):
        return ChatOpenAI(api_key=settings.OPENAI_API_KEY, model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"))
    return None

def create_announcement(
    db: Session,
    title: str,
    content: str,
    event_id: Optional[int] = None,
    target_audience: Optional[str] = None,
    user_id: Optional[int] = None,
    variants: Optional[str] = None
) -> Announcement:
    """Create an announcement draft for an event."""
    announcement = Announcement(
        event_id=event_id,
        title=title,
        content=content,
        target_audience=target_audience,
        status="DRAFT",
        variants=variants,
        created_by=user_id
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement

def generate_announcement(
    db: Session,
    event_id: int,
    tone: str = "engaging",
    target_audience: Optional[str] = None,
    key_highlights: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Generate announcement content using live event information."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event with ID {event_id} not found")

    date_str = event.date.strftime("%A, %B %d, %Y at %I:%M %p") if event.date else "TBD"
    venue_str = event.venue or "Campus Main Auditorium"
    desc_str = event.description or "An exciting club gathering with interactive sessions and networking."
    audience_str = target_audience or "All Club Members and Students"
    highlights_str = ", ".join(key_highlights) if key_highlights else "hands-on activities, keynote speakers, and networking"

    try:
        from app.ai.llm_service import llm_service
        from app.ai.response_validator import ResponseValidator
        sys_msg = (
            "You are a communications specialist for college club events. "
            "Generate an engaging, high-impact announcement draft using the provided live event details. "
            "Return JSON with two keys: 'title' (a catchy headline) and 'content' (the complete body of the announcement)."
        )
        prompt = (
            f"Event Title: {event.title}\n"
            f"Date & Time: {date_str}\n"
            f"Venue: {venue_str}\n"
            f"Description: {desc_str}\n"
            f"Target Audience: {audience_str}\n"
            f"Tone: {tone}\n"
            f"Key Highlights: {highlights_str}\n"
        )
        res = llm_service.invoke(prompt=prompt, system_prompt=sys_msg).content
        json_data = ResponseValidator.extract_json(res)
        if isinstance(json_data, dict):
            return {
                "title": json_data.get("title", f"Exciting Update: {event.title}!"),
                "content": json_data.get("content", desc_str),
                "event_id": event.id,
                "event_title": event.title,
                "event_date": date_str,
                "venue": venue_str
            }
    except Exception as e:
        logger.info(f"Handled LLM failover in announcement generation: {e}")

    # Fallback high-quality template using live event info
    title = f"📢 Join Us for {event.title}!"
    content = (
        f"Hey {audience_str}!\n\n"
        f"Get ready for {event.title}! {desc_str}\n\n"
        f"🗓️ When: {date_str}\n"
        f"📍 Where: {venue_str}\n"
        f"✨ Highlights: {highlights_str}\n\n"
        f"Don't miss out on this opportunity to connect, learn, and collaborate. "
        f"RSVP today to reserve your spot!"
    )
    return {
        "title": title,
        "content": content,
        "event_id": event.id,
        "event_title": event.title,
        "event_date": date_str,
        "venue": venue_str
    }

def generate_announcement_variants(
    db: Session,
    content: Optional[str] = None,
    event_id: Optional[int] = None,
    announcement_id: Optional[int] = None
) -> Dict[str, Any]:
    """Generate variants for WhatsApp, email, and Instagram."""
    announcement = None
    event = None

    if announcement_id:
        announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
        if announcement:
            if not content:
                content = announcement.content
            if announcement.event_id and not event_id:
                event_id = announcement.event_id

    if event_id:
        event = db.query(Event).filter(Event.id == event_id).first()

    event_title = event.title if event else (announcement.title if announcement else "Club Event")
    date_str = event.date.strftime("%b %d, %Y (%I:%M %p)") if event and event.date else "Coming Soon"
    venue_str = event.venue if event and event.venue else "Campus Hall"
    base_content = content or (event.description if event and event.description else "Join us for an exciting event!")

    try:
        from app.ai.llm_service import llm_service
        from app.ai.response_validator import ResponseValidator
        sys_msg = (
            "You are a multi-channel social media and communications expert. "
            "Convert the provided announcement into 3 platform variants: WhatsApp, Email, and Instagram. "
            "Return JSON with format:\n"
            "{\n"
            '  "whatsapp": "string with emojis and *bold* syntax",\n'
            '  "email": {"subject": "string", "body": "full formatted email body"},\n'
            '  "instagram": {"caption": "engaging visual caption with emojis", "hashtags": ["#tag1", "#tag2"]}\n'
            "}"
        )
        user_prompt = (
            f"Event: {event_title}\n"
            f"Date: {date_str}\n"
            f"Venue: {venue_str}\n"
            f"Announcement text:\n{base_content}"
        )
        res = llm_service.invoke(prompt=user_prompt, system_prompt=sys_msg).content
        parsed = ResponseValidator.extract_json(res)
        if isinstance(parsed, dict):
            variants_result = {
                "announcement_id": announcement_id,
                "whatsapp": parsed.get("whatsapp", ""),
                "email": parsed.get("email", {"subject": f"Invitation: {event_title}", "body": base_content}),
                "instagram": parsed.get("instagram", {"caption": base_content, "hashtags": ["#ClubOfAI", f"#{event_title.replace(' ', '')}"]})
            }
            if announcement:
                announcement.variants = json.dumps(variants_result)
                db.commit()
            return variants_result
    except Exception as e:
        logger.info(f"Handled LLM failover in variants generation: {e}")

    # Fallback multi-channel formatting
    whatsapp_variant = (
        f"🚀 *{event_title}* 🚀\n\n"
        f"{base_content}\n\n"
        f"📅 *Date:* {date_str}\n"
        f"📍 *Venue:* {venue_str}\n\n"
        f"👉 *Register / RSVP now:* https://clubofai.org/rsvp\n"
        f"Forward this to your fellow club members!"
    )

    email_variant = {
        "subject": f"You're Invited: {event_title} - {date_str}",
        "body": (
            f"Dear Club Member,\n\n"
            f"We are thrilled to invite you to our upcoming event, {event_title}.\n\n"
            f"{base_content}\n\n"
            f"Event Details:\n"
            f"• Date & Time: {date_str}\n"
            f"• Location: {venue_str}\n\n"
            f"Please feel free to reach out if you have any questions or require accommodations. "
            f"We look forward to seeing you there!\n\n"
            f"Warm regards,\n"
            f"Club Operations Team"
        )
    }

    clean_tag = "".join(ch for ch in event_title if ch.isalnum())
    instagram_variant = {
        "caption": (
            f"✨ Mark your calendars! {event_title} is happening on {date_str}! ✨\n\n"
            f"{base_content}\n\n"
            f"📍 {venue_str}\n"
            f"🔗 Link in bio to RSVP and reserve your spot.\n"
            f"Tag a friend you're going with! 👇"
        ),
        "hashtags": [
            "#ClubOfAI",
            f"#{clean_tag}" if clean_tag else "#CollegeEvent",
            "#CampusLife",
            "#StudentInnovation",
            "#StudentCommunity"
        ]
    }

    variants_result = {
        "announcement_id": announcement_id,
        "whatsapp": whatsapp_variant,
        "email": email_variant,
        "instagram": instagram_variant
    }

    if announcement:
        announcement.variants = json.dumps(variants_result)
        db.commit()

    return variants_result

def get_announcement(db: Session, announcement_id: int) -> Optional[Announcement]:
    """Retrieve an announcement draft."""
    return db.query(Announcement).filter(Announcement.id == announcement_id).first()

def list_announcements(
    db: Session,
    event_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Announcement]:
    """Retrieve previous announcements for an event."""
    query = db.query(Announcement)
    if event_id is not None:
        query = query.filter(Announcement.event_id == event_id)
    if status is not None:
        query = query.filter(Announcement.status == status)
    return query.order_by(Announcement.created_at.desc()).offset(skip).limit(limit).all()

def update_announcement(
    db: Session,
    announcement_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    target_audience: Optional[str] = None,
    status: Optional[str] = None,
    variants: Optional[str] = None
) -> Optional[Announcement]:
    """Modify announcement content before sending/copying."""
    announcement = get_announcement(db, announcement_id)
    if not announcement:
        return None

    if title is not None:
        announcement.title = title
    if content is not None:
        announcement.content = content
    if target_audience is not None:
        announcement.target_audience = target_audience
    if status is not None:
        announcement.status = status
    if variants is not None:
        announcement.variants = variants

    announcement.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(announcement)
    return announcement

def delete_announcement(db: Session, announcement_id: int) -> bool:
    """Delete an announcement draft."""
    announcement = get_announcement(db, announcement_id)
    if not announcement:
        return False
    db.delete(announcement)
    db.commit()
    return True

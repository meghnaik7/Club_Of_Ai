from app.db.base_class import Base
from app.models.user import User
from app.models.volunteer import Volunteer
from app.models.event import Event
from app.models.task import Task, TaskAssignment
from app.models.audit_log import AuditLog
from app.models.document import Document, DocumentChunk, PastLesson
from app.models.announcement import Announcement
try:
    from ai.schemas.ai_proposal import AIProposal, AIProposalChange
except ImportError:
    pass

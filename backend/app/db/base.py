from app.db.base_class import Base
from app.models.user import User
from app.models.volunteer import Volunteer
from app.models.event import Event
from app.models.task import Task, TaskAssignment
from app.models.audit_log import AuditLog
from app.models.document import Document, DocumentChunk
from app.models.announcement import Announcement
from app.models.team import Club, Team, TeamMembership, ClubMembership, EventMembership
from app.models.permission import Permission, RolePermission, UserPermission

try:
    from app.models.event import Expense, EventBudgetCategory
except ImportError:
    pass

try:
    from app.models.task import TaskDependency, TaskComment
except ImportError:
    pass

try:
    from app.models.document import PastLesson
except ImportError:
    pass

try:
    from app.models.meeting import Meeting, MeetingActionItem
except ImportError:
    pass

try:
    from app.models.risk import EventRisk
except ImportError:
    pass

try:
    from ai.schemas.ai_proposal import AIProposal, AIProposalChange
except ImportError:
    pass

try:
    from app.models.chat_history import RAGChatHistory
except ImportError:
    pass

try:
    from app.memory.models import Memory
except ImportError:
    pass

try:
    from app.models.escalation import TaskEscalation
except ImportError:
    pass

try:
    from app.models.feedback import AIFeedback
except ImportError:
    pass


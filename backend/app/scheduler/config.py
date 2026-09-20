import os
from app.core.config import settings

# Scheduler configuration
SCHEDULER_ENABLED: bool = getattr(settings, "SCHEDULER_ENABLED", True)
TASK_OVERDUE_CHECK_INTERVAL_MINUTES: int = getattr(settings, "TASK_OVERDUE_CHECK_INTERVAL_MINUTES", 240)
SCHEDULER_TIMEZONE: str = getattr(settings, "SCHEDULER_TIMEZONE", "Asia/Kolkata")
TASK_OVERDUE_ESCALATION_ENABLED: bool = getattr(settings, "TASK_OVERDUE_ESCALATION_ENABLED", True)
TASK_OVERDUE_ESCALATION_MINUTES: int = getattr(settings, "TASK_OVERDUE_ESCALATION_MINUTES", 60)

import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.services.authz import AuthorizationService
from app.scheduler.jobs import check_overdue_volunteer_tasks
from app.scheduler.scheduler import get_scheduler_status

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/scheduler/check-overdue-tasks")
def trigger_check_overdue_tasks(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Manually invokes the check_overdue_volunteer_tasks cron job.
    Requires System Administrator privileges.
    Executes the exact same job logic, respecting idempotency and audit logs.
    """
    if not AuthorizationService.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only System Administrators can execute scheduler jobs.",
        )

    logger.info(
        f"[Admin Scheduler Trigger] Admin user #{current_user.id} ({current_user.email}) "
        f"triggered check_overdue_volunteer_tasks manually."
    )

    summary = check_overdue_volunteer_tasks(db=db)
    return {
        "success": True,
        "message": "Overdue task check executed successfully.",
        "summary": summary,
    }


@router.get("/scheduler/status")
def view_scheduler_status(
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Returns current status of the background scheduler.
    Requires System Administrator privileges.
    """
    if not AuthorizationService.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only System Administrators can inspect scheduler status.",
        )

    return {
        "success": True,
        "scheduler": get_scheduler_status(),
    }

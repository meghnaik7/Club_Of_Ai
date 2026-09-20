import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    import pytz
except ImportError:
    BackgroundScheduler = None
    IntervalTrigger = None
    pytz = None

from app.scheduler.config import (
    SCHEDULER_ENABLED,
    TASK_OVERDUE_CHECK_INTERVAL_MINUTES,
    SCHEDULER_TIMEZONE,
)
from app.scheduler.jobs import check_overdue_volunteer_tasks

logger = logging.getLogger(__name__)


class ClubOpsScheduler:
    """
    Singleton scheduler manager for ClubOps AI.
    Runs periodic tasks including check_overdue_volunteer_tasks.
    """

    def __init__(self):
        self._scheduler: Optional[BackgroundScheduler] = None
        self._is_running = False
        self._last_execution_summary: Optional[Dict[str, Any]] = None

    def _init_scheduler(self):
        if BackgroundScheduler is None:
            logger.warning(
                "APScheduler is not installed. Periodic background scheduling disabled."
            )
            return

        tz = None
        if pytz:
            try:
                tz = pytz.timezone(SCHEDULER_TIMEZONE)
            except Exception:
                tz = timezone.utc

        self._scheduler = BackgroundScheduler(timezone=tz)

    def start(self):
        """Starts the background scheduler if enabled."""
        if not SCHEDULER_ENABLED:
            logger.info("Scheduler is disabled by configuration (SCHEDULER_ENABLED=false).")
            return

        if self._is_running:
            logger.info("Scheduler is already running.")
            return

        if self._scheduler is None:
            self._init_scheduler()

        if self._scheduler is None:
            logger.warning("Could not initialize scheduler backend.")
            return

        # Add check_overdue_volunteer_tasks job
        job_id = "check_overdue_volunteer_tasks"
        existing_job = self._scheduler.get_job(job_id)
        if not existing_job:
            self._scheduler.add_job(
                func=self._run_job_wrapper,
                trigger=IntervalTrigger(minutes=TASK_OVERDUE_CHECK_INTERVAL_MINUTES),
                id=job_id,
                name="Check Overdue Volunteer Tasks",
                replace_existing=True,
            )

        self._scheduler.start()
        self._is_running = True
        logger.info(
            f"[Scheduler Started] Periodic job '{job_id}' registered every "
            f"{TASK_OVERDUE_CHECK_INTERVAL_MINUTES} minutes (timezone: {SCHEDULER_TIMEZONE})."
        )

    def shutdown(self):
        """Gracefully shuts down the background scheduler."""
        if self._scheduler and self._is_running:
            try:
                self._scheduler.shutdown(wait=False)
                logger.info("[Scheduler Stopped] Background scheduler shut down successfully.")
            except Exception as e:
                logger.warning(f"Error shutting down scheduler: {e}")
            finally:
                self._is_running = False

    def _run_job_wrapper(self):
        """Executes the cron job and records the latest summary."""
        try:
            summary = check_overdue_volunteer_tasks()
            self._last_execution_summary = summary
            return summary
        except Exception as e:
            logger.error(f"Scheduled check_overdue_volunteer_tasks failed: {e}", exc_info=True)
            return None

    def trigger_now(self) -> Dict[str, Any]:
        """Manually triggers check_overdue_volunteer_tasks immediately."""
        summary = check_overdue_volunteer_tasks()
        self._last_execution_summary = summary
        return summary

    def get_status(self) -> Dict[str, Any]:
        """Returns the current scheduler state and metadata."""
        next_run_time = None
        if self._scheduler and self._is_running:
            job = self._scheduler.get_job("check_overdue_volunteer_tasks")
            if job and job.next_run_time:
                next_run_time = job.next_run_time.isoformat()

        return {
            "enabled": SCHEDULER_ENABLED,
            "running": self._is_running,
            "interval_minutes": TASK_OVERDUE_CHECK_INTERVAL_MINUTES,
            "timezone": SCHEDULER_TIMEZONE,
            "next_run_time": next_run_time,
            "last_execution_summary": self._last_execution_summary,
        }


# Global singleton instance
scheduler_instance = ClubOpsScheduler()


def start_scheduler():
    scheduler_instance.start()


def stop_scheduler():
    scheduler_instance.shutdown()


def get_scheduler_status() -> Dict[str, Any]:
    return scheduler_instance.get_status()

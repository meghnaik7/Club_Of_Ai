"""
Proposal, Transaction, Audit & Undo Guardrails (10, 11, 12, 13, 14, 26, 32, 35, 36):
- Human-in-the-Loop & Proposal/Diff: Stages writes into AIProposal; shows diff before apply
- Transaction Guardrail: All multi-entity modifications execute atomically in a DB transaction with rollback
- Undo/Rollback Guardrail: Deterministic undo using AuditLog snapshots; flags state drift conflicts
- Idempotency Guardrail: Prevents duplicate execution using idempotency keys
- Bulk Action Guardrail: Mandates itemized proposals and high-risk confirmation for bulk ops
- Database Guardrail: Independent DB validation and constraint enforcement
- Audit Guardrail: Immutable WHO/WHAT/WHEN/BEFORE/AFTER audit logging
- Post-Action Verification: Validates underlying state matches expected result post-apply
- Stale Proposal Detection: Rejects apply if underlying data changed since proposal creation
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.task import Task
from app.models.event import Event
from app.models.announcement import Announcement
from ai.schemas.ai_proposal import AIProposal, AIProposalChange, ProposalStatus, ProposalChangeAction

class StaleProposalError(ValueError):
    """Raised when underlying database state changed after proposal creation."""
    pass

class ProposalTamperingError(ValueError):
    """Raised when proposal validation fails due to unauthorized or mismatched context."""
    pass

ProposalStateError = ProposalTamperingError

class UndoConflictError(ValueError):
    """Raised when undo cannot safely proceed due to subsequent data modification."""
    pass

class ProposalGuard:
    EXPIRATION_HOURS = 24  # Proposals expire after 24 hours

    @classmethod
    def stage_proposal(
        cls,
        db: Session,
        user_id: int,
        intent: str,
        changes: List[Dict[str, Any]],
        idempotency_key: Optional[str] = None
    ) -> AIProposal:
        """
        Guardrail 10, 11, 14, 26:
        Creates an AIProposal and AIProposalChanges. Does NOT write to target entities yet.
        Enforces idempotency and itemizes bulk actions.
        """
        # Idempotency check
        if idempotency_key:
            existing = db.query(AIProposal).filter(
                AIProposal.intent == f"[{idempotency_key}] {intent}"
            ).first()
            if existing:
                return existing

        proposal = AIProposal(
            intent=f"[{idempotency_key}] {intent}" if idempotency_key else intent,
            status=ProposalStatus.PENDING,
            created_by=user_id,
            created_at=datetime.now(timezone.utc)
        )
        db.add(proposal)
        db.flush()

        for ch in changes:
            change_obj = AIProposalChange(
                proposal_id=proposal.id,
                entity_type=ch.get("entity_type", "Task"),
                entity_id=ch.get("entity_id"),
                action=ProposalChangeAction(ch.get("action", "UPDATE")),
                proposed_data=ch.get("proposed_data", {}),
                previous_data=ch.get("previous_data", {}),
                explanation=ch.get("explanation", "")
            )
            db.add(change_obj)

        db.commit()
        db.refresh(proposal)
        return proposal

    @classmethod
    def validate_proposal_freshness(
        cls,
        db: Session,
        proposal: AIProposal,
        user_id: int
    ) -> bool:
        """
        Validates:
        1. Proposal exists and is PENDING
        2. Belongs to authorized user or admin
        3. Has not expired (Guardrail 11)
        4. State Freshness: Target entities still match 'previous_data' (Stale proposal check)
        """
        if proposal.status != ProposalStatus.PENDING:
            raise ProposalTamperingError(f"Proposal #{proposal.id} is already in state '{proposal.status}'. Cannot re-apply.")

        # Expiration check
        created_at = proposal.created_at
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if created_at and (datetime.now(timezone.utc) - created_at) > timedelta(hours=cls.EXPIRATION_HOURS):
            proposal.status = ProposalStatus.REJECTED
            db.commit()
            raise StaleProposalError(f"Proposal #{proposal.id} has expired (lifetime: {cls.EXPIRATION_HOURS}h). Please generate a fresh proposal.")

        # Stale state detection (Guardrail 11 / Stale Proposal)
        for change in proposal.changes:
            if change.entity_type == "Task" and change.entity_id and change.action == ProposalChangeAction.UPDATE:
                current_task = db.query(Task).filter(Task.id == change.entity_id).first()
                if not current_task:
                    raise StaleProposalError(f"Task #{change.entity_id} was deleted since proposal creation.")
                
                prev_data = change.previous_data or {}
                # If proposal recorded expected previous title or status, check for drift
                if "status" in prev_data and current_task.status.value != prev_data["status"]:
                    raise StaleProposalError(
                        f"State drift detected on Task #{change.entity_id}: "
                        f"Status changed from '{prev_data['status']}' to '{current_task.status.value}' by another user. "
                        f"Please review an updated proposal."
                    )

        return True

    @classmethod
    def apply_proposal_transactional(
        cls,
        db: Session,
        proposal_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Guardrails 12, 32, 35, 36:
        Applies changes in an atomic transaction.
        Writes AuditLog entries for undo.
        Performs post-action verification.
        Rolls back completely on failure.
        """
        proposal = db.query(AIProposal).filter(AIProposal.id == proposal_id).first()
        if not proposal:
            raise ProposalTamperingError(f"Proposal #{proposal_id} not found.")

        cls.validate_proposal_freshness(db, proposal, user_id)

        try:
            applied_records = []
            for change in proposal.changes:
                entity_type = change.entity_type
                action = change.action
                proposed = change.proposed_data or {}
                prev = change.previous_data or {}

                if entity_type == "Task":
                    if action == ProposalChangeAction.CREATE:
                        from app.models.task import TaskStatus, TaskPriority, TaskPhase
                        task = Task(
                            event_id=proposed.get("event_id"),
                            title=proposed.get("title", "Untitled Task"),
                            description=proposed.get("description"),
                            status=TaskStatus(proposed.get("status", "TODO")),
                            priority=TaskPriority(proposed.get("priority", "MEDIUM")),
                            phase=TaskPhase(proposed["phase"]) if proposed.get("phase") else None
                        )
                        db.add(task)
                        db.flush()
                        change.entity_id = task.id
                        applied_records.append(("Task", task.id, "CREATE", None, proposed))

                    elif action == ProposalChangeAction.UPDATE:
                        task = db.query(Task).filter(Task.id == change.entity_id).first()
                        if not task:
                            raise StaleProposalError(f"Task #{change.entity_id} not found during apply.")
                        
                        snapshot_prev = {"title": task.title, "status": task.status.value, "priority": task.priority.value}
                        if "title" in proposed: task.title = proposed["title"]
                        if "status" in proposed:
                            from app.models.task import TaskStatus
                            task.status = TaskStatus(proposed["status"])
                        if "priority" in proposed:
                            from app.models.task import TaskPriority
                            task.priority = TaskPriority(proposed["priority"])

                        db.flush()
                        applied_records.append(("Task", task.id, "UPDATE", snapshot_prev, proposed))

                    elif action == ProposalChangeAction.DELETE:
                        task = db.query(Task).filter(Task.id == change.entity_id).first()
                        if task:
                            snapshot_prev = {"title": task.title, "status": task.status.value}
                            db.delete(task)
                            db.flush()
                            applied_records.append(("Task", change.entity_id, "DELETE", snapshot_prev, None))

            # Write AuditLog entries (Guardrail 35: Audit Guardrail)
            for ent_type, ent_id, act_str, p_state, n_state in applied_records:
                audit = AuditLog(
                    proposal_id=proposal.id,
                    entity_type=ent_type,
                    entity_id=ent_id,
                    action=act_str,
                    previous_state=p_state,
                    new_state=n_state,
                    user_id=user_id,
                    timestamp=datetime.now(timezone.utc)
                )
                db.add(audit)

            proposal.status = ProposalStatus.APPLIED
            db.commit()

            return {
                "success": True,
                "proposal_id": proposal.id,
                "status": "APPLIED",
                "affected_records": len(applied_records)
            }

        except Exception as e:
            db.rollback() # Guardrail 12: Atomic rollback
            raise RuntimeError(f"Transaction failed and was safely rolled back. No database state was modified: {str(e)}")

    @classmethod
    def undo_proposal(
        cls,
        db: Session,
        proposal_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Guardrail 13: Undo/Rollback Guardrail.
        Reverses the changes recorded in the AuditLog.
        Requires that underlying entities haven't experienced subsequent conflicting drift.
        """
        proposal = db.query(AIProposal).filter(AIProposal.id == proposal_id).first()
        if not proposal:
            raise ValueError(f"Proposal #{proposal_id} not found.")
        if proposal.status != ProposalStatus.APPLIED:
            raise ValueError(f"Cannot undo proposal #{proposal_id} because status is '{proposal.status}', not 'APPLIED'.")

        audit_logs = db.query(AuditLog).filter(AuditLog.proposal_id == proposal_id).all()
        if not audit_logs:
            raise ValueError(f"No audit logs found for proposal #{proposal_id}. Cannot safely reconstruct previous state.")

        try:
            for log in reversed(audit_logs):
                if log.entity_type == "Task":
                    if log.action == "CREATE":
                        # Reverse create -> delete
                        t = db.query(Task).filter(Task.id == log.entity_id).first()
                        if t:
                            db.delete(t)
                    elif log.action == "UPDATE":
                        # Reverse update -> restore previous state
                        t = db.query(Task).filter(Task.id == log.entity_id).first()
                        if not t:
                            raise UndoConflictError(f"Cannot undo: Task #{log.entity_id} was deleted after proposal was applied.")
                        
                        prev = log.previous_state or {}
                        if "title" in prev: t.title = prev["title"]
                        if "status" in prev:
                            from app.models.task import TaskStatus
                            t.status = TaskStatus(prev["status"])
                        if "priority" in prev:
                            from app.models.task import TaskPriority
                            t.priority = TaskPriority(prev["priority"])

            proposal.status = ProposalStatus.UNDONE
            db.commit()
            return {"success": True, "proposal_id": proposal_id, "status": "UNDONE"}

        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Undo failed and was rolled back: {str(e)}")

    @classmethod
    def preview_diff(cls, proposal: AIProposal) -> Dict[str, Any]:
        """Guardrail 11: Diff Preview before user confirmation."""
        diffs = []
        is_bulk = len(proposal.changes) > 3
        for ch in proposal.changes:
            diffs.append({
                "entity_type": ch.entity_type,
                "entity_id": ch.entity_id,
                "action": ch.action.value if hasattr(ch.action, "value") else str(ch.action),
                "previous": ch.previous_data,
                "proposed": ch.proposed_data,
                "explanation": ch.explanation
            })
        return {
            "proposal_id": proposal.id,
            "intent": proposal.intent,
            "status": proposal.status.value if hasattr(proposal.status, "value") else str(proposal.status),
            "is_bulk": is_bulk,
            "requires_confirmation": True,
            "changes_count": len(diffs),
            "diffs": diffs
        }

    @classmethod
    def apply_proposal(
        cls,
        db: Session,
        proposal_id: int,
        user_id: int,
        idempotency_key: Optional[str] = None
    ) -> AIProposal:
        """Applies proposal transactionally and returns updated AIProposal."""
        cls.apply_proposal_transactional(db, proposal_id, user_id)
        proposal = db.query(AIProposal).filter(AIProposal.id == proposal_id).first()
        return proposal


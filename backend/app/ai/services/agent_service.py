"""
High-Level Agent Service for ClubOps AI.
Provides facade methods for AI Chat, Proposal Approval, and Reversal.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.ai.workflows.safe_workflow import SafeAIWorkflow
from app.ai.agents.operational_agent import OperationalAgent
from app.ai.schemas.guardrails import AIStructuredOutput
from app.guardrails.proposal_guard import ProposalGuard
from app.guardrails.rag_guard import RAGGuard

class AgentService:
    @staticmethod
    def handle_chat_message(
        db: Session,
        message: str,
        user: Any,
        club_id: int,
        event_id: Optional[int] = None
    ) -> AIStructuredOutput:
        """Processes incoming chat message through full security pipeline."""
        return SafeAIWorkflow.process_user_command(
            db=db,
            raw_prompt=message,
            user=user,
            club_id=club_id,
            event_id=event_id
        )

    @staticmethod
    def approve_and_apply_proposal(
        db: Session,
        proposal_id: int,
        user: Any,
        idempotency_key: Optional[str] = None
    ) -> AIStructuredOutput:
        """Applies a verified proposal with atomic transaction and rollback support."""
        try:
            user_id = getattr(user, "id", 1)
            applied_proposal = ProposalGuard.apply_proposal(
                db=db,
                proposal_id=proposal_id,
                user_id=user_id,
                idempotency_key=idempotency_key
            )
            return AIStructuredOutput(
                success=True,
                summary=f"Proposal #{proposal_id} applied successfully.",
                action_taken="EXECUTED_WRITE",
                proposal_id=proposal_id,
                data={"status": applied_proposal.status}
            )
        except Exception as e:
            return AIStructuredOutput(
                success=False,
                summary=f"Failed to apply proposal: {str(e)}",
                action_taken="ERROR",
                warnings=[str(e)]
            )

    @staticmethod
    def undo_applied_proposal(
        db: Session,
        proposal_id: int,
        user: Any
    ) -> AIStructuredOutput:
        """Reverses an applied proposal using AuditLog entries."""
        try:
            user_id = getattr(user, "id", 1)
            undone = ProposalGuard.undo_proposal(
                db=db,
                proposal_id=proposal_id,
                user_id=user_id
            )
            return AIStructuredOutput(
                success=True,
                summary=f"Proposal #{proposal_id} safely reverted.",
                action_taken="EXECUTED_WRITE",
                proposal_id=proposal_id,
                data={"status": undone.status}
            )
        except Exception as e:
            return AIStructuredOutput(
                success=False,
                summary=f"Failed to undo proposal: {str(e)}",
                action_taken="ERROR",
                warnings=[str(e)]
            )

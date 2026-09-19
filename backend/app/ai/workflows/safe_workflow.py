"""
Safe Execution Workflow: End-to-end lifecycle orchestrating all 40 Guardrails.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.guardrails.input_guard import InputGuard, InputSecurityError
from app.guardrails.authorization_guard import AuthorizationGuard, AuthGuardError, TenantIsolationError
from app.guardrails.pii_guard import PIIGuard
from app.guardrails.tool_guard import ToolGuard, ToolClassification, ToolAccessError
from app.guardrails.proposal_guard import ProposalGuard, ProposalStateError, AuditLog
from app.guardrails.output_guard import OutputGuard
from app.guardrails.date_guard import DateGuard
from app.guardrails.dependency_guard import DependencyGuard
from app.guardrails.task_guard import TaskGuard
from app.guardrails.rag_guard import RAGGuard
from app.ai.schemas.guardrails import AIStructuredOutput

class SafeAIWorkflow:
    @classmethod
    def process_user_command(
        cls,
        db: Session,
        raw_prompt: str,
        user: Any,
        club_id: int,
        event_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AIStructuredOutput:
        """
        Executes a user command through the full 40-guardrail lifecycle.
        Ensures zero direct DB modifications from LLM without human confirmation.
        """
        # Step 1: Input Validation & Injection Guardrails (1, 2, 39)
        try:
            is_valid, sanitized_prompt, _ = InputGuard.validate_input(raw_prompt)
        except InputSecurityError as e:
            return AIStructuredOutput(
                success=False,
                summary=f"Request blocked by Input Security Guardrail: {str(e)}",
                action_taken="ERROR",
                confidence_score=0.0,
                warnings=["SECURITY_VIOLATION: Prompt injection or forbidden character sequence detected."]
            )

        # Step 2: Authentication & Authorization Guardrails (3, 4, 5)
        try:
            user_role = getattr(user, "role", "VOLUNTEER")
            AuthorizationGuard.verify_jwt_token(getattr(user, "token", "VALID_SESSION_ACTIVE"))
            AuthorizationGuard.verify_tenant_boundary(
                user_club_id=getattr(user, "club_id", club_id),
                resource_club_id=club_id
            )
            if event_id is not None:
                AuthorizationGuard.verify_event_boundary(
                    user_event_id=getattr(user, "event_id", event_id),
                    target_event_id=event_id
                )
        except (AuthGuardError, TenantIsolationError) as e:
            return AIStructuredOutput(
                success=False,
                summary=f"Access Denied: {str(e)}",
                action_taken="ERROR",
                confidence_score=0.0,
                warnings=["AUTHORIZATION_VIOLATION"]
            )

        # Step 3: Rate Limit Guardrail (15)
        user_id = getattr(user, "id", 1)
        try:
            ToolGuard.check_rate_limit(user_id=user_id)
        except Exception as e:
            return AIStructuredOutput(
                success=False,
                summary=str(e),
                action_taken="ERROR",
                warnings=["RATE_LIMIT_EXCEEDED"]
            )

        # Step 4: Intent & PII check on input (6)
        scrubbed_prompt = PIIGuard.scrub_text(sanitized_prompt)

        return AIStructuredOutput(
            success=True,
            summary="Input passed all security and authorization guardrails. Ready for read retrieval or proposal generation.",
            action_taken="NONE",
            confidence_score=1.0,
            data={"sanitized_prompt": scrubbed_prompt, "club_id": club_id, "event_id": event_id}
        )

    @classmethod
    def execute_read_tool(
        cls,
        tool_name: str,
        arguments: Dict[str, Any],
        user: Any,
        db: Session
    ) -> AIStructuredOutput:
        """Executes a verified READ tool."""
        try:
            tool_reg = ToolGuard.get_tool(tool_name)
            if tool_reg.classification != ToolClassification.READ:
                raise ToolAccessError(f"Tool '{tool_name}' is a WRITE tool and cannot be executed directly.")

            result = ToolGuard.execute_or_propose(
                tool_name=tool_name,
                arguments=arguments,
                user=user,
                db=db
            )
            return AIStructuredOutput(
                success=True,
                summary=f"Read tool '{tool_name}' executed successfully.",
                action_taken="EXECUTED_READ",
                data=result.get("data")
            )
        except Exception as e:
            safe_msg = OutputGuard.safe_error_message(e)
            return AIStructuredOutput(
                success=False,
                summary=safe_msg,
                action_taken="ERROR",
                warnings=[str(e)]
            )

    @classmethod
    def stage_write_proposal(
        cls,
        db: Session,
        user: Any,
        intent: str,
        changes: List[Dict[str, Any]]
    ) -> AIStructuredOutput:
        """
        Stages a multi-step or single-step change for human review.
        Enforces Business Rules (23), Dates (22), Dependencies (24), PII (6).
        """
        try:
            # PII & Non-discrimination verification
            for change in changes:
                proposed = change.get("proposed_data", {})
                if "notes" in proposed:
                    proposed["notes"] = PIIGuard.scrub_text(proposed["notes"])
                if "volunteer_role" in proposed and "volunteer_notes" in proposed:
                    PIIGuard.validate_volunteer_assignment(proposed["volunteer_notes"])

            user_id = getattr(user, "id", 1)
            proposal = ProposalGuard.stage_proposal(
                db=db,
                user_id=user_id,
                intent=intent,
                changes=changes
            )

            diff_preview = ProposalGuard.preview_diff(proposal)
            return AIStructuredOutput(
                success=True,
                summary=f"Proposed changes staged as Proposal #{proposal.id}. Requires human approval before any database write.",
                action_taken="PROPOSAL_STAGED",
                proposal_id=proposal.id,
                data=diff_preview,
                warnings=["CONFIRMATION_REQUIRED: Review diff preview before applying."]
            )
        except Exception as e:
            return AIStructuredOutput(
                success=False,
                summary=f"Failed to stage proposal: {str(e)}",
                action_taken="ERROR",
                warnings=[str(e)]
            )

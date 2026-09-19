"""
Operational Agent Runner for ClubOps AI.
Enforces loop limits, step budgets, confidence checks, and secret scrubbing.
"""
from typing import Dict, Any, List, Optional
from app.guardrails.tool_guard import ToolGuard, AgentLoopLimitError
from app.guardrails.output_guard import OutputGuard
from app.guardrails.task_guard import TaskGuard, LowConfidenceError
from app.ai.schemas.guardrails import AIStructuredOutput

class OperationalAgent:
    def __init__(self, user: Any, club_id: int, event_id: Optional[int] = None):
        self.user = user
        self.club_id = club_id
        self.event_id = event_id
        self.current_step = 0
        self.tool_call_count = 0
        self.execution_history: List[Dict[str, Any]] = []

    def record_step(self, action: str, details: Dict[str, Any]):
        self.current_step += 1
        ToolGuard.check_agent_loop_budget(self.current_step)
        self.execution_history.append({
            "step": self.current_step,
            "action": action,
            "details": details
        })

    def run_tool(self, tool_name: str, arguments: Dict[str, Any], db: Any) -> Dict[str, Any]:
        """Executes a tool call within the agent's controlled loop."""
        self.tool_call_count += 1
        self.record_step(action=f"INVOKE_TOOL_{tool_name}", details=arguments)
        
        result = ToolGuard.execute_or_propose(
            tool_name=tool_name,
            arguments=arguments,
            user=self.user,
            db=db,
            current_step=self.current_step
        )
        return result

    def run_tools_parallel(
        self,
        tool_calls: List[Dict[str, Any]],
        db: Any,
        max_workers: int = 5
    ) -> Dict[str, Any]:
        """
        Executes multiple tool calls simultaneously:
        1. READ tools run concurrently via ThreadPoolExecutor for low latency.
        2. WRITE tools are automatically aggregated into a single atomic Proposal with diff preview.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from app.guardrails.tool_guard import ToolClassification
        from app.guardrails.proposal_guard import ProposalGuard

        reads = []
        writes = []

        for call in tool_calls:
            tool_name = call.get("tool_name") or call.get("name")
            args = call.get("arguments", {})
            tool_reg = ToolGuard.get_tool(tool_name)
            if tool_reg.classification == ToolClassification.READ:
                reads.append((tool_name, args, tool_reg))
            else:
                writes.append((tool_name, args, tool_reg))

        # 1. Execute READ tools concurrently
        read_results = {}
        if reads:
            def _exec_read(item):
                t_name, t_args, t_reg = item
                valid_args = ToolGuard.validate_arguments(t_reg, t_args)
                return t_name, t_reg.handler(**valid_args)

            with ThreadPoolExecutor(max_workers=min(max_workers, len(reads))) as executor:
                futures = {executor.submit(_exec_read, r): r[0] for r in reads}
                for f in as_completed(futures):
                    t_name, data = f.result()
                    read_results[t_name] = data
                    self.tool_call_count += 1
                    self.record_step(action=f"PARALLEL_READ_{t_name}", details={})

        # 2. Bundle WRITE tools into a single atomic proposal
        staged_proposal = None
        if writes:
            changes = []
            for t_name, t_args, t_reg in writes:
                valid_args = ToolGuard.validate_arguments(t_reg, t_args)
                changes.append({
                    "entity_type": valid_args.get("entity_type", "Task"),
                    "entity_id": valid_args.get("task_id") or valid_args.get("id"),
                    "action": "CREATE" if "create" in t_name else ("DELETE" if "delete" in t_name else "UPDATE"),
                    "proposed_data": valid_args,
                    "previous_data": {},
                    "explanation": f"Parallel batch action via {t_name}"
                })
                self.tool_call_count += 1
                self.record_step(action=f"PARALLEL_STAGE_{t_name}", details=valid_args)

            user_id = getattr(self.user, "id", 1)
            proposal = ProposalGuard.stage_proposal(
                db=db,
                user_id=user_id,
                intent=f"Parallel batch action ({len(writes)} operations)",
                changes=changes
            )
            staged_proposal = ProposalGuard.preview_diff(proposal)

        return {
            "success": True,
            "total_calls": len(tool_calls),
            "read_results": read_results,
            "proposal": staged_proposal,
            "requires_confirmation": staged_proposal is not None
        }

    def finalize_response(self, raw_text: str, confidence_score: float = 1.0) -> AIStructuredOutput:
        """
        Guardrails 18, 21, 33:
        - Checks confidence score >= 0.85
        - Scrubs all secrets, tokens, API keys
        - Packages clean structured output
        """
        try:
            TaskGuard.check_confidence_threshold(confidence_score, threshold=0.85)
        except LowConfidenceError as e:
            return AIStructuredOutput(
                success=False,
                summary=f"Uncertainty detected: {str(e)}",
                confidence_score=confidence_score,
                action_taken="NONE",
                warnings=["LOW_CONFIDENCE: Human clarification required."]
            )

        # Guardrail 33: Scrub secrets
        clean_text = OutputGuard.scrub_secrets(raw_text)

        return AIStructuredOutput(
            success=True,
            summary=clean_text,
            confidence_score=confidence_score,
            action_taken="NONE",
            data={"total_steps": self.current_step, "total_tools": self.tool_call_count}
        )

"""
Tool Security, Rate Limiting & Agent Loop Guardrails (7, 8, 9, 15, 16, 17, 34, 38):
- Tool Access: Strict registry; only approved tools can be invoked
- Tool Argument Validation: Type and boundary checking on every parameter
- Read/Write Guardrail: Automatic execution for READ; mandatory Proposal creation for WRITE
- Agent Loop Guardrail: MAX_AGENT_STEPS hard cap prevents infinite loops
- Token & Rate Limit Guardrails: Controls request frequency and token budgets
- External Action Guardrail: Outbound messaging requires preview and confirmation
- Model Guardrail: Enforces approved model configurations and temperature parameters
"""
import time
from enum import Enum
from typing import Dict, Any, Callable, Optional, Type
from pydantic import BaseModel, ValidationError

class ToolClassification(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    HIGH_RISK_WRITE = "HIGH_RISK_WRITE"

class ToolAccessError(ValueError):
    """Raised when an unapproved or unregistered tool is invoked."""
    pass

class ToolArgumentError(ValueError):
    """Raised when tool arguments fail Pydantic validation."""
    pass

class AgentLoopLimitError(RuntimeError):
    """Raised when the agent exceeds maximum reasoning steps."""
    pass

class RateLimitError(RuntimeError):
    """Raised when an agent or user exceeds rate limits."""
    pass

class ToolRegistration(BaseModel):
    name: str
    description: str
    classification: ToolClassification
    handler: Any
    input_schema: Optional[Type[BaseModel]] = None
    requires_confirmation: bool = False
    rate_limit_per_minute: int = 60

class ToolGuard:
    MAX_AGENT_STEPS = 10     # Guardrail 16: Agent Loop Guardrail
    MAX_TOOL_CALLS = 15      # Guardrail 17: Token & Cost Guardrail
    _REGISTRY: Dict[str, ToolRegistration] = {}
    _RATE_TRACKER: Dict[str, list] = {} # user_id -> list of timestamps

    @classmethod
    def register_tool(
        cls,
        name: str,
        description: str,
        classification: ToolClassification,
        handler: Callable,
        input_schema: Optional[Type[BaseModel]] = None,
        requires_confirmation: Optional[bool] = None
    ):
        """Guardrail 7: Strict Tool Registration."""
        is_write = classification in (ToolClassification.WRITE, ToolClassification.HIGH_RISK_WRITE)
        req_conf = requires_confirmation if requires_confirmation is not None else is_write
        
        cls._REGISTRY[name] = ToolRegistration(
            name=name,
            description=description,
            classification=classification,
            handler=handler,
            input_schema=input_schema,
            requires_confirmation=req_conf
        )

    @classmethod
    def get_tool(cls, name: str) -> ToolRegistration:
        if name not in cls._REGISTRY:
            raise ToolAccessError(
                f"Unauthorized tool invocation: '{name}' is not in the approved ClubOps Tool Registry. "
                f"Arbitrary tool or script execution is strictly forbidden."
            )
        return cls._REGISTRY[name]

    @classmethod
    def check_rate_limit(cls, user_id: int, max_per_minute: int = 40):
        """Guardrail 15: Rate Limit Guardrail."""
        now = time.time()
        user_key = str(user_id)
        if user_key not in cls._RATE_TRACKER:
            cls._RATE_TRACKER[user_key] = []

        # Keep timestamps from the last 60 seconds
        cls._RATE_TRACKER[user_key] = [t for t in cls._RATE_TRACKER[user_key] if now - t < 60]

        if len(cls._RATE_TRACKER[user_key]) >= max_per_minute:
            raise RateLimitError("Rate limit exceeded for AI operations. Please wait before submitting more commands.")

        cls._RATE_TRACKER[user_key].append(now)

    @classmethod
    def check_agent_loop_budget(cls, current_step: int):
        """Guardrail 16: Agent Loop Guardrail."""
        if current_step > cls.MAX_AGENT_STEPS:
            raise AgentLoopLimitError(
                f"Agent step budget exceeded ({current_step} > {cls.MAX_AGENT_STEPS}). "
                f"Execution stopped to prevent infinite agent loop. No partial changes were applied."
            )

    @classmethod
    def validate_arguments(cls, tool_reg: ToolRegistration, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Guardrail 8: Tool Argument Validation."""
        if not tool_reg.input_schema:
            return arguments

        try:
            validated_model = tool_reg.input_schema(**arguments)
            return validated_model.model_dump()
        except ValidationError as e:
            raise ToolArgumentError(
                f"Invalid arguments for tool '{tool_reg.name}': {str(e)}"
            )

    @classmethod
    def execute_or_propose(
        cls,
        tool_name: str,
        arguments: Dict[str, Any],
        user: Any,
        db: Any,
        current_step: int = 1
    ) -> Dict[str, Any]:
        """
        Guardrail 9: Read vs Write Guardrail.
        - If classification is READ: validates arguments, executes immediately.
        - If classification is WRITE or HIGH_RISK_WRITE: blocks direct database write!
          Automatically stages proposal and returns diff for user confirmation.
        """
        cls.check_agent_loop_budget(current_step)
        tool_reg = cls.get_tool(tool_name)
        validated_args = cls.validate_arguments(tool_reg, arguments)

        # READ tools: execute directly in read-only mode with safe error wrapping & retry
        if tool_reg.classification == ToolClassification.READ:
            try:
                data = tool_reg.handler(**validated_args)
            except Exception as e:
                err_str = str(e).lower()
                # If transient database error, retry once safely
                if any(k in err_str for k in ["connection", "operationalerror", "timeout", "temporarily unavailable"]):
                    try:
                        time.sleep(0.5)
                        data = tool_reg.handler(**validated_args)
                    except Exception as retry_e:
                        from app.ai.errors import classify_exception
                        ai_err = classify_exception(retry_e)
                        return {
                            "status": "TOOL_ERROR",
                            "tool": tool_name,
                            "error": ai_err.to_user_dict()["error"]
                        }
                else:
                    from app.ai.errors import classify_exception
                    ai_err = classify_exception(e)
                    return {
                        "status": "TOOL_ERROR",
                        "tool": tool_name,
                        "error": ai_err.to_user_dict()["error"]
                    }

            return {
                "status": "EXECUTED_READ",
                "tool": tool_name,
                "data": data
            }

        # WRITE / HIGH_RISK_WRITE tools: Stage proposal (Guardrail 9, 10, 11)
        from app.guardrails.proposal_guard import ProposalGuard
        
        change_item = {
            "entity_type": validated_args.get("entity_type", "Task"),
            "entity_id": validated_args.get("task_id") or validated_args.get("id"),
            "action": "CREATE" if "create" in tool_name else ("DELETE" if "delete" in tool_name else "UPDATE"),
            "proposed_data": validated_args,
            "previous_data": {},
            "explanation": f"AI action requested via tool: {tool_name}"
        }

        user_id = getattr(user, "id", 1)
        proposal = ProposalGuard.stage_proposal(
            db=db,
            user_id=user_id,
            intent=f"Action via {tool_name}",
            changes=[change_item]
        )

        return {
            "status": "PROPOSAL_CREATED",
            "tool": tool_name,
            "requires_confirmation": True,
            "proposal_id": proposal.id,
            "message": f"Write action '{tool_name}' requires human confirmation. Proposal #{proposal.id} has been staged with diff preview.",
            "diff_preview": validated_args
        }

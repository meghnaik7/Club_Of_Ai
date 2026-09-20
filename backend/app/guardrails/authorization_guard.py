"""
Authorization & Isolation Guardrails (3, 4, 5):
- Authentication Guardrail: Verifies request authenticity from backend token context
- Authorization Guardrail: Ensures user role permissions for requested action
- Tenant / Event Isolation: Prevents access to another club or event's private data
"""
from typing import Optional, Set
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.event import Event
from app.models.task import Task
from app.models.document import Document

class AuthorizationViolationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class TenantIsolationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

PermissionDeniedError = AuthorizationViolationError
AuthGuardError = AuthorizationViolationError

class AuthorizationGuard:
    # Role permission mappings
    ROLE_HIERARCHY = {
        UserRole.ADMIN: 3,
        UserRole.CLUB_MANAGER: 2,
        UserRole.VOLUNTEER: 1,
    }

    @classmethod
    def verify_jwt_token(cls, token: Optional[str]) -> bool:
        if not token or len(token) < 5:
            raise AuthGuardError("Invalid or missing session token.")
        return True

    @classmethod
    def verify_event_boundary(cls, user_event_id: Optional[int], target_event_id: int) -> bool:
        if user_event_id is not None and user_event_id != target_event_id:
            raise TenantIsolationError(
                f"Cross-event violation: User assigned to Event {user_event_id} cannot access Event {target_event_id}."
            )
        return True

    @classmethod
    def verify_tenant_boundary(cls, user_club_id: Optional[int], resource_club_id: int) -> bool:
        if user_club_id is not None and user_club_id != resource_club_id:
            raise TenantIsolationError(
                f"Cross-club tenant violation: User club {user_club_id} cannot access Club {resource_club_id} resources."
            )
        return True

    @classmethod
    def check_role_permission(cls, user: User, action_name: str, required_role: Optional[str] = None) -> bool:
        user_role = getattr(user, "role", UserRole.VOLUNTEER)
        if required_role:
            req_role_enum = UserRole.ADMIN if "ADMIN" in required_role.upper() else (
                UserRole.CLUB_MANAGER if "LEAD" in required_role.upper() or "MANAGER" in required_role.upper() else UserRole.VOLUNTEER
            )
            user_level = cls.ROLE_HIERARCHY.get(user_role, 0)
            req_level = cls.ROLE_HIERARCHY.get(req_role_enum, 0)
            if user_level < req_level:
                raise PermissionDeniedError(
                    f"User role '{user_role.value if hasattr(user_role, 'value') else user_role}' lacks required privilege '{required_role}' for '{action_name}'."
                )
            return True
        return cls.verify_action_permission(user, action_name)

    ACTION_PERMISSIONS = {
        # Read actions - all authenticated users can view their scoped event
        "READ_EVENT": {UserRole.ADMIN, UserRole.CLUB_MANAGER, UserRole.VOLUNTEER},
        "READ_TASK": {UserRole.ADMIN, UserRole.CLUB_MANAGER, UserRole.VOLUNTEER},
        "READ_VOLUNTEER": {UserRole.ADMIN, UserRole.CLUB_MANAGER, UserRole.VOLUNTEER},
        "READ_DOCUMENT": {UserRole.ADMIN, UserRole.CLUB_MANAGER, UserRole.VOLUNTEER},
        "READ_ANNOUNCEMENT": {UserRole.ADMIN, UserRole.CLUB_MANAGER, UserRole.VOLUNTEER},

        # Write actions - restricted
        "CREATE_TASK": {UserRole.ADMIN, UserRole.CLUB_MANAGER},
        "UPDATE_TASK": {UserRole.ADMIN, UserRole.CLUB_MANAGER, UserRole.VOLUNTEER},
        "DELETE_TASK": {UserRole.ADMIN, UserRole.CLUB_MANAGER},
        "ASSIGN_TASK": {UserRole.ADMIN, UserRole.CLUB_MANAGER},
        "BULK_TASK_ACTION": {UserRole.ADMIN, UserRole.CLUB_MANAGER},

        "CREATE_EVENT": {UserRole.ADMIN, UserRole.CLUB_MANAGER},
        "UPDATE_EVENT": {UserRole.ADMIN, UserRole.CLUB_MANAGER},
        "DELETE_EVENT": {UserRole.ADMIN},

        "CREATE_VOLUNTEER": {UserRole.ADMIN, UserRole.CLUB_MANAGER},
        "UPDATE_VOLUNTEER": {UserRole.ADMIN, UserRole.CLUB_MANAGER},
        "DELETE_VOLUNTEER": {UserRole.ADMIN},

        "CREATE_ANNOUNCEMENT": {UserRole.ADMIN, UserRole.CLUB_MANAGER},
        "PUBLISH_ANNOUNCEMENT": {UserRole.ADMIN, UserRole.CLUB_MANAGER},
        "DELETE_ANNOUNCEMENT": {UserRole.ADMIN, UserRole.CLUB_MANAGER},

        "MODIFY_BUDGET": {UserRole.ADMIN, UserRole.CLUB_MANAGER},
        "DELETE_ALL_TASKS": {UserRole.ADMIN},
    }

    @classmethod
    def verify_authenticated_user(cls, current_user: Optional[User]) -> User:
        """Guardrail 3: Verify request has a valid authenticated user."""
        if not current_user or not getattr(current_user, "id", None):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Unauthenticated AI requests are strictly forbidden."
            )
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive."
            )
        return current_user

    @classmethod
    def verify_action_permission(cls, user: User, action: str) -> bool:
        """Guardrail 4: Ensure user has permission to perform the action."""
        cls.verify_authenticated_user(user)
        user_role = user.role
        allowed_roles = cls.ACTION_PERMISSIONS.get(action)

        if allowed_roles is None:
            # High risk or unknown action defaults to ADMIN only
            if user_role != UserRole.ADMIN:
                raise AuthorizationViolationError(
                    f"Action '{action}' is unclassified or restricted to administrators."
                )
            return True

        if user_role not in allowed_roles:
            raise AuthorizationViolationError(
                f"User with role '{user_role.value if hasattr(user_role, 'value') else user_role}' "
                f"is not authorized to perform action '{action}'."
            )
        return True

    @classmethod
    def enforce_event_isolation(
        cls,
        db: Session,
        user: User,
        target_event_id: int,
        requested_entity_type: Optional[str] = None,
        requested_entity_id: Optional[int] = None
    ) -> bool:
        """
        Guardrail 5: Tenant / Event Isolation.
        Verifies that target_event_id exists and the requested entity belongs to it.
        Prevents cross-event data leakage.
        """
        cls.verify_authenticated_user(user)

        # 1. Verify Event exists
        event = db.query(Event).filter(Event.id == target_event_id).first()
        if not event:
            raise TenantIsolationError(f"Target event ID {target_event_id} does not exist.")

        # 2. If an entity is requested, verify it belongs strictly to target_event_id
        if requested_entity_type == "Task" and requested_entity_id:
            task = db.query(Task).filter(Task.id == requested_entity_id).first()
            if not task:
                raise TenantIsolationError(f"Task ID {requested_entity_id} not found.")
            if task.event_id != target_event_id:
                raise TenantIsolationError(
                    f"Cross-event violation: Task {requested_entity_id} belongs to Event {task.event_id}, "
                    f"not target Event {target_event_id}."
                )

        elif requested_entity_type == "Document" and requested_entity_id:
            doc = db.query(Document).filter(Document.id == requested_entity_id).first()
            if not doc:
                raise TenantIsolationError(f"Document ID {requested_entity_id} not found.")
            if doc.event_id is not None and doc.event_id != target_event_id:
                raise TenantIsolationError(
                    f"Cross-event violation: Document {requested_entity_id} belongs to Event {doc.event_id}, "
                    f"not target Event {target_event_id}."
                )

        return True

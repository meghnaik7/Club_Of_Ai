from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.api import deps
from app.core.permissions import ROLE_PERMISSIONS, SYSTEM_PERMISSIONS
from app.models.permission import Permission, UserPermission, ScopeType, PermissionEffect
from app.models.user import User
from app.models.audit_log import AuditLog
from app.services.authz import AuthorizationService

router = APIRouter()


@router.get("/", response_model=List[schemas.Permission])
def list_permissions(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """List all available system permissions."""
    perms = db.query(Permission).order_by(Permission.key).all()
    return perms


@router.get("/matrix", response_model=Dict[str, List[str]])
def get_role_permission_matrix(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get the standard role-to-permissions mapping matrix."""
    return ROLE_PERMISSIONS


@router.get("/users/{user_id}", response_model=List[schemas.UserPermissionResponse])
def get_user_permissions(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get explicit permission overrides for a user."""
    # Self or Club Leader / club.manage
    if current_user.id != user_id:
        AuthorizationService.require_permission(
            db, current_user, "club.manage",
            detail="Only Club Leaders can view other users' explicit permissions"
        )

    overrides = db.query(UserPermission).filter(UserPermission.user_id == user_id).all()
    result = []
    for ov in overrides:
        result.append(
            schemas.UserPermissionResponse(
                id=ov.id,
                user_id=ov.user_id,
                permission_id=ov.permission_id,
                permission_key=ov.permission.key if ov.permission else "",
                scope_type=ov.scope_type.value if hasattr(ov.scope_type, "value") else str(ov.scope_type),
                scope_id=ov.scope_id,
                effect=ov.effect.value if hasattr(ov.effect, "value") else str(ov.effect),
            )
        )
    return result


@router.post("/users/{user_id}", response_model=schemas.UserPermissionResponse)
def add_user_permission_override(
    user_id: int,
    override_in: schemas.UserPermissionCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Grant an explicit ALLOW or DENY permission override to a user (Club Leader only)."""
    AuthorizationService.require_permission(
        db, current_user, "club.manage",
        detail="Only Club Leaders can set permission overrides"
    )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    perm = db.query(Permission).filter(Permission.key == override_in.permission_key).first()
    if not perm:
        raise HTTPException(status_code=400, detail=f"Invalid permission key: {override_in.permission_key}")

    # Parse scope type & effect
    try:
        scope_enum = ScopeType(override_in.scope_type.upper()) if override_in.scope_type else ScopeType.GLOBAL
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid scope_type: {override_in.scope_type}")

    try:
        effect_enum = PermissionEffect(override_in.effect.upper()) if override_in.effect else PermissionEffect.ALLOW
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid effect: {override_in.effect}")

    # Check for existing override on same user + permission + scope
    existing = db.query(UserPermission).filter(
        UserPermission.user_id == user_id,
        UserPermission.permission_id == perm.id,
        UserPermission.scope_type == scope_enum,
        UserPermission.scope_id == override_in.scope_id,
    ).first()

    if existing:
        existing.effect = effect_enum
        db.add(existing)
        db.commit()
        db.refresh(existing)
        override = existing
    else:
        override = UserPermission(
            user_id=user_id,
            permission_id=perm.id,
            scope_type=scope_enum,
            scope_id=override_in.scope_id,
            effect=effect_enum,
        )
        db.add(override)
        db.commit()
        db.refresh(override)

    # Audit log
    audit = AuditLog(
        action=f"PERMISSION_OVERRIDE_{effect_enum.value}",
        actor_id=current_user.id,
        user_id=target_user.id,
        entity_type="USER_PERMISSION",
        entity_id=override.id,
        scope_type=scope_enum.value,
        scope_id=override_in.scope_id,
        meta_data={
            "permission_key": perm.key,
            "effect": effect_enum.value,
            "scope_type": scope_enum.value,
            "scope_id": override_in.scope_id,
            "actor_email": current_user.email,
        }
    )
    db.add(audit)
    db.commit()

    return schemas.UserPermissionResponse(
        id=override.id,
        user_id=override.user_id,
        permission_id=override.permission_id,
        permission_key=perm.key,
        scope_type=override.scope_type.value if hasattr(override.scope_type, "value") else str(override.scope_type),
        scope_id=override.scope_id,
        effect=override.effect.value if hasattr(override.effect, "value") else str(override.effect),
    )


@router.delete("/users/{user_id}/{override_id}")
def delete_user_permission_override(
    user_id: int,
    override_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Remove an explicit permission override from a user (Club Leader only)."""
    AuthorizationService.require_permission(
        db, current_user, "club.manage",
        detail="Only Club Leaders can delete permission overrides"
    )

    override = db.query(UserPermission).filter(
        UserPermission.id == override_id,
        UserPermission.user_id == user_id,
    ).first()
    if not override:
        raise HTTPException(status_code=404, detail="Permission override not found")

    perm_key = override.permission.key if override.permission else str(override.permission_id)
    db.delete(override)

    audit = AuditLog(
        action="PERMISSION_OVERRIDE_DELETE",
        actor_id=current_user.id,
        user_id=user_id,
        entity_type="USER_PERMISSION",
        entity_id=override_id,
        meta_data={
            "permission_key": perm_key,
            "actor_email": current_user.email,
        }
    )
    db.add(audit)
    db.commit()

    return {"ok": True, "message": "Permission override removed successfully"}

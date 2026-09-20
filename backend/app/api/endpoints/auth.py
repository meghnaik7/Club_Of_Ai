from datetime import timedelta
from typing import Any, List
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import schemas
from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.user import User

from pydantic import BaseModel
import os

router = APIRouter()

class DemoLoginRequest(BaseModel):
    demo_account: str


def get_dashboard_redirect_by_role(role: str) -> str:
    role_upper = (role or "").upper()
    if "ADMIN" in role_upper:
        return "/admin/organization"
    elif "CLUB_HEAD" in role_upper or "CLUB_LEADER" in role_upper or "CLUB_MANAGER" in role_upper:
        return "/dashboard"
    elif "SUBTEAM_LEAD" in role_upper or "TEAM_LEADER" in role_upper:
        return "/teams"
    elif "VOLUNTEER" in role_upper or "TEAM_MEMBER" in role_upper:
        return "/dashboard"
    return "/dashboard"


DEMO_ACCOUNT_MAP = {
    "admin": {
        "email": os.getenv("DEMO_ADMIN_EMAIL", "admin@demo.local"),
        "fallback": "admin@clubops.ai",
        "default_name": "Demo Administrator"
    },
    "club_head": {
        "email": os.getenv("DEMO_CLUB_HEAD_EMAIL", "clubhead@demo.local"),
        "fallback": "leader@clubops.ai",
        "default_name": "Demo Club Head"
    },
    "subteam_lead": {
        "email": os.getenv("DEMO_SUBTEAM_LEAD_EMAIL", "teamlead@demo.local"),
        "fallback": "sneha@clubops.ai",
        "default_name": "Demo AI Lead"
    },
    "volunteer": {
        "email": os.getenv("DEMO_VOLUNTEER_EMAIL", "volunteer@demo.local"),
        "fallback": "volunteer@demo.local",
        "default_name": "Demo Volunteer 1"
    }
}


@router.post("/demo-login")
def demo_login(
    payload: DemoLoginRequest,
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Secure demo sign-in.
    The backend maps the demo key to a predefined account and determines
    the actual role from the database record. No client-supplied role is trusted.
    """
    key = payload.demo_account.strip().lower()
    if key not in DEMO_ACCOUNT_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid demo account '{payload.demo_account}'. Supported values: {list(DEMO_ACCOUNT_MAP.keys())}"
        )

    config = DEMO_ACCOUNT_MAP[key]
    primary_email = config["email"]
    fallback_email = config.get("fallback")

    # Search user in database
    user = db.query(User).filter(User.email == primary_email).first()
    if not user and fallback_email:
        user = db.query(User).filter(User.email == fallback_email).first()

    # If demo accounts not yet seeded, trigger auto-seed
    if not user:
        try:
            from app.db.seed_teams_and_roles import seed_demo_accounts_and_org
            seed_demo_accounts_and_org(db)
            user = db.query(User).filter(User.email == primary_email).first()
            if not user and fallback_email:
                user = db.query(User).filter(User.email == fallback_email).first()
        except Exception as err:
            pass

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"Demo account for '{key}' ({primary_email}) could not be initialized."
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Demo account is deactivated.")

    # Determine real role from the database user record
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    redirect_url = get_dashboard_redirect_by_role(role_val)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = security.create_access_token(user.id, expires_delta=access_token_expires)

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role_val,
        "redirect_url": redirect_url,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": role_val,
            "club_id": user.club_id,
            "subteam_id": user.subteam_id
        }
    }


@router.post("/login", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/register", response_model=schemas.User)
def register_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserCreate,
) -> Any:
    """
    Register new user.
    """
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user_obj = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role if user_in.role else "VOLUNTEER"
    )
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj

@router.get("/me", response_model=schemas.User)
def read_user_me(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get current user.
    """
    return current_user


@router.get("/users", response_model=List[schemas.User])
def read_users(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get list of all users.
    """
    return db.query(User).all()
@router.get("/me/summary", response_model=schemas.UserAuthzSummary)
def read_user_authz_summary(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get current user authorization profile including roles, teams, and permissions.
    """
    from app.services.authz import AuthorizationService
    return AuthorizationService.get_user_authz_summary(db, current_user)


@router.get("/me/permissions")
def read_user_permissions(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get effective permission keys list for current user.
    """
    from app.services.authz import AuthorizationService
    summary = AuthorizationService.get_user_authz_summary(db, current_user)
    return summary.get("permissions", [])


@router.get("/me/teams")
def read_user_teams(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get all teams and roles for the current user.
    """
    from app.services.authz import AuthorizationService
    summary = AuthorizationService.get_user_authz_summary(db, current_user)
    return summary.get("teams", [])


@router.get("/me/events")
def read_user_events(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get event roles for the current user.
    """
    from app.services.authz import AuthorizationService
    summary = AuthorizationService.get_user_authz_summary(db, current_user)
    return summary.get("event_roles", [])


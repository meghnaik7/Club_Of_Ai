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

router = APIRouter()

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



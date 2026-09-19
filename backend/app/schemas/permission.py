from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class PermissionBase(BaseModel):
    key: str
    description: Optional[str] = None

class Permission(PermissionBase):
    id: int

    class Config:
        from_attributes = True

class UserPermissionCreate(BaseModel):
    permission_key: str
    scope_type: Optional[str] = "GLOBAL"
    scope_id: Optional[int] = None
    effect: Optional[str] = "ALLOW"

class UserPermissionResponse(BaseModel):
    id: int
    user_id: int
    permission_id: int
    permission_key: str
    scope_type: str
    scope_id: Optional[int] = None
    effect: str

    class Config:
        from_attributes = True

class UserTeamSummary(BaseModel):
    id: int
    name: str
    role: str

class UserEventSummary(BaseModel):
    event_id: int
    role: str

class UserAuthzSummary(BaseModel):
    user_id: int
    full_name: str
    email: str
    is_club_leader: bool
    club_role: Optional[str] = None
    teams: List[UserTeamSummary] = []
    event_roles: List[UserEventSummary] = []
    permissions: List[str] = []

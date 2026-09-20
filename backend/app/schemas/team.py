from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None

class TeamCreate(TeamBase):
    club_id: Optional[int] = None

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class TeamMemberResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    email: str
    role: str
    joined_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class Team(TeamBase):
    id: int
    club_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    member_count: Optional[int] = 0
    leader: Optional[TeamMemberResponse] = None
    members: Optional[List[TeamMemberResponse]] = []

    model_config = ConfigDict(from_attributes=True)

class TeamMemberAdd(BaseModel):
    user_id: int
    role: Optional[str] = "TEAM_MEMBER"

class TeamLeaderAssign(BaseModel):
    user_id: int

class ClubBase(BaseModel):
    name: str
    description: Optional[str] = None

class ClubCreate(ClubBase):
    pass

class Club(ClubBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

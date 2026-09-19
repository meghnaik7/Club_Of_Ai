from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models.volunteer import VolunteerStatus

class VolunteerBase(BaseModel):
    skills: Optional[str] = None
    availability: Optional[str] = None
    max_capacity: Optional[int] = 10
    status: Optional[VolunteerStatus] = VolunteerStatus.ACTIVE

class VolunteerCreate(VolunteerBase):
    user_id: int

class VolunteerUpdate(VolunteerBase):
    pass

class VolunteerInDBBase(VolunteerBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)

# Used to return User info alongside Volunteer info
class UserInfo(BaseModel):
    id: int
    full_name: str
    email: str
    model_config = ConfigDict(from_attributes=True)

class Volunteer(VolunteerInDBBase):
    user: Optional[UserInfo] = None
    
class VolunteerResponse(Volunteer):
    active_task_count: int = 0
    load_indicator: str = "LOW"

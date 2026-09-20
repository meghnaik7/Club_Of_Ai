from sqlalchemy import Boolean, Column, Integer, String, Enum, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.db.base_class import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    CLUB_HEAD = "CLUB_HEAD"
    CLUB_MANAGER = "CLUB_MANAGER"  # Distinct value for legacy rows
    SUBTEAM_LEAD = "SUBTEAM_LEAD"
    TEAM_LEADER = "TEAM_LEADER"    # Distinct value for legacy rows
    VOLUNTEER = "VOLUNTEER"
    TEAM_MEMBER = "TEAM_MEMBER"    # Distinct value for legacy rows


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VOLUNTEER, nullable=False)
    is_active = Column(Boolean, default=True)
    phone = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    skills = Column(String, nullable=True)
    availability = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=True)

    # Direct organizational assignment
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="SET NULL"), nullable=True, index=True)
    subteam_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)

    volunteer_profile = relationship("Volunteer", back_populates="user", uselist=False)
    club = relationship("Club", foreign_keys=[club_id])
    subteam = relationship("Team", foreign_keys=[subteam_id])


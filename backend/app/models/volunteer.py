from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.db.base_class import Base

class VolunteerStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class Volunteer(Base):
    __tablename__ = "volunteers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=True, index=True)
    subteam_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    skills = Column(String, nullable=True)  # Stored as comma-separated list
    availability = Column(String, nullable=True)  # Stored as comma-separated list
    max_capacity = Column(Integer, default=10, nullable=False)  # e.g. hours per week
    status = Column(Enum(VolunteerStatus), default=VolunteerStatus.ACTIVE, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="volunteer_profile")
    club = relationship("Club", foreign_keys=[club_id])
    subteam = relationship("Team", foreign_keys=[subteam_id])
    task_assignments = relationship("TaskAssignment", back_populates="volunteer")

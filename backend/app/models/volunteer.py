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
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    skills = Column(String, nullable=True) # Stored as comma-separated list
    availability = Column(String, nullable=True) # Stored as comma-separated list
    max_capacity = Column(Integer, default=10, nullable=False) # e.g. hours per week
    status = Column(Enum(VolunteerStatus), default=VolunteerStatus.ACTIVE, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="volunteer_profile")
    task_assignments = relationship("TaskAssignment", back_populates="volunteer")

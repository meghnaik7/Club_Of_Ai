from sqlalchemy import Boolean, Column, Integer, String, Enum
from sqlalchemy.orm import relationship
import enum

from app.db.base_class import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    CLUB_MANAGER = "CLUB_MANAGER"
    VOLUNTEER = "VOLUNTEER"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VOLUNTEER, nullable=False)
    is_active = Column(Boolean, default=True)

    volunteer_profile = relationship("Volunteer", back_populates="user", uselist=False)

import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class TeamRole(str, enum.Enum):
    SUBTEAM_LEAD = "SUBTEAM_LEAD"
    TEAM_LEADER = "TEAM_LEADER"
    VOLUNTEER = "VOLUNTEER"
    TEAM_MEMBER = "TEAM_MEMBER"


class ClubRole(str, enum.Enum):
    CLUB_HEAD = "CLUB_HEAD"
    CLUB_LEADER = "CLUB_LEADER"



class EventRole(str, enum.Enum):
    EVENT_COORDINATOR = "EVENT_COORDINATOR"
    EVENT_MEMBER = "EVENT_MEMBER"


class Club(Base):
    __tablename__ = "clubs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    teams = relationship("Team", back_populates="club", cascade="all, delete-orphan")
    memberships = relationship("ClubMembership", back_populates="club", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    lead_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    club = relationship("Club", back_populates="teams")
    lead = relationship("User", foreign_keys=[lead_id])
    memberships = relationship("TeamMembership", back_populates="team", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="team")


# Alias SubTeam to Team
SubTeam = Team


class TeamMembership(Base):
    __tablename__ = "team_memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum(TeamRole), default=TeamRole.VOLUNTEER, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    team = relationship("Team", back_populates="memberships")
    user = relationship("User", backref="team_memberships")


SubTeamMembership = TeamMembership


class ClubMembership(Base):
    __tablename__ = "club_memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum(ClubRole), default=ClubRole.CLUB_HEAD, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    club = relationship("Club", back_populates="memberships")
    user = relationship("User", backref="club_memberships")


class EventMembership(Base):
    __tablename__ = "event_memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum(EventRole), default=EventRole.EVENT_MEMBER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="event_memberships")
    event = relationship("Event", backref="event_memberships")

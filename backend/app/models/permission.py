import enum
from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ScopeType(str, enum.Enum):
    GLOBAL = "GLOBAL"
    CLUB = "CLUB"
    TEAM = "TEAM"
    EVENT = "EVENT"
    TASK = "TASK"


class PermissionEffect(str, enum.Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    role_mappings = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")
    user_overrides = relationship("UserPermission", back_populates="permission", cascade="all, delete-orphan")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(50), index=True, nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("role", "permission_id", name="uq_role_permission"),
    )

    # Relationships
    permission = relationship("Permission", back_populates="role_mappings")


class UserPermission(Base):
    __tablename__ = "user_permissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)
    scope_type = Column(Enum(ScopeType), default=ScopeType.GLOBAL, nullable=False)
    scope_id = Column(Integer, nullable=True)
    effect = Column(Enum(PermissionEffect), default=PermissionEffect.ALLOW, nullable=False)

    # Relationships
    permission = relationship("Permission", back_populates="user_overrides")
    user = relationship("User", backref="explicit_permissions")

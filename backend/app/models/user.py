"""User model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    """Application user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    timezone_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_onboarded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", lazy="selectin")
    learning_profile = relationship("LearningProfile", back_populates="user", uselist=False, lazy="selectin")
    events = relationship("Event", back_populates="user", lazy="selectin")

    __table_args__ = (
        Index("ix_users_email_lower", func.lower(email), unique=True),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"

from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey
from datetime import datetime, timezone

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)

    is_verified = Column(Boolean, default=False, nullable=False)

    plan = Column(String(20), default="FREE", nullable=False)

    google_id = Column(String(255), unique=True, nullable=True)

    verification_token_hash = Column(String(255), nullable=True)
    verification_expires_at = Column(DateTime, nullable=True)

    reset_token_hash = Column(String(255), nullable=True)
    reset_expires_at = Column(DateTime, nullable=True)

    reset_code_hash = Column(String(255), nullable=True)
    reset_code_expires_at = Column(DateTime, nullable=True)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    last_login = Column(DateTime, nullable=True)


class ChatAIHistory(Base):
    __tablename__ = "chat_ai_histories"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    session_id = Column(
        String(100),
        nullable=True,
        index=True
    )

    user_message = Column(
        String,
        nullable=False
    )

    ai_reply = Column(
        String,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
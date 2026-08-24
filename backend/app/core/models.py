from sqlalchemy import Boolean, Column, DateTime, Integer, String
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

    # Reset password lama
    reset_token_hash = Column(String(255), nullable=True)
    reset_expires_at = Column(DateTime, nullable=True)

    # Reset password menggunakan kode 6 digit
    reset_code_hash = Column(String(255), nullable=True)
    reset_code_expires_at = Column(DateTime, nullable=True)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    last_login = Column(DateTime, nullable=True)

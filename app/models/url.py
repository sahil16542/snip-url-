from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Text, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class URL(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    short_code: Mapped[str] = mapped_column(
        String(16),
        unique=True,
        nullable=False,
    )

    original_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
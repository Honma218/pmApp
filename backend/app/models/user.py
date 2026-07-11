"""USERS モデル。

ユーザー・ロールを保持する。ロールは staff / manager の 2 種（Phase 1）。
将来のロール追加を見越し、ネイティブ ENUM ではなく String + CHECK 制約で表現する。
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

# Phase 1 で許可するロール。CHECK 制約と共有する。
USER_ROLES = ("staff", "manager")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('staff', 'manager')",
            name="ck_users_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # Google OAuth の subject 識別子（不変・一意）。ステップ3で upsert キーに使う。
    google_sub: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    reports: Mapped[list["Report"]] = relationship(  # noqa: F821
        back_populates="user",
    )

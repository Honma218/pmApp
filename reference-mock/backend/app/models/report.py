"""REPORTS モデル。

業務報告の確定ログ。status=confirmed の報告は確定後不変として扱う
（CLAUDE.md 原則6、後の突合・再生成の前提）。Phase 1 では ai_summary_json は
表示・保存のみで、後段で PROJECTS / INCIDENTS / SKILLS へ正規化しやすい形にしておく。
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

# Phase 1 の報告ステータス。draft（下書き）/ confirmed（確定・不変）。
REPORT_STATUSES = ("draft", "confirmed")


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'confirmed')",
            name="ck_reports_status",
        ),
        Index("ix_reports_user_id_report_date", "user_id", "report_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # { incidents[], achievements[], issues[], skills[] }（Phase 1 は表示・保存のみ）
    ai_summary_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'draft'"),
    )
    # 追加質問の「一度きり対話」状態（設計 9.3）。確定前に質問→回答（3b）が済んだら
    # true。スライス3a はこの値を読むだけで書き込まない（書き込みは3b）。
    followup_done: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="reports")  # noqa: F821

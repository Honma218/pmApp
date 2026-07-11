"""報告 I/O スキーマ。

ステップ5 で入力（自由文）と下書き自動保存に必要な項目を追加する。
要約生成（ステップ6）・確定（ステップ7）・一覧（ステップ8）の項目は後続で拡張する。
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.summary import ReportSummary


class ReportDraftCreate(BaseModel):
    """当日下書きの取得・作成（get-or-create）入力。"""

    report_date: date


class ReportDraftUpdate(BaseModel):
    """下書き自動保存の入力。本文のみを更新する。"""

    raw_text: str


class ReportConfirmIn(BaseModel):
    """確定入力。編集後の要約を固定スキーマで再検証してから受け取る（原則3）。"""

    summary: ReportSummary


class ReportOut(BaseModel):
    """報告の公開表現。前回参照では ai_summary_json も表示に用いる。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    report_date: date
    raw_text: str
    ai_summary_json: dict | None
    status: str
    followup_done: bool
    created_at: datetime


class ReportListItem(BaseModel):
    """一覧用の軽量表現。本文・要約は運ばず、詳細取得で取り寄せる。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_date: date
    status: str
    created_at: datetime

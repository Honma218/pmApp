"""報告ルーティング。

ステップ5 で入力（自由文）・下書き自動保存（PATCH）・前回参照を追加する。
ブラウザからは next.config.mjs の rewrites（/api/* → backend）経由で到達するため、
業務 API は /api 配下に置く。全ての報告アクセスは所有者検証を必ず通す。
要約生成（6）・確定（7）・一覧（8）は後続ステップで追加する。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user, get_owned_report
from app.models.report import Report
from app.models.user import User
from app.schemas.questions import FollowupAnswersIn, FollowupQuestions
from app.schemas.report import (
    ReportConfirmIn,
    ReportDraftCreate,
    ReportDraftUpdate,
    ReportListItem,
    ReportOut,
)
from app.services import reports as reports_service
from app.services.summarizer import Summarizer, get_summarizer

router = APIRouter(prefix="/api/reports", tags=["reports"])


def get_summarizer_dependency() -> Summarizer:
    """要約プロバイダを設定駆動で解決して返す依存。テストで override 可能。

    API 層は具体プロバイダを import せず、Summarizer インターフェースのみに依存する。
    """
    return get_summarizer()


@router.post("", response_model=ReportOut)
def create_or_get_draft(
    payload: ReportDraftCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Report:
    """指定日の自分の下書きを取得（無ければ作成）する。get-or-create。"""
    return reports_service.get_or_create_draft(db, current_user, payload.report_date)


@router.get("", response_model=list[ReportListItem])
def list_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Report]:
    """自分の確定済み報告を新しい順に一覧する（閲覧用）。"""
    return reports_service.list_confirmed_reports(db, current_user)


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report: Report = Depends(get_owned_report)) -> Report:
    """所有者本人のみが自分の報告を取得できる。他人の報告は 403。"""
    return report


@router.patch("/{report_id}", response_model=ReportOut)
def update_report_draft(
    payload: ReportDraftUpdate,
    report: Report = Depends(get_owned_report),
    db: Session = Depends(get_db),
) -> Report:
    """下書き本文を保存する（自動保存）。確定済みは不変のため 409。"""
    return reports_service.update_draft_text(db, report, payload.raw_text)


@router.get("/{report_id}/previous", response_model=ReportOut | None)
def get_previous_report(
    report: Report = Depends(get_owned_report),
    db: Session = Depends(get_db),
) -> Report | None:
    """アンカー報告の日付より前の、自分の直近の報告を返す（無ければ null）。"""
    return reports_service.get_previous_report(db, report.user, report.report_date)


@router.post("/{report_id}/summarize", response_model=ReportOut)
def summarize_report(
    report: Report = Depends(get_owned_report),
    summarizer: Summarizer = Depends(get_summarizer_dependency),
    db: Session = Depends(get_db),
) -> Report:
    """下書き本文を抽象化層で要約し、結果を draft に保存して返す。確定済みは 409。"""
    return reports_service.summarize_report(db, report, summarizer)


@router.post("/{report_id}/followup-questions", response_model=FollowupQuestions)
def followup_questions(
    report: Report = Depends(get_owned_report),
    summarizer: Summarizer = Depends(get_summarizer_dependency),
    db: Session = Depends(get_db),
) -> FollowupQuestions:
    """薄い項目への追加質問を生成して返す（スライス3a・配線のみ）。

    確定済みは 409、要約未生成は 422、followup_done 済みは空を返す。生成失敗時は
    degrade で空（報告は確定可能）。回答の本文追記・要約再生成は3bで行う。
    """
    return reports_service.generate_followup_questions(db, report, summarizer)


@router.post("/{report_id}/followup-answers", response_model=ReportOut)
def followup_answers(
    payload: FollowupAnswersIn,
    report: Report = Depends(get_owned_report),
    summarizer: Summarizer = Depends(get_summarizer_dependency),
    db: Session = Depends(get_db),
) -> Report:
    """追加質問への回答を本文へ追記し、要約を作り直して返す（スライス3b）。

    確定済みは 409、followup_done 済みは 409（二重防止）、回答なしは 422。再要約失敗時は
    追記ごとロールバックして 502（案A：raw_text だけ残さない）。成功時は更新後の報告を返す。
    """
    return reports_service.answer_followup(db, report, summarizer, payload.answers)


@router.post("/{report_id}/confirm", response_model=ReportOut)
def confirm_report(
    payload: ReportConfirmIn,
    report: Report = Depends(get_owned_report),
    db: Session = Depends(get_db),
) -> Report:
    """編集後の要約で報告を確定する（status=confirmed）。確定後は不変。"""
    return reports_service.confirm_report(db, report, payload.summary)

"""報告のドメインロジック（ステップ5: 入力・下書き自動保存・前回参照）。

ルーティングは薄く保ち、取得/作成・更新・前回参照の判断はここに集約する。
権限境界（所有者検証）はルーティング側の get_owned_report / 現在ユーザーで担保する前提。
"""

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report import Report
from app.models.user import User
from app.schemas.questions import FollowupAnswer, FollowupQuestions
from app.schemas.summary import ReportSummary
from app.services.report_quality import generate_followup_or_none
from app.services.summarizer import Summarizer, SummarizerError


def _require_draft(report: Report) -> None:
    """確定済み（confirmed）は不変（原則6）。draft 以外の変更操作を 409 で拒否する。"""
    if report.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="confirmed report is immutable",
        )


def get_or_create_draft(db: Session, user: User, report_date: date) -> Report:
    """指定日の報告を取得する。無ければ draft を作成して返す（冪等な get-or-create）。

    同一日の報告が既にある場合（draft / confirmed いずれも）はそれを返す。
    確定済みの日に対しても既存を返し、編集可否は更新側で status により判定する。
    """
    existing = db.scalars(
        select(Report)
        .where(Report.user_id == user.id, Report.report_date == report_date)
        .order_by(Report.created_at.desc())
        .limit(1)
    ).first()
    if existing is not None:
        return existing

    report = Report(user_id=user.id, report_date=report_date, raw_text="", status="draft")
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def update_draft_text(db: Session, report: Report, raw_text: str) -> Report:
    """下書き本文を更新する。確定済み（confirmed）は不変のため 409。

    CLAUDE.md 原則6: 確定後の報告は不変。下書きのみ編集を許す。
    """
    _require_draft(report)
    report.raw_text = raw_text
    db.commit()
    db.refresh(report)
    return report


def summarize_report(db: Session, report: Report, summarizer: Summarizer) -> Report:
    """下書き本文を抽象化層で要約し、結果を draft の ai_summary_json に保存して返す。

    - draft 以外（confirmed）は 409（不変）。
    - 本文が空のときは要約対象が無いため 422。
    - 具体プロバイダには依存せず Summarizer インターフェース越しに呼ぶ（原則2）。
    """
    _require_draft(report)
    if not report.raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="raw_text is empty",
        )
    try:
        summary = summarizer.summarize(report.raw_text)
    except SummarizerError as exc:
        # プロバイダ起因の失敗は 502（上流依存の失敗）として扱う。
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="summarization failed",
        ) from exc
    report.ai_summary_json = summary.model_dump()
    db.commit()
    db.refresh(report)
    return report


def generate_followup_questions(
    db: Session, report: Report, summarizer: Summarizer
) -> FollowupQuestions:
    """保存済み要約の薄い項目に対する追加質問を生成して返す（スライス3a）。

    - draft 以外（confirmed）は 409（原則6：確定後不変）。
    - 要約（ai_summary_json）が未生成なら 422（要約→粒度判定の順を守る）。
    - followup_done が既に true なら再生成せず空を返す（読み取りガード＝一度きり）。
      この関数は followup_done を書き込まない（書き込みは3b）。
    - 検出・生成・degrade は generate_followup_or_none に委譲（再実装しない）。
      対象カテゴリ・しきい値は設定から読む（原則7）。生成は抽象化層越し（原則2）、
      失敗時は質問なし（degrade）で報告は確定可能（10.3）。
    """
    _require_draft(report)
    if report.ai_summary_json is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="summary not generated yet",
        )
    if report.followup_done:
        return FollowupQuestions(questions=[])

    questions = generate_followup_or_none(summarizer, report.ai_summary_json)
    return FollowupQuestions(questions=questions)


def _append_followup_answers(raw_text: str, answers: list[FollowupAnswer]) -> str:
    """既存本文を壊さず、末尾に追加質問の回答ブロックを足す（体裁＝設計5.1）。

    区切り線「---」＋見出し「【追加質問への回答】」の下に、Q（カテゴリ）/ A のペアを並べる。
    元の本文はそのまま保ち、末尾の余分な改行だけ整えて連結する。
    """
    lines = ["---", "【追加質問への回答】"]
    for ans in answers:
        lines.append(f"Q（{ans.category}）: {ans.question.strip()}")
        lines.append(f"A: {ans.answer.strip()}")
    block = "\n".join(lines)

    base = raw_text.rstrip("\n")
    if base:
        return f"{base}\n\n{block}"
    return block


def answer_followup(
    db: Session,
    report: Report,
    summarizer: Summarizer,
    answers: list[FollowupAnswer],
) -> Report:
    """追加質問への回答を本文へ追記し、要約を作り直して確定前状態に戻す（スライス3b）。

    案A（全か無か）：本文追記 → 再要約 → 両方成功で followup_done=true → そこで初めて
    1回コミットする。再要約が失敗（SummarizerError）したら追記ごとロールバックし、
    report は回答前（元の本文・古い要約・followup_done=false）のまま。raw_text だけが
    先にコミットされる状態は作らない（10章 degrade：報告は必ず確定できる）。

    - draft 以外（confirmed）は 409（原則6）。
    - followup_done が既に true なら 409（二重対話の防止＝設計5.x・9.3）。
    - 空・空白のみの回答は記録しない（原則3：空欄は埋めない）。残り0件なら 422。
    - 再要約は summarize_report と同じ抽象化層呼び出し（原則2・3）を使い、再実装しない。
    """
    _require_draft(report)
    if report.followup_done:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="followup already completed",
        )

    recorded = [a for a in answers if a.answer.strip()]
    if not recorded:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="no answers provided",
        )

    # 1) 本文末尾へ追記（この時点ではまだコミットしない）。
    report.raw_text = _append_followup_answers(report.raw_text, recorded)

    # 2) 追記後の本文から要約を作り直す（抽象化層越し）。失敗したら全部巻き戻す。
    try:
        summary = summarizer.summarize(report.raw_text)
    except SummarizerError as exc:
        db.rollback()  # 案A：追記を含めて巻き戻す。raw_text だけ残さない。
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="summarization failed",
        ) from exc

    # 3) 両方成功 → 新しい要約と「対話済み」を立てて、ここで初めて 1 回コミット。
    report.ai_summary_json = summary.model_dump()
    report.followup_done = True
    db.commit()
    db.refresh(report)
    return report


def confirm_report(db: Session, report: Report, summary: ReportSummary) -> Report:
    """編集後の要約で報告を確定する。status=confirmed として格納し、以後不変とする。

    要約は固定スキーマ（ReportSummary）で再検証済みのものを受け取る（原則3）。
    既に確定済みなら 409（原則6）。
    """
    _require_draft(report)
    report.ai_summary_json = summary.model_dump()
    report.status = "confirmed"
    db.commit()
    db.refresh(report)
    return report


def list_confirmed_reports(db: Session, user: User) -> list[Report]:
    """自分の確定済み（confirmed）報告を report_date 降順で返す。

    閲覧（ステップ8）の一覧用。下書き（draft）や他人の報告は含めない。
    """
    return list(
        db.scalars(
            select(Report)
            .where(Report.user_id == user.id, Report.status == "confirmed")
            .order_by(Report.report_date.desc(), Report.created_at.desc())
        )
    )


def get_previous_report(db: Session, user: User, before_date: date) -> Report | None:
    """before_date より前の最新の自分の報告を返す（status 不問）。無ければ None。

    前回本文・前回要約の参照表示に用いる。確定フロー（ステップ7）未実装の段階でも
    直近の入力を参照できるよう status は問わない。
    """
    return db.scalars(
        select(Report)
        .where(Report.user_id == user.id, Report.report_date < before_date)
        .order_by(Report.report_date.desc(), Report.created_at.desc())
        .limit(1)
    ).first()

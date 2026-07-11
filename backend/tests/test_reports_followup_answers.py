"""追加質問への回答処理（粒度判定スライス3b）の HTTP テスト。

検証の核:
- 回答 → 本文末尾へ追記（体裁：区切り線＋見出し＋Q/Aペア）＋要約を作り直す＋followup_done=true。
- 二重防止：followup_done が true の報告は受け付けない（409・summarize は呼ばれない）。
- 確定後不変（原則6）：confirmed は 409。
- 権限境界：他人の報告は 403。
- 回答なし（空・空白のみ）は 422。
- 案A degrade：再要約が SummarizerError → 追記ごとロールバックし、raw_text 未変更・
  ai_summary_json は元のまま・followup_done=false（その後も確定可能）。

Summarizer はネットワーク不要のフェイクに override する。
"""

import pytest

from app.api.reports import get_summarizer_dependency
from app.core.security import get_current_user
from app.main import app
from app.schemas.summary import ReportSummary
from app.services.summarizer import SummarizerError
from tests.conftest import make_report, make_user

OLD_SUMMARY = {"incidents": [], "achievements": [], "issues": ["古い要約"], "skills": []}
ANSWERS = {
    "answers": [
        {"category": "issues", "question": "現在の課題は?", "answer": "レビュー待ちで遅延"},
        {"category": "skills", "question": "使った技術は?", "answer": "FastAPI"},
    ]
}


class FakeSummarizer:
    """渡された本文を記録し、既知の要約を返す決定的フェイク。"""

    def __init__(self) -> None:
        self.received: list[str] = []

    def summarize(self, raw_text: str) -> ReportSummary:
        self.received.append(raw_text)
        return ReportSummary(achievements=["再生成された成果"], skills=["FastAPI"])

    def generate_questions(self, thin_by_category):  # pragma: no cover - 本経路では未使用
        raise AssertionError("generate_questions は呼ばれないはず")


class FailingSummarizer:
    """summarize が必ず失敗するフェイク（案A degrade 検証用）。"""

    def summarize(self, raw_text: str) -> ReportSummary:
        raise SummarizerError("再要約失敗")

    def generate_questions(self, thin_by_category):  # pragma: no cover
        raise AssertionError("generate_questions は呼ばれないはず")


class ExplodingSummarizer:
    """summarize が呼ばれたら失敗するフェイク（呼ばれないことの検証用）。"""

    def summarize(self, raw_text: str) -> ReportSummary:
        raise AssertionError("ガード/検証により summarize は呼ばれないはず")

    def generate_questions(self, thin_by_category):  # pragma: no cover
        raise AssertionError("generate_questions は呼ばれないはず")


@pytest.fixture
def login():
    def _login(user):
        app.dependency_overrides[get_current_user] = lambda: user

    return _login


def _use_summarizer(fake):
    app.dependency_overrides[get_summarizer_dependency] = lambda: fake
    return fake


def _draft(db, owner, *, raw_text="元の本文", summary=OLD_SUMMARY, followup_done=False):
    report = make_report(db, owner=owner, status="draft")
    report.raw_text = raw_text
    report.ai_summary_json = summary
    report.followup_done = followup_done
    db.flush()
    return report


def test_answers_append_to_body_and_regenerate_summary(client, db_session, login):
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = _draft(db_session, owner)
    fake = _use_summarizer(FakeSummarizer())
    login(owner)

    res = client.post(f"/api/reports/{report.id}/followup-answers", json=ANSWERS)

    assert res.status_code == 200
    body = res.json()

    # 本文：元の本文を保ったまま末尾に体裁つきで追記されている。
    expected_raw = (
        "元の本文\n\n"
        "---\n"
        "【追加質問への回答】\n"
        "Q（issues）: 現在の課題は?\n"
        "A: レビュー待ちで遅延\n"
        "Q（skills）: 使った技術は?\n"
        "A: FastAPI"
    )
    assert body["raw_text"] == expected_raw
    # 要約：作り直された内容に置き換わっている（古い要約ではない）。
    assert body["ai_summary_json"]["achievements"] == ["再生成された成果"]
    assert body["ai_summary_json"]["issues"] == []
    # 対話済みフラグが立つ。
    assert body["followup_done"] is True
    # 再要約は「追記後の本文」に対して行われている。
    assert fake.received == [expected_raw]
    # DB にも反映されている。
    db_session.refresh(report)
    assert report.raw_text == expected_raw
    assert report.followup_done is True


def test_answers_rejected_when_followup_done(client, db_session, login):
    # 二重防止：既に followup_done=true なら 409、summarize は呼ばれない。
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = _draft(db_session, owner, followup_done=True)
    _use_summarizer(ExplodingSummarizer())
    login(owner)

    res = client.post(f"/api/reports/{report.id}/followup-answers", json=ANSWERS)

    assert res.status_code == 409
    db_session.refresh(report)
    assert report.raw_text == "元の本文"  # 追記されていない


def test_answers_confirmed_gets_409(client, db_session, login):
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = make_report(db_session, owner=owner, status="confirmed")
    db_session.flush()
    _use_summarizer(ExplodingSummarizer())
    login(owner)

    res = client.post(f"/api/reports/{report.id}/followup-answers", json=ANSWERS)

    assert res.status_code == 409


def test_answers_other_users_report_gets_403(client, db_session, login):
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    other = make_user(db_session, email="x@example.com", google_sub="s-x")
    report = _draft(db_session, owner)
    _use_summarizer(ExplodingSummarizer())
    login(other)

    res = client.post(f"/api/reports/{report.id}/followup-answers", json=ANSWERS)

    assert res.status_code == 403


def test_answers_empty_gets_422(client, db_session, login):
    # 回答が空白のみ → 記録対象なし → 422（抽象化層は呼ばない）。
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = _draft(db_session, owner)
    _use_summarizer(ExplodingSummarizer())
    login(owner)

    res = client.post(
        f"/api/reports/{report.id}/followup-answers",
        json={"answers": [{"category": "issues", "question": "課題は?", "answer": "   "}]},
    )

    assert res.status_code == 422
    db_session.refresh(report)
    assert report.raw_text == "元の本文"


def test_answers_degrade_rolls_back_on_resummarize_failure(client, db_session, login):
    # 案A：再要約失敗 → 追記ごとロールバック。raw_text 未変更・要約は元のまま・
    # followup_done=false（その後も古い要約で確定できる）。
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = _draft(db_session, owner)
    # サービスの db.rollback() がセットアップ行まで巻き戻さないよう、ここで確定させておく
    # （テスト全体は conftest の外側トランザクションで最後に rollback される）。
    db_session.commit()
    _use_summarizer(FailingSummarizer())
    login(owner)

    res = client.post(f"/api/reports/{report.id}/followup-answers", json=ANSWERS)

    assert res.status_code == 502
    db_session.refresh(report)
    assert report.raw_text == "元の本文"  # 追記されていない
    assert report.ai_summary_json == OLD_SUMMARY  # 要約は元のまま
    assert report.followup_done is False  # フラグは立っていない
    assert report.status == "draft"  # 下書きのまま＝この後も確定できる

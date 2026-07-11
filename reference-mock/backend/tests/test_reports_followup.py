"""追加質問エンドポイント（粒度判定スライス3a・配線）の HTTP テスト。

検証の核:
- 薄い項目を持つ下書きに対し質問が返る（抽象化層を DI＝原則2）。
- 一度きりガード：followup_done が true の報告は再生成せず空を返す。
- degrade：生成失敗（SummarizerError）でも 5xx にせず空を返す（報告は確定可能＝10.3）。
- 3a 自身は followup_done を書き込まない（書き込みは3b）。
- 権限境界（他人は 403）・確定後不変（confirmed は 409）・要約未生成は 422。

しきい値・対象カテゴリは get_settings() の既定（min_chars=10・全カテゴリ）に従う。
Summarizer はネットワーク不要のフェイクに override する。
"""

import pytest

from app.api.reports import get_summarizer_dependency
from app.core.security import get_current_user
from app.main import app
from app.schemas.questions import FollowupQuestion, FollowupQuestions
from app.services.summarizer import SummarizerError
from tests.conftest import make_report, make_user

# issues に閾値未満（10文字未満）の薄い項目を1つ持つ要約。
THIN_SUMMARY = {"incidents": [], "achievements": [], "issues": ["短い"], "skills": []}


class FakeQuestionSummarizer:
    """渡された thin_by_category を記録し、固定の質問を返す決定的フェイク。"""

    def __init__(self) -> None:
        self.received = None

    def summarize(self, raw_text):  # pragma: no cover - 本経路では使わない
        raise AssertionError("summarize は呼ばれないはず")

    def generate_questions(self, thin_by_category):
        self.received = dict(thin_by_category)
        return FollowupQuestions(
            questions=[FollowupQuestion(category="issues", question="詳しく教えてください")]
        )


class FailingQuestionSummarizer:
    """generate_questions が必ず失敗するフェイク（degrade 検証用）。"""

    def summarize(self, raw_text):  # pragma: no cover - 本経路では使わない
        raise AssertionError("summarize は呼ばれないはず")

    def generate_questions(self, thin_by_category):
        raise SummarizerError("生成失敗")


class ExplodingQuestionSummarizer:
    """generate_questions が呼ばれたら失敗するフェイク（呼ばれないことの検証用）。"""

    def summarize(self, raw_text):  # pragma: no cover - 本経路では使わない
        raise AssertionError("summarize は呼ばれないはず")

    def generate_questions(self, thin_by_category):
        raise AssertionError("ガードが効くため呼ばれないはず")


@pytest.fixture
def login():
    def _login(user):
        app.dependency_overrides[get_current_user] = lambda: user

    return _login


def _use_summarizer(fake):
    app.dependency_overrides[get_summarizer_dependency] = lambda: fake
    return fake


def _draft_with_summary(db, owner, summary=THIN_SUMMARY, *, followup_done=False):
    report = make_report(db, owner=owner, status="draft")
    report.raw_text = "本日の作業内容"
    report.ai_summary_json = summary
    report.followup_done = followup_done
    db.flush()
    return report


def test_followup_returns_questions_for_thin_draft(client, db_session, login):
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = _draft_with_summary(db_session, owner)
    fake = _use_summarizer(FakeQuestionSummarizer())
    login(owner)

    res = client.post(f"/api/reports/{report.id}/followup-questions")

    assert res.status_code == 200
    assert res.json() == {
        "questions": [{"category": "issues", "question": "詳しく教えてください"}]
    }
    # 同カテゴリの薄い項目テキスト群が素な形で渡る（レイヤーの向き）。
    assert fake.received == {"issues": ["短い"]}


def test_followup_does_not_set_followup_done(client, db_session, login):
    # 3a は読み取りガードのみ。成功して質問を返しても followup_done は false のまま。
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = _draft_with_summary(db_session, owner)
    _use_summarizer(FakeQuestionSummarizer())
    login(owner)

    res = client.post(f"/api/reports/{report.id}/followup-questions")

    assert res.status_code == 200
    db_session.refresh(report)
    assert report.followup_done is False


def test_followup_guard_returns_empty_when_done(client, db_session, login):
    # followup_done=true の報告は再生成せず空（generate_questions は呼ばれない）。
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = _draft_with_summary(db_session, owner, followup_done=True)
    _use_summarizer(ExplodingQuestionSummarizer())
    login(owner)

    res = client.post(f"/api/reports/{report.id}/followup-questions")

    assert res.status_code == 200
    assert res.json() == {"questions": []}


def test_followup_degrades_to_empty_on_failure(client, db_session, login):
    # 生成失敗でも 5xx にせず空を返す（報告は後で確定できる）。
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = _draft_with_summary(db_session, owner)
    _use_summarizer(FailingQuestionSummarizer())
    login(owner)

    res = client.post(f"/api/reports/{report.id}/followup-questions")

    assert res.status_code == 200
    assert res.json() == {"questions": []}


def test_followup_no_summary_gets_422(client, db_session, login):
    # 要約未生成（ai_summary_json が None）は 422。抽象化層は呼ばない。
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = make_report(db_session, owner=owner, status="draft")
    report.raw_text = "本文はあるが未要約"
    db_session.flush()
    _use_summarizer(ExplodingQuestionSummarizer())
    login(owner)

    res = client.post(f"/api/reports/{report.id}/followup-questions")

    assert res.status_code == 422


def test_followup_confirmed_gets_409(client, db_session, login):
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = make_report(db_session, owner=owner, status="confirmed")
    _use_summarizer(FakeQuestionSummarizer())
    login(owner)

    res = client.post(f"/api/reports/{report.id}/followup-questions")

    assert res.status_code == 409


def test_followup_other_users_report_gets_403(client, db_session, login):
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    other = make_user(db_session, email="x@example.com", google_sub="s-x")
    report = _draft_with_summary(db_session, owner)
    _use_summarizer(FakeQuestionSummarizer())
    login(other)

    res = client.post(f"/api/reports/{report.id}/followup-questions")

    assert res.status_code == 403

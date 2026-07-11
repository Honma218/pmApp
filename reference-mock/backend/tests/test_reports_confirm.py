"""要約・確定フロー（ステップ7）の HTTP テスト。

レビュー必須箇所の検証に集中する:
- 抽象化層の配線（Summarizer を DI、フェイクに差し替え可能 = 原則2）
- 確定境界での要約スキーマ再検証（原則3）
- 確定後不変（confirm / summarize / PATCH すべて 409 = 原則6）
- 権限境界（他人の報告は 403）
Summarizer はネットワーク不要のフェイクに override する。
"""

import pytest

from app.api.reports import get_summarizer_dependency
from app.core.security import get_current_user
from app.main import app
from app.schemas.summary import ReportSummary
from tests.conftest import make_report, make_user


class FakeSummarizer:
    """既知の要約を返す決定的フェイク（呼び出し回数も記録）。"""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def summarize(self, raw_text: str) -> ReportSummary:
        self.calls.append(raw_text)
        return ReportSummary(achievements=["生成された成果"], skills=["Python"])


@pytest.fixture
def login():
    def _login(user):
        app.dependency_overrides[get_current_user] = lambda: user

    return _login


@pytest.fixture
def fake_summarizer():
    """要約プロバイダをフェイクに差し替える（差し替え可能性の実証）。"""
    fake = FakeSummarizer()
    app.dependency_overrides[get_summarizer_dependency] = lambda: fake
    return fake


def _draft_with_text(db, owner, text="本日の作業内容"):
    report = make_report(db, owner=owner, status="draft")
    report.raw_text = text
    db.flush()
    return report


# --- summarize -------------------------------------------------------------


def test_summarize_persists_summary_on_draft(client, db_session, login, fake_summarizer):
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = _draft_with_text(db_session, owner)
    login(owner)

    res = client.post(f"/api/reports/{report.id}/summarize")

    assert res.status_code == 200
    body = res.json()
    assert body["ai_summary_json"]["achievements"] == ["生成された成果"]
    assert body["status"] == "draft"  # 要約だけでは確定しない
    assert fake_summarizer.calls == ["本日の作業内容"]
    db_session.refresh(report)
    assert report.ai_summary_json["skills"] == ["Python"]


def test_summarize_empty_text_gets_422(client, db_session, login, fake_summarizer):
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = _draft_with_text(db_session, owner, text="   ")
    login(owner)

    res = client.post(f"/api/reports/{report.id}/summarize")

    assert res.status_code == 422
    assert fake_summarizer.calls == []  # 空なら抽象化層を呼ばない


def test_summarize_confirmed_gets_409(client, db_session, login, fake_summarizer):
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = make_report(db_session, owner=owner, status="confirmed")
    login(owner)

    res = client.post(f"/api/reports/{report.id}/summarize")

    assert res.status_code == 409


def test_summarize_other_users_report_gets_403(client, db_session, login, fake_summarizer):
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    other = make_user(db_session, email="x@example.com", google_sub="s-x")
    report = _draft_with_text(db_session, owner)
    login(other)

    res = client.post(f"/api/reports/{report.id}/summarize")

    assert res.status_code == 403


# --- confirm ---------------------------------------------------------------


def test_confirm_freezes_report_with_edited_summary(client, db_session, login):
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = _draft_with_text(db_session, owner)
    login(owner)

    res = client.post(
        f"/api/reports/{report.id}/confirm",
        json={"summary": {"issues": ["編集した課題"], "skills": ["FastAPI"]}},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "confirmed"
    assert body["ai_summary_json"]["issues"] == ["編集した課題"]
    assert body["ai_summary_json"]["incidents"] == []  # 欠損は空配列に正規化


def test_confirm_rejects_schema_violation(client, db_session, login):
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = _draft_with_text(db_session, owner)
    login(owner)

    # 配列に数値を混入（編集経路でもスキーマを破れない）。
    res = client.post(
        f"/api/reports/{report.id}/confirm",
        json={"summary": {"skills": [123]}},
    )

    assert res.status_code == 422


def test_confirm_then_immutable_across_endpoints(client, db_session, login, fake_summarizer):
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    report = _draft_with_text(db_session, owner)
    login(owner)

    first = client.post(
        f"/api/reports/{report.id}/confirm",
        json={"summary": {"achievements": ["完了"]}},
    )
    assert first.status_code == 200

    # 確定後はあらゆる変更操作が 409。
    assert client.post(f"/api/reports/{report.id}/confirm",
                       json={"summary": {}}).status_code == 409
    assert client.post(f"/api/reports/{report.id}/summarize").status_code == 409
    assert client.patch(f"/api/reports/{report.id}",
                        json={"raw_text": "編集"}).status_code == 409

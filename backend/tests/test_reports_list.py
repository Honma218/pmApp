"""自分の報告一覧（ステップ8）の HTTP テスト。

DoD: 自分の確定済み報告だけが一覧できる。
- draft は除外、他人の報告は含めない
- report_date 降順
- 0件は空配列
- 未認証は 401
"""

from datetime import date

import pytest

from app.core.security import get_current_user
from app.main import app
from app.models.report import Report
from tests.conftest import make_user


@pytest.fixture
def login():
    def _login(user):
        app.dependency_overrides[get_current_user] = lambda: user

    return _login


def _add_report(db, owner, *, report_date, status):
    report = Report(
        user_id=owner.id, report_date=report_date, raw_text="x", status=status
    )
    db.add(report)
    db.flush()
    return report


def test_list_returns_only_own_confirmed_sorted_desc(client, db_session, login):
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    other = make_user(db_session, email="x@example.com", google_sub="s-x")
    _add_report(db_session, owner, report_date=date(2026, 5, 1), status="confirmed")
    _add_report(db_session, owner, report_date=date(2026, 6, 1), status="confirmed")
    _add_report(db_session, owner, report_date=date(2026, 6, 2), status="draft")
    _add_report(db_session, other, report_date=date(2026, 6, 3), status="confirmed")
    login(owner)

    res = client.get("/api/reports")

    assert res.status_code == 200
    body = res.json()
    # 自分の confirmed 2件のみ、新しい順。
    assert [item["report_date"] for item in body] == ["2026-06-01", "2026-05-01"]
    assert all(item["status"] == "confirmed" for item in body)


def test_list_empty_when_no_confirmed(client, db_session, login):
    owner = make_user(db_session, email="o@example.com", google_sub="s-o")
    _add_report(db_session, owner, report_date=date(2026, 6, 1), status="draft")
    login(owner)

    res = client.get("/api/reports")

    assert res.status_code == 200
    assert res.json() == []


def test_list_unauthenticated_gets_401(client, db_session):
    res = client.get("/api/reports")

    assert res.status_code == 401

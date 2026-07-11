"""確定後不変（CLAUDE.md 原則6）の関所テスト。

確定済み（status=confirmed）の報告本文を PATCH しようとすると 409 で拒否される。
ステップ3の所有者検証（403）と同格の重要な境界。所有者本人であっても確定後は編集不可。
"""

import pytest

from app.core.security import get_current_user
from app.main import app
from tests.conftest import make_report, make_user


@pytest.fixture
def login():
    """指定ユーザーとしてログイン済みにする（get_current_user を差し替え）。"""

    def _login(user):
        app.dependency_overrides[get_current_user] = lambda: user

    return _login


def test_patch_confirmed_report_gets_409(client, db_session, login):
    owner = make_user(db_session, email="owner@example.com", google_sub="sub-owner")
    report = make_report(db_session, owner=owner, status="confirmed")
    login(owner)

    res = client.patch(f"/api/reports/{report.id}", json={"raw_text": "edited"})

    assert res.status_code == 409

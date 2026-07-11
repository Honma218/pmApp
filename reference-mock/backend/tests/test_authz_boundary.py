"""権限境界の一元テスト（ステップ9）。

DoD「他人のデータに触れない」を、報告 ID 付きの全エンドポイントについて明示的に
回帰テスト化する。いずれも共通の get_owned_report を通すため、非所有者は 403 となる。
個別ステップ（5/7/8）のテストとは独立に、境界の総覧をここで保証する。
"""

import pytest

from app.core.security import get_current_user
from app.main import app
from tests.conftest import make_report, make_user

# (HTTP メソッド, パス接尾辞, ボディ) の組。ボディは 403 到達前の 422 を避けるため有効値。
PER_REPORT_ENDPOINTS = [
    ("get", "", None),
    ("patch", "", {"raw_text": "x"}),
    ("post", "/summarize", None),
    ("post", "/confirm", {"summary": {}}),
    ("get", "/previous", None),
]


@pytest.fixture
def login():
    def _login(user):
        app.dependency_overrides[get_current_user] = lambda: user

    return _login


@pytest.mark.parametrize("method,suffix,body", PER_REPORT_ENDPOINTS)
def test_non_owner_gets_403_on_every_per_report_endpoint(
    client, db_session, login, method, suffix, body
):
    owner = make_user(db_session, email="owner@example.com", google_sub="sub-owner")
    other = make_user(db_session, email="other@example.com", google_sub="sub-other")
    report = make_report(db_session, owner=owner, status="draft")
    login(other)  # 所有者ではない別ユーザーとしてアクセス

    res = client.request(method, f"/api/reports/{report.id}{suffix}", json=body)

    assert res.status_code == 403

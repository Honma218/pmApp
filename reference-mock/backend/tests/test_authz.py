"""権限境界（所有者検証）の HTTP レベルテスト。

ステップ3 DoD の中核: 他人の report_id へのアクセスが 403 になること。
認証済みユーザーは get_current_user の依存性差し替えで表現し、所有者検証
（get_owned_report）の挙動に焦点を当てる。
"""

import uuid

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


def test_owner_can_read_own_report(client, db_session, login):
    owner = make_user(db_session, email="owner@example.com", google_sub="sub-owner")
    report = make_report(db_session, owner=owner)
    login(owner)

    res = client.get(f"/api/reports/{report.id}")

    assert res.status_code == 200
    body = res.json()
    assert body["id"] == str(report.id)
    assert body["user_id"] == str(owner.id)


def test_other_user_gets_403_on_someone_elses_report(client, db_session, login):
    owner = make_user(db_session, email="owner@example.com", google_sub="sub-owner")
    other = make_user(db_session, email="other@example.com", google_sub="sub-other")
    report = make_report(db_session, owner=owner)
    login(other)

    res = client.get(f"/api/reports/{report.id}")

    assert res.status_code == 403


def test_unknown_report_id_gets_404(client, db_session, login):
    owner = make_user(db_session, email="owner@example.com", google_sub="sub-owner")
    login(owner)

    res = client.get(f"/api/reports/{uuid.uuid4()}")

    assert res.status_code == 404


def test_unauthenticated_gets_401(client, db_session):
    owner = make_user(db_session, email="owner@example.com", google_sub="sub-owner")
    report = make_report(db_session, owner=owner)
    # ログインしない（セッション無し）

    res = client.get(f"/api/reports/{report.id}")

    assert res.status_code == 401

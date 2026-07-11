"""get_current_user（セッション→ユーザー解決）の単体テスト。"""

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.security import get_current_user
from tests.conftest import make_user


def _request_with_session(session: dict) -> SimpleNamespace:
    """request.session のみを持つ最小のスタブ。"""
    return SimpleNamespace(session=session)


def test_valid_session_resolves_user(db_session):
    user = make_user(db_session, email="u@example.com", google_sub="sub-u")
    req = _request_with_session({"user_id": str(user.id)})

    got = get_current_user(req, db_session)

    assert got.id == user.id


def test_empty_session_raises_401(db_session):
    with pytest.raises(HTTPException) as ei:
        get_current_user(_request_with_session({}), db_session)
    assert ei.value.status_code == 401


def test_malformed_user_id_raises_401(db_session):
    req = _request_with_session({"user_id": "not-a-uuid"})
    with pytest.raises(HTTPException) as ei:
        get_current_user(req, db_session)
    assert ei.value.status_code == 401


def test_unknown_user_id_raises_401(db_session):
    req = _request_with_session({"user_id": str(uuid.uuid4())})
    with pytest.raises(HTTPException) as ei:
        get_current_user(req, db_session)
    assert ei.value.status_code == 401

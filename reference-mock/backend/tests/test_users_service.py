"""upsert_user（ユーザー upsert・許可ドメイン検証）のテスト。"""

from types import SimpleNamespace

import pytest

import app.services.users as users_mod
from app.services.users import DEFAULT_ROLE, DomainNotAllowedError, upsert_user


def test_new_user_is_created_as_staff(db_session):
    user = upsert_user(
        db_session, google_sub="g-new", email="new@example.com", name="New"
    )
    assert user.id is not None
    assert user.role == DEFAULT_ROLE


def test_existing_user_is_updated_not_duplicated(db_session):
    first = upsert_user(
        db_session, google_sub="g-dup", email="old@example.com", name="Old"
    )
    first_id = first.id

    second = upsert_user(
        db_session, google_sub="g-dup", email="updated@example.com", name="Updated"
    )

    assert second.id == first_id
    assert second.email == "updated@example.com"
    assert second.name == "Updated"
    assert second.role == DEFAULT_ROLE  # ロールは upsert で変更しない


def test_disallowed_domain_is_rejected(db_session, monkeypatch):
    monkeypatch.setattr(
        users_mod,
        "get_settings",
        lambda: SimpleNamespace(ALLOWED_EMAIL_DOMAIN="corp.example"),
    )
    with pytest.raises(DomainNotAllowedError):
        upsert_user(
            db_session, google_sub="g-bad", email="intruder@other.com", name="X"
        )


def test_allowed_domain_passes(db_session, monkeypatch):
    monkeypatch.setattr(
        users_mod,
        "get_settings",
        lambda: SimpleNamespace(ALLOWED_EMAIL_DOMAIN="corp.example"),
    )
    user = upsert_user(
        db_session, google_sub="g-ok", email="staff@corp.example", name="OK"
    )
    assert user.role == DEFAULT_ROLE

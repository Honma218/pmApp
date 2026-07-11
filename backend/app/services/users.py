"""ユーザー関連のドメインロジック。

OAuth で確認した本人情報から USERS を upsert する。許可ドメインの検証もここで行う
（権限境界・アクセス制御はバックエンドで強制する: CLAUDE.md 原則1）。
具体的な OAuth プロバイダには依存しない。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User

# 初回ログイン時の既定ロール。manager への昇格は当面 DB で手動運用する。
DEFAULT_ROLE = "staff"


class DomainNotAllowedError(Exception):
    """許可ドメイン外のメールでログインしようとした場合に送出する。"""

    def __init__(self, email: str) -> None:
        super().__init__(f"email domain not allowed: {email}")
        self.email = email


def _assert_domain_allowed(email: str) -> None:
    """ALLOWED_EMAIL_DOMAIN が設定されていれば末尾一致を検証する。"""
    allowed = get_settings().ALLOWED_EMAIL_DOMAIN
    if not allowed:
        return
    domain = email.rsplit("@", 1)[-1].lower()
    if domain != allowed.lower():
        raise DomainNotAllowedError(email)


def upsert_user(db: Session, *, google_sub: str, email: str, name: str) -> User:
    """google_sub をキーにユーザーを作成 or 更新して返す。

    - 新規: role=staff で作成。
    - 既存: email / name を最新で上書き（ロールは変更しない）。
    許可ドメイン外の場合は DomainNotAllowedError を送出する。
    """
    _assert_domain_allowed(email)

    user = db.execute(
        select(User).where(User.google_sub == google_sub)
    ).scalar_one_or_none()

    if user is None:
        user = User(
            google_sub=google_sub,
            email=email,
            name=name,
            role=DEFAULT_ROLE,
        )
        db.add(user)
    else:
        user.email = email
        user.name = name

    db.commit()
    db.refresh(user)
    return user

"""認可（アクセス境界の強制）。

CLAUDE.md 原則1: 権限境界はバックエンドで強制する。フロントの出し分けに依存しない。
ここでは FastAPI の依存性として「現在のユーザー解決」と「所有者検証」を提供し、
全ての保護エンドポイントがこれを通る形にする。

Phase 1 の方針: deny-by-default。報告は所有者本人のみアクセス可。
（管理者のグループ横断アクセスは group_id 未導入のため後フェーズ。）
"""

import uuid

from fastapi import Depends, HTTPException, Path, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.report import Report
from app.models.user import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """署名付きセッションの user_id から現在のユーザーを解決する。

    未ログイン・不正セッション・該当ユーザー無しはいずれも 401。
    """
    raw_id = request.session.get("user_id")
    if not raw_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not authenticated",
        )
    try:
        user_id = uuid.UUID(str(raw_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid session",
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user not found",
        )
    return user


def get_owned_report(
    report_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Report:
    """report_id の報告を取得し、所有者でなければ拒否する。

    - 存在しない: 404
    - 存在するが他人のもの: 403（所有の有無は明かすが内容は返さない）

    これが Phase 1 の権限境界の中核。報告を扱う保護エンドポイントは必ずこれを通す。
    """
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="report not found",
        )
    if report.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )
    return report

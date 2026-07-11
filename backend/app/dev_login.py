"""開発専用のログイン回避（本番では絶対に有効化しないこと）。

ローカルで Google ログイン無しに一連の流れ（入力→要約→確認→確定）を触るための
仕組み。本番の認証・権限境界コード（core/security.py, api/auth.py）は一切変更せず、
本物と同じセッション機構で開発用ユーザーのセッションを張るだけにする。

二重の安全弁:
1. このルートは専用起動口 app.dev_main からのみ読み込まれる（本番の app.main は含まない）。
2. 環境変数 DEV_AUTH_BYPASS=true のときだけ有効。無ければ起動拒否 / 404。
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.users import upsert_user

# 開発用ユーザーの固定情報。ALLOWED_EMAIL_DOMAIN 未設定なら upsert_user を通る。
_DEV_GOOGLE_SUB = "dev-local-user"
_DEV_EMAIL = "dev@example.com"
_DEV_NAME = "ローカル開発ユーザー"

router = APIRouter(prefix="/auth", tags=["dev"])


def is_enabled() -> bool:
    """開発用ログインが有効か（DEV_AUTH_BYPASS=true のときだけ True）。"""
    return os.environ.get("DEV_AUTH_BYPASS", "").lower() == "true"


def ensure_enabled() -> None:
    """無効な環境での誤起動を防ぐ安全弁。dev_main 起動時に呼ぶ。"""
    if not is_enabled():
        raise RuntimeError(
            "DEV_AUTH_BYPASS=true でないため開発用ログインは起動できません。"
            "本番では app.main:app を使用してください。"
        )


@router.get("/dev-login")
def dev_login(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    """開発用ユーザーで本物のセッションを張り、入力画面へ送る。

    本物の OAuth コールバックと同じく request.session に user_id を入れるだけで、
    以降のアクセスは通常の get_current_user / get_owned_report が処理する。
    """
    if not is_enabled():
        # 万一有効化されていない環境に存在しても、経路自体を塞ぐ。
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

    user = upsert_user(
        db,
        google_sub=_DEV_GOOGLE_SUB,
        email=_DEV_EMAIL,
        name=_DEV_NAME,
    )
    request.session["user_id"] = str(user.id)
    return RedirectResponse(url="/report", status_code=status.HTTP_302_FOUND)

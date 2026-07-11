"""認証ルーティング（Google OAuth 2.0）。

ルーティングは薄く保ち、ユーザーの永続化・ドメイン検証は services 層に委ねる。
"""

from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.oauth import oauth
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.user import UserOut
from app.services.users import DomainNotAllowedError, upsert_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request):
    """Google の同意画面へリダイレクトする。"""
    settings = get_settings()
    redirect_uri = settings.OAUTH_REDIRECT_URI or str(
        request.url_for("auth_callback")
    )
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback", name="auth_callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    """OAuth コールバック。トークンを検証し、ユーザーを upsert してセッションを張る。"""
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="oauth failed",
        )

    userinfo = token.get("userinfo")
    if not userinfo or not userinfo.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing user info",
        )
    if not userinfo.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="email not verified",
        )

    try:
        user = upsert_user(
            db,
            google_sub=userinfo["sub"],
            email=userinfo["email"],
            name=userinfo.get("name") or userinfo["email"],
        )
    except DomainNotAllowedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="email domain not allowed",
        )

    request.session["user_id"] = str(user.id)
    return RedirectResponse(
        url=get_settings().POST_LOGIN_REDIRECT_URL,
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    """セッションを破棄する。"""
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    """現在ログイン中のユーザーを返す。"""
    return current_user

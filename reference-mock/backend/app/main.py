"""FastAPI アプリのエントリポイント。

ステップ3で認証（Google OAuth）と権限境界を追加。SessionMiddleware による
署名付き Cookie でセッションを保持し、報告アクセスは所有者検証を必ず通す。
"""

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.api import auth, reports
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="業務報告・スキルシート生成システム", version="0.1.0")

# セッションは SESSION_SECRET で署名した httpOnly Cookie に保持する。
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET,
    session_cookie="session",
    same_site="lax",
    https_only=settings.COOKIE_SECURE,
)

app.include_router(auth.router)
app.include_router(reports.router)


@app.get("/health")
def health() -> dict[str, str]:
    """死活監視用エンドポイント。常に 200 を返す。"""
    return {"status": "ok"}

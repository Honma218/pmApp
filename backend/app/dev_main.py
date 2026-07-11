"""開発専用の起動口（uvicorn app.dev_main:app）。

本番アプリ（app.main:app）をそのまま読み込み、開発用ログインルートだけを足す。
本番は引き続き app.main:app を使うこと。こちらは DEV_AUTH_BYPASS=true が無いと
起動を拒否する（dev_login.ensure_enabled）。
"""

from app.dev_login import ensure_enabled
from app.dev_login import router as dev_login_router
from app.main import app

# DEV_AUTH_BYPASS=true でなければここで起動を止める（本番混入防止の安全弁）。
ensure_enabled()

app.include_router(dev_login_router)

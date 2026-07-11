"""アプリケーション設定。

`.env` / 環境変数から設定値を読み込む。Phase 1 ステップ2 の範囲では DB 接続のみ
が必須。OAuth / AI など後続ステップで使う値は任意（未設定でも起動を妨げない）。
シークレットはコミットしない（CLAUDE.md 原則10）。
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.schemas.summary import SUMMARY_FIELDS


class Settings(BaseSettings):
    """環境変数で上書き可能なアプリ設定。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- DB（ステップ2で必須） ---
    # 例: postgresql+psycopg://localhost/staff_report
    DATABASE_URL: str = "postgresql+psycopg://localhost/staff_report"

    # --- 認証（ステップ3） ---
    GOOGLE_OAUTH_CLIENT_ID: str | None = None
    GOOGLE_OAUTH_CLIENT_SECRET: str | None = None
    OAUTH_REDIRECT_URI: str | None = None
    # 設定時、この末尾ドメインのメールのみログインを許可する（ホワイトリスト）。
    ALLOWED_EMAIL_DOMAIN: str | None = None
    # セッション Cookie の署名鍵。本番では必ず十分に長い値を環境変数で設定すること。
    SESSION_SECRET: str = "dev-insecure-secret-change-me"
    # ログイン成功後のリダイレクト先（フロントはステップ4で用意）。
    POST_LOGIN_REDIRECT_URL: str = "/"
    # 本番（HTTPS）では True にして Secure Cookie を強制する。
    COOKIE_SECURE: bool = False

    # --- AI 要約（ステップ6で使用、ここでは任意） ---
    # 未設定時は決定的な stub プロバイダを用いる（鍵なしでも動作）。
    # 実プロバイダは gemini / vertex（claude は後続）。具体依存は provider 実装に隔離。
    AI_PROVIDER: str | None = None
    AI_API_KEY: str | None = None
    # 使用モデル（未設定時はプロバイダ既定値）。プロバイダ差し替え時に上書き可能。
    AI_MODEL: str | None = None

    # --- 粒度判定（スライス1） ---
    # 「薄い項目」を検出する対象カテゴリ。仮初期値は4カテゴリすべて（SUMMARY_FIELDS）。
    # 当面は単一の固定値として読む（原則7：分岐を埋めず設定から読む）。管理者が画面で
    # 付け替えられるようにするのは土台スライス（後続）。単位はカテゴリ（項目単位は後続）。
    REPORT_QUALITY_TARGET_CATEGORIES: frozenset[str] = frozenset(SUMMARY_FIELDS)
    # これ未満（前後の空白を除いた文字数）の項目を「薄い」とみなす最小文字数。仮初期値10。
    REPORT_QUALITY_MIN_CHARS: int = 10


@lru_cache
def get_settings() -> Settings:
    """設定のシングルトンを返す（プロセス内でキャッシュ）。"""
    return Settings()

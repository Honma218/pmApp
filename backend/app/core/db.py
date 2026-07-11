"""DB 接続まわり（同期 SQLAlchemy 2.0 + psycopg v3）。

- `Base`: 全 ORM モデルの宣言基底。Alembic の `target_metadata` に使う。
- `engine` / `SessionLocal`: 同期エンジンとセッションファクトリ。
- `get_db`: FastAPI の依存性として 1 リクエスト 1 セッションを払い出す。

タイムゾーンは保存 UTC で統一する（CLAUDE.md 原則9）。timestamptz と
サーバ側 now() を使い、表示側でローカル変換する方針。
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """全 ORM モデルの宣言基底。"""


engine = create_engine(
    get_settings().DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """1 リクエスト 1 セッション。FastAPI の Depends で使う。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

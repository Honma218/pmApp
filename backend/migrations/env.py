"""Alembic 実行環境。

DB URL は alembic.ini ではなく app.core.config の Settings から注入する
（シークレットをコミットしない）。target_metadata は app の Base.metadata。
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings

# app.models を import することで全モデルが Base.metadata に登録される。
from app.core.db import Base  # isort: skip
import app.models  # noqa: F401  side-effect: モデル登録  # isort: skip

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """オフライン（SQL 出力）モードでマイグレーションを実行する。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """オンライン（実 DB 接続）モードでマイグレーションを実行する。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

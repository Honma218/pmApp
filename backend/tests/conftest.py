"""テスト共通フィクスチャ。

DB テストはローカル Postgres（既存の開発 DB）に対してトランザクション接続し、
各テスト終了時にロールバックして DB を汚さない。接続できない環境では skip する。
"""

import os
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.main import app
from app.models.report import Report
from app.models.user import User

# 既定では開発 DB を使い、トランザクションで隔離する（TEST_DATABASE_URL で上書き可）。
TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", get_settings().DATABASE_URL)
engine = create_engine(TEST_DB_URL, future=True)


@pytest.fixture
def db_session():
    """各テストを 1 トランザクションに閉じ込め、終了時にロールバックする。"""
    try:
        connection = engine.connect()
    except OperationalError:
        pytest.skip("PostgreSQL に接続できないため DB テストをスキップ")
    trans = connection.begin()
    # アプリ側の commit() は savepoint で受け、外側トランザクションで巻き戻す。
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    """get_db をテストセッションに差し替えた TestClient。"""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(db: Session, *, email: str, google_sub: str, role: str = "staff",
              name: str = "Test User") -> User:
    """テスト用ユーザーを作成して返す。"""
    user = User(email=email, google_sub=google_sub, role=role, name=name)
    db.add(user)
    db.flush()
    return user


def make_report(db: Session, *, owner: User, status: str = "confirmed") -> Report:
    """owner が所有する報告を作成して返す。"""
    report = Report(
        user_id=owner.id,
        report_date=date(2026, 6, 1),
        raw_text="sample",
        status=status,
    )
    db.add(report)
    db.flush()
    return report

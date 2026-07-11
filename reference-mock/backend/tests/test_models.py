"""モデル定義のスモークテスト（ライブ DB 不要）。

import の side-effect で users / reports が Base.metadata に登録されること、
主要カラムと制約が定義されていることを確認する。
"""

from app.core.db import Base
import app.models  # noqa: F401  side-effect: モデル登録


def test_metadata_has_expected_tables():
    assert set(Base.metadata.tables) == {"users", "reports"}


def test_users_columns():
    cols = Base.metadata.tables["users"].columns
    assert {"id", "google_sub", "email", "name", "role", "created_at"} <= set(cols.keys())


def test_reports_columns():
    cols = Base.metadata.tables["reports"].columns
    assert {
        "id",
        "user_id",
        "report_date",
        "raw_text",
        "ai_summary_json",
        "status",
        "created_at",
    } <= set(cols.keys())

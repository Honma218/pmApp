"""ORM モデルの集約。

Alembic の autogenerate / `Base.metadata` 解決のため、ここで全モデルを import して
おく（モデルの side-effect 登録を一箇所に集約する）。
"""

from app.models.report import Report
from app.models.user import User

__all__ = ["User", "Report"]

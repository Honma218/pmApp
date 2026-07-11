"""reports: followup_done を追加（追加質問の一度きり対話状態・設計 9.3）

Revision ID: 0002_reports_followup_done
Revises: 0001_initial
Create Date: 粒度判定スライス3a

既存行は server_default=false により false で埋まる（NULL は発生しない）。
スライス3a はこの列を読むだけ（書き込みは3b）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_reports_followup_done"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column(
            "followup_done",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("reports", "followup_done")

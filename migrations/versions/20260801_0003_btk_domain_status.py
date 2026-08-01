"""btk domain status

Revision ID: 20260801_0003
Revises: 20260801_0002
Create Date: 2026-08-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260801_0003"
down_revision = "20260801_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("domains", sa.Column("btk_status", sa.Text(), nullable=True))
    op.add_column("domains", sa.Column("btk_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("domains", sa.Column("btk_error", sa.Text(), nullable=True))
    op.create_index("ix_domains_btk_pending", "domains", ["btk_status", "last_checked_at"])


def downgrade() -> None:
    op.drop_index("ix_domains_btk_pending", table_name="domains")
    op.drop_column("domains", "btk_error")
    op.drop_column("domains", "btk_checked_at")
    op.drop_column("domains", "btk_status")

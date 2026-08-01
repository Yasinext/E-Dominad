"""btk note

Revision ID: 20260801_0004
Revises: 20260801_0003
Create Date: 2026-08-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260801_0004"
down_revision = "20260801_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("domains", sa.Column("btk_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("domains", "btk_note")

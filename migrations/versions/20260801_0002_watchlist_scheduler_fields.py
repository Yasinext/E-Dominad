"""watchlist scheduler fields

Revision ID: 20260801_0002
Revises: 20260730_0001
Create Date: 2026-08-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260801_0002"
down_revision = "20260730_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("watchlists", sa.Column("scan_cursor", sa.BigInteger(), nullable=True))
    op.add_column(
        "domain_status_changes",
        sa.Column("scan_job_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_domain_status_changes_scan_job_id_scan_jobs",
        "domain_status_changes",
        "scan_jobs",
        ["scan_job_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_domain_status_changes_scan_job_id_scan_jobs",
        "domain_status_changes",
        type_="foreignkey",
    )
    op.drop_column("domain_status_changes", "scan_job_id")
    op.drop_column("watchlists", "scan_cursor")

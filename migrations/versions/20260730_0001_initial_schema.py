"""initial schema

Revision ID: 20260730_0001
Revises:
Create Date: 2026-07-30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260730_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_groups",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("chat_id"),
    )
    op.create_table(
        "telegram_updates",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("update_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.UniqueConstraint("update_id"),
    )
    op.create_table(
        "scan_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("requested_by", sa.BigInteger(), nullable=False),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("root", sa.Text(), nullable=True),
        sa.Column("range_start", sa.BigInteger(), nullable=True),
        sa.Column("range_end", sa.BigInteger(), nullable=True),
        sa.Column("range_width", sa.Integer(), nullable=True),
        sa.Column("single_domain", sa.Text(), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("completed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("registered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("not_found_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unknown_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.Text(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index(
        "uq_scan_jobs_active_range",
        "scan_jobs",
        ["chat_id", "root", "range_start", "range_end"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )
    op.create_index(
        "uq_scan_jobs_active_single",
        "scan_jobs",
        ["chat_id", "single_domain"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )
    op.create_table(
        "domains",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("current_verified_status", sa.Text(), nullable=True),
        sa.Column("previous_verified_status", sa.Text(), nullable=True),
        sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registration_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiration_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_changed_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registrar_name", sa.Text(), nullable=True),
        sa.Column("registrar_iana_id", sa.Text(), nullable=True),
        sa.Column("rdap_statuses", postgresql.JSONB(), nullable=True),
        sa.Column("nameservers", postgresql.JSONB(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_check_outcome", sa.Text(), nullable=True),
        sa.Column("consecutive_failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("domain"),
    )
    op.create_table(
        "domain_checks",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("domain_id", sa.BigInteger(), sa.ForeignKey("domains.id"), nullable=False),
        sa.Column("scan_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scan_jobs.id")),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("attempt_count", sa.SmallInteger(), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "scan_job_domains",
        sa.Column("scan_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scan_jobs.id")),
        sa.Column("domain_id", sa.BigInteger(), sa.ForeignKey("domains.id"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("verified_status", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("scan_job_id", "domain_id"),
    )
    op.create_index(
        "uq_scan_job_domains_ordinal",
        "scan_job_domains",
        ["scan_job_id", "ordinal"],
        unique=True,
    )
    op.create_table(
        "watchlists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("watch_type", sa.Text(), nullable=False),
        sa.Column("root", sa.Text(), nullable=True),
        sa.Column("range_start", sa.BigInteger(), nullable=True),
        sa.Column("range_end", sa.BigInteger(), nullable=True),
        sa.Column("range_width", sa.Integer(), nullable=True),
        sa.Column("single_domain", sa.Text(), nullable=True),
        sa.Column("frequency", sa.Text(), nullable=False, server_default="weekly"),
        sa.Column(
            "notification_mode",
            sa.Text(),
            nullable=False,
            server_default="newly_registered",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "uq_watchlists_range",
        "watchlists",
        ["chat_id", "root", "range_start", "range_end", "frequency"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE"),
    )
    op.create_index(
        "uq_watchlists_single",
        "watchlists",
        ["chat_id", "single_domain", "frequency"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE"),
    )
    op.create_table(
        "domain_status_changes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("domain_id", sa.BigInteger(), sa.ForeignKey("domains.id"), nullable=False),
        sa.Column("old_status", sa.Text(), nullable=True),
        sa.Column("new_status", sa.Text(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmation_count", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "telegram_outbox",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_by", sa.Text(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("idempotency_key"),
    )


def downgrade() -> None:
    op.drop_table("telegram_outbox")
    op.drop_table("domain_status_changes")
    op.drop_index("uq_watchlists_single", table_name="watchlists")
    op.drop_index("uq_watchlists_range", table_name="watchlists")
    op.drop_table("watchlists")
    op.drop_index("uq_scan_job_domains_ordinal", table_name="scan_job_domains")
    op.drop_table("scan_job_domains")
    op.drop_table("domain_checks")
    op.drop_table("domains")
    op.drop_index("uq_scan_jobs_active_single", table_name="scan_jobs")
    op.drop_index("uq_scan_jobs_active_range", table_name="scan_jobs")
    op.drop_table("scan_jobs")
    op.drop_table("telegram_updates")
    op.drop_table("telegram_groups")

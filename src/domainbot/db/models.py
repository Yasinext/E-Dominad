from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, SmallInteger, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from domainbot.db.base import Base, TimestampMixin


class TelegramGroup(TimestampMixin, Base):
    __tablename__ = "telegram_groups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TelegramUpdate(Base):
    __tablename__ = "telegram_updates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    update_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error_code: Mapped[str | None] = mapped_column(Text)


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    requested_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    job_type: Mapped[str] = mapped_column(Text, nullable=False)
    root: Mapped[str | None] = mapped_column(Text)
    range_start: Mapped[int | None] = mapped_column(BigInteger)
    range_end: Mapped[int | None] = mapped_column(BigInteger)
    range_width: Mapped[int | None] = mapped_column(Integer)
    single_domain: Mapped[str | None] = mapped_column(Text)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    registered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    not_found_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unknown_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(SmallInteger, default=100, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(Text)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    domains: Mapped[list[ScanJobDomain]] = relationship(back_populates="scan_job")

    __table_args__ = (
        Index(
            "uq_scan_jobs_active_range",
            "chat_id",
            "root",
            "range_start",
            "range_end",
            unique=True,
            postgresql_where=status.in_(["queued", "running"]),
        ),
        Index(
            "uq_scan_jobs_active_single",
            "chat_id",
            "single_domain",
            unique=True,
            postgresql_where=status.in_(["queued", "running"]),
        ),
    )


class Domain(TimestampMixin, Base):
    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    domain: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    current_verified_status: Mapped[str | None] = mapped_column(Text)
    previous_verified_status: Mapped[str | None] = mapped_column(Text)
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registration_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expiration_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_changed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registrar_name: Mapped[str | None] = mapped_column(Text)
    registrar_iana_id: Mapped[str | None] = mapped_column(Text)
    rdap_statuses: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    nameservers: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_check_outcome: Mapped[str | None] = mapped_column(Text)
    consecutive_failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    btk_status: Mapped[str | None] = mapped_column(Text)
    btk_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    btk_note: Mapped[str | None] = mapped_column(Text)
    btk_error: Mapped[str | None] = mapped_column(Text)


class DomainCheck(Base):
    __tablename__ = "domain_checks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id"), nullable=False)
    scan_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scan_jobs.id"))
    source: Mapped[str] = mapped_column(Text, nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    error_type: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScanJobDomain(Base):
    __tablename__ = "scan_job_domains"

    scan_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scan_jobs.id"), primary_key=True, nullable=False
    )
    domain_id: Mapped[int] = mapped_column(
        ForeignKey("domains.id"), primary_key=True, nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    verified_status: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    scan_job: Mapped[ScanJob] = relationship(back_populates="domains")

    __table_args__ = (Index("uq_scan_job_domains_ordinal", "scan_job_id", "ordinal", unique=True),)


class Watchlist(TimestampMixin, Base):
    __tablename__ = "watchlists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    watch_type: Mapped[str] = mapped_column(Text, nullable=False)
    root: Mapped[str | None] = mapped_column(Text)
    range_start: Mapped[int | None] = mapped_column(BigInteger)
    range_end: Mapped[int | None] = mapped_column(BigInteger)
    range_width: Mapped[int | None] = mapped_column(Integer)
    scan_cursor: Mapped[int | None] = mapped_column(BigInteger)
    single_domain: Mapped[str | None] = mapped_column(Text)
    frequency: Mapped[str] = mapped_column(Text, default="weekly", nullable=False)
    notification_mode: Mapped[str] = mapped_column(Text, default="newly_registered", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index(
            "uq_watchlists_range",
            "chat_id",
            "root",
            "range_start",
            "range_end",
            "frequency",
            unique=True,
            postgresql_where=is_active.is_(True),
        ),
        Index(
            "uq_watchlists_single",
            "chat_id",
            "single_domain",
            "frequency",
            unique=True,
            postgresql_where=is_active.is_(True),
        ),
    )


class DomainStatusChange(Base):
    __tablename__ = "domain_status_changes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id"), nullable=False)
    scan_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scan_jobs.id"))
    old_status: Mapped[str | None] = mapped_column(Text)
    new_status: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmation_count: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TelegramOutbox(Base):
    __tablename__ = "telegram_outbox"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_by: Mapped[str | None] = mapped_column(Text)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from domainbot.db.models import (
    Domain,
    DomainCheck,
    DomainStatusChange,
    ScanJob,
    ScanJobDomain,
    TelegramOutbox,
)
from domainbot.domain.status import DomainStatus
from domainbot.jobs.planner import ScanJobPlan
from domainbot.jobs.result_service import build_domain_update, job_bucket_for_outcome
from domainbot.jobs.types import ScanJobDomainOutcome, ScanJobStatus
from domainbot.rdap.result import RdapResult


@dataclass(frozen=True)
class PendingJobDomain:
    scan_job_domain: ScanJobDomain
    domain: Domain


@dataclass(frozen=True)
class ActiveJobSummary:
    root: str | None
    range_start: int | None
    range_end: int | None
    single_domain: str | None
    completed_count: int
    total_count: int


class ScanJobRepository:
    async def create_scan_job(
        self,
        session: AsyncSession,
        plan: ScanJobPlan,
        chat_id: int,
        requested_by: int,
        now: datetime | None = None,
    ) -> ScanJob:
        created_at = now or datetime.now(UTC)
        job = ScanJob(
            chat_id=chat_id,
            requested_by=requested_by,
            job_type=plan.job_type.value,
            root=plan.root,
            range_start=plan.range_start,
            range_end=plan.range_end,
            range_width=plan.range_width,
            single_domain=plan.single_domain,
            total_count=plan.total_count,
            status=ScanJobStatus.QUEUED.value,
            created_at=created_at,
        )
        session.add(job)
        await session.flush()

        for ordinal, domain_name in enumerate(plan.domains, start=1):
            domain = await self._get_or_create_domain(session, domain_name, created_at)
            session.add(
                ScanJobDomain(
                    scan_job_id=job.id,
                    domain_id=domain.id,
                    ordinal=ordinal,
                    outcome=ScanJobDomainOutcome.PENDING.value,
                )
            )
        return job

    async def claim_next_job(
        self,
        session: AsyncSession,
        worker_id: str,
        lease_seconds: int = 300,
        now: datetime | None = None,
    ) -> ScanJob | None:
        claimed_at = now or datetime.now(UTC)
        stale_running = (
            (ScanJob.status == ScanJobStatus.RUNNING.value)
            & (ScanJob.lease_expires_at.is_not(None))
            & (ScanJob.lease_expires_at < claimed_at)
        )
        statement: Select[tuple[ScanJob]] = (
            select(ScanJob)
            .where((ScanJob.status == ScanJobStatus.QUEUED.value) | stale_running)
            .order_by(ScanJob.priority.asc(), ScanJob.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = await session.scalar(statement)
        if job is None:
            return None

        job.status = ScanJobStatus.RUNNING.value
        job.started_at = job.started_at or claimed_at
        job.locked_by = worker_id
        job.locked_at = claimed_at
        job.lease_expires_at = claimed_at + timedelta(seconds=lease_seconds)
        return job

    async def pending_domains(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
    ) -> list[PendingJobDomain]:
        statement = (
            select(ScanJobDomain, Domain)
            .join(Domain, Domain.id == ScanJobDomain.domain_id)
            .where(
                ScanJobDomain.scan_job_id == job_id,
                ScanJobDomain.outcome == ScanJobDomainOutcome.PENDING.value,
            )
            .order_by(ScanJobDomain.ordinal.asc())
        )
        rows = (await session.execute(statement)).all()
        return [PendingJobDomain(scan_job_domain=row[0], domain=row[1]) for row in rows]

    async def record_result(
        self,
        session: AsyncSession,
        job: ScanJob,
        pending: PendingJobDomain,
        result: RdapResult,
        checked_at: datetime | None = None,
    ) -> None:
        now = checked_at or datetime.now(UTC)
        domain = pending.domain
        current = _status_or_none(domain.current_verified_status)
        update = build_domain_update(
            current_verified_status=current,
            consecutive_failure_count=domain.consecutive_failure_count,
            result=result,
            checked_at=now,
        )

        domain.current_verified_status = _status_value(update.current_verified_status)
        domain.previous_verified_status = _status_value(update.previous_verified_status)
        if update.status_changed_at is not None:
            domain.status_changed_at = update.status_changed_at
        domain.last_checked_at = update.last_checked_at
        if update.last_successful_check_at is not None:
            domain.last_successful_check_at = update.last_successful_check_at
        domain.last_check_outcome = update.last_check_outcome.value
        domain.consecutive_failure_count = update.consecutive_failure_count

        if result.parsed is not None:
            domain.registration_date = result.parsed.registration_date
            domain.expiration_date = result.parsed.expiration_date
            domain.last_changed_date = result.parsed.last_changed_date
            domain.registrar_name = result.parsed.registrar_name
            domain.registrar_iana_id = result.parsed.registrar_iana_id
            domain.rdap_statuses = {"values": list(result.parsed.statuses)}
            domain.nameservers = {"values": list(result.parsed.nameservers)}

        session.add(
            DomainCheck(
                domain_id=domain.id,
                scan_job_id=job.id,
                source="rdap_verisign",
                http_status=result.http_status,
                outcome=result.outcome.value,
                attempt_count=result.attempt_count,
                response_time_ms=result.response_time_ms,
                error_type=result.error_type,
                error_message=result.error_message,
                checked_at=now,
            )
        )

        if update.transition.changed:
            session.add(
                DomainStatusChange(
                    domain_id=domain.id,
                    scan_job_id=job.id,
                    old_status=_status_value(update.transition.previous_verified_status),
                    new_status=result.outcome.value,
                    detected_at=now,
                    confirmed_at=now,
                )
            )

        pending.scan_job_domain.outcome = result.outcome.value
        pending.scan_job_domain.verified_status = _status_value(update.current_verified_status)
        pending.scan_job_domain.checked_at = now

        job.completed_count += 1
        bucket = job_bucket_for_outcome(result.outcome)
        if bucket == "registered":
            job.registered_count += 1
        elif bucket == "not_found":
            job.not_found_count += 1
        else:
            job.unknown_count += 1

    def renew_lease(
        self,
        job: ScanJob,
        worker_id: str,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> None:
        renewed_at = now or datetime.now(UTC)
        job.locked_by = worker_id
        job.locked_at = renewed_at
        job.lease_expires_at = renewed_at + timedelta(seconds=lease_seconds)

    async def finish_if_complete(
        self,
        session: AsyncSession,
        job: ScanJob,
        now: datetime | None = None,
    ) -> bool:
        pending_count = await session.scalar(
            select(func.count())
            .select_from(ScanJobDomain)
            .where(
                ScanJobDomain.scan_job_id == job.id,
                ScanJobDomain.outcome == ScanJobDomainOutcome.PENDING.value,
            )
        )
        if int(pending_count or 0) > 0:
            return False

        if job.status == ScanJobStatus.COMPLETED.value:
            return True

        finished_at = now or datetime.now(UTC)
        job.status = ScanJobStatus.COMPLETED.value
        job.finished_at = finished_at
        job.locked_by = None
        job.locked_at = None
        job.lease_expires_at = None
        outbox = await _completion_outbox(session, job, finished_at)
        if outbox is not None:
            session.add(outbox)
        return True

    async def fail_job(
        self,
        session: AsyncSession,
        job: ScanJob,
        message: str,
        now: datetime | None = None,
    ) -> None:
        job.status = ScanJobStatus.FAILED.value
        job.finished_at = now or datetime.now(UTC)
        job.error_message = message
        job.locked_by = None
        job.locked_at = None
        job.lease_expires_at = None

    async def active_job_summary(
        self,
        session: AsyncSession,
        chat_id: int,
    ) -> ActiveJobSummary | None:
        statement = (
            select(ScanJob)
            .where(
                ScanJob.chat_id == chat_id,
                ScanJob.status.in_([ScanJobStatus.QUEUED.value, ScanJobStatus.RUNNING.value]),
            )
            .order_by(ScanJob.created_at.asc())
            .limit(1)
        )
        job = await session.scalar(statement)
        if job is None:
            return None
        return ActiveJobSummary(
            root=job.root,
            range_start=job.range_start,
            range_end=job.range_end,
            single_domain=job.single_domain,
            completed_count=job.completed_count,
            total_count=job.total_count,
        )

    async def _get_or_create_domain(
        self,
        session: AsyncSession,
        domain_name: str,
        now: datetime,
    ) -> Domain:
        await session.execute(
            insert(Domain)
            .values(domain=domain_name, created_at=now, updated_at=now)
            .on_conflict_do_nothing(index_elements=[Domain.domain])
        )
        existing = await session.scalar(select(Domain).where(Domain.domain == domain_name))
        if existing is None:
            raise RuntimeError("Domain upsert did not return a row.")
        return existing


def _status_or_none(value: str | None) -> DomainStatus | None:
    if value is None:
        return None
    try:
        return DomainStatus(value)
    except ValueError:
        return None


def _status_value(status: DomainStatus | None) -> str | None:
    return status.value if status is not None else None


async def _completion_outbox(
    session: AsyncSession,
    job: ScanJob,
    now: datetime,
) -> TelegramOutbox | None:
    if job.job_type == "watch":
        return await _watch_completed_outbox(session, job, now)
    if job.job_type == "pool_refresh":
        return await _pool_refresh_completed_outbox(session, job, now)
    return _scan_completed_outbox(job, now)


def _scan_completed_outbox(job: ScanJob, now: datetime) -> TelegramOutbox:
    return TelegramOutbox(
        chat_id=job.chat_id,
        message_type="scan_completed",
        payload={
            "job_id": str(job.id),
            "job_type": job.job_type,
            "root": job.root,
            "range_start": job.range_start,
            "range_end": job.range_end,
            "single_domain": job.single_domain,
            "total_count": job.total_count,
            "registered_count": job.registered_count,
            "not_found_count": job.not_found_count,
            "unknown_count": job.unknown_count,
            "finished_at": now.isoformat(),
        },
        idempotency_key=f"scan_completed:{job.id}",
        status="pending",
        next_attempt_at=now,
        created_at=now,
    )


async def _watch_completed_outbox(
    session: AsyncSession,
    job: ScanJob,
    now: datetime,
) -> TelegramOutbox | None:
    statement = (
        select(Domain.domain)
        .join(DomainStatusChange, DomainStatusChange.domain_id == Domain.id)
        .where(
            DomainStatusChange.scan_job_id == job.id,
            DomainStatusChange.old_status == DomainStatus.NOT_FOUND_IN_REGISTRY.value,
            DomainStatusChange.new_status == DomainStatus.REGISTERED.value,
        )
        .order_by(Domain.domain.asc())
    )
    domains = tuple((await session.scalars(statement)).all())
    if not domains:
        return None
    return TelegramOutbox(
        chat_id=job.chat_id,
        message_type="watch_newly_registered",
        payload={
            "job_id": str(job.id),
            "domains": list(domains),
            "total_count": len(domains),
            "finished_at": now.isoformat(),
        },
        idempotency_key=f"watch_newly_registered:{job.id}",
        status="pending",
        next_attempt_at=now,
        created_at=now,
    )


async def _pool_refresh_completed_outbox(
    session: AsyncSession,
    job: ScanJob,
    now: datetime,
) -> TelegramOutbox | None:
    unfinished_count = await session.scalar(
        select(func.count())
        .select_from(ScanJob)
        .where(
            ScanJob.chat_id == job.chat_id,
            ScanJob.job_type == "pool_refresh",
            ScanJob.created_at == job.created_at,
            ScanJob.status != ScanJobStatus.COMPLETED.value,
        )
    )
    if int(unfinished_count or 0) > 0:
        return None
    return TelegramOutbox(
        chat_id=job.chat_id,
        message_type="pool_domain_refresh_completed",
        payload={
            "created_at": job.created_at.isoformat(),
            "finished_at": now.isoformat(),
        },
        idempotency_key=f"pool_domain_refresh_completed:{job.chat_id}:{job.created_at.isoformat()}",
        status="pending",
        next_attempt_at=now,
        created_at=now,
    )

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domainbot.btk.types import BtkResult, BtkStatus
from domainbot.db.models import Domain, ScanJob, TelegramOutbox
from domainbot.domain.status import DomainStatus
from domainbot.jobs.types import ScanJobStatus


class BtkRepository:
    async def pending_domains(
        self,
        session: AsyncSession,
        limit: int,
        retry_after: timedelta,
    ) -> tuple[Domain, ...]:
        retry_cutoff = datetime.now(UTC) - retry_after
        statement: Select[tuple[Domain]] = (
            select(Domain)
            .where(
                Domain.last_checked_at.is_not(None),
                Domain.current_verified_status == DomainStatus.REGISTERED.value,
                or_(
                    Domain.btk_status.is_(None),
                    and_(
                        Domain.btk_status.in_(
                            [
                                BtkStatus.SUSPECT.value,
                                BtkStatus.INCONCLUSIVE.value,
                                BtkStatus.DEAD.value,
                                BtkStatus.ERROR.value,
                            ]
                        ),
                        or_(
                            Domain.btk_checked_at.is_(None),
                            Domain.btk_checked_at <= retry_cutoff,
                        ),
                    ),
                ),
            )
            .order_by(Domain.btk_checked_at.asc().nullsfirst(), Domain.domain.asc())
            .limit(limit)
        )
        return tuple((await session.scalars(statement)).all())

    async def record_results(
        self,
        session: AsyncSession,
        results: tuple[BtkResult, ...],
    ) -> None:
        if not results:
            return
        by_domain = {result.domain: result for result in results}
        statement = select(Domain).where(Domain.domain.in_(by_domain.keys()))
        domains = (await session.scalars(statement)).all()
        checked_at = datetime.now(UTC)
        for domain in domains:
            result = by_domain[domain.domain]
            domain.btk_status = result.status.value
            domain.btk_checked_at = checked_at
            domain.btk_note = result.note
            domain.btk_error = _error_text(result)

    async def complete_refresh_notifications_if_ready(
        self,
        session: AsyncSession,
    ) -> int:
        pending_count = await session.scalar(
            select(func.count())
            .select_from(Domain)
            .where(
                Domain.last_checked_at.is_not(None),
                Domain.current_verified_status == DomainStatus.REGISTERED.value,
                Domain.btk_status.is_(None),
            )
        )
        if int(pending_count or 0) > 0:
            return 0

        trackers = tuple(
            (
                await session.scalars(
                    select(ScanJob)
                    .where(
                        ScanJob.job_type == "btk_refresh",
                        ScanJob.status == ScanJobStatus.RUNNING.value,
                    )
                    .order_by(ScanJob.created_at.asc())
                )
            ).all()
        )
        if not trackers:
            return 0

        completed_at = datetime.now(UTC)
        for tracker in trackers:
            tracker.status = ScanJobStatus.COMPLETED.value
            tracker.finished_at = completed_at
            tracker.locked_by = None
            tracker.locked_at = None
            tracker.lease_expires_at = None
            session.add(
                TelegramOutbox(
                    chat_id=tracker.chat_id,
                    message_type="pool_btk_refresh_completed",
                    payload={
                        "job_id": str(tracker.id),
                        "finished_at": completed_at.isoformat(),
                    },
                    idempotency_key=f"pool_btk_refresh_completed:{tracker.id}",
                    status="pending",
                    next_attempt_at=completed_at,
                    created_at=completed_at,
                )
            )
        return len(trackers)


def _error_text(result: BtkResult) -> str | None:
    if result.status == BtkStatus.ERROR:
        return result.error or result.note or "BTK kontrolü hata aldı."
    return None

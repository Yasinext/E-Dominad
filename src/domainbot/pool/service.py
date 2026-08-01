from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from domainbot.db.models import Domain, ScanJob
from domainbot.jobs.planner import ScanJobPlan
from domainbot.jobs.repository import ScanJobRepository
from domainbot.jobs.types import ScanJobStatus, ScanJobType


@dataclass(frozen=True)
class PoolRefreshResult:
    domain_count: int
    job_count: int
    already_running: bool = False


class PoolRefreshService:
    def __init__(self, repository: ScanJobRepository | None = None) -> None:
        self.repository = repository or ScanJobRepository()

    async def enqueue_domain_refresh(
        self,
        session: AsyncSession,
        chat_id: int,
        requested_by: int,
        batch_size: int,
        now: datetime | None = None,
    ) -> PoolRefreshResult:
        active_count = await self._active_domain_refresh_count(session, chat_id)
        if active_count:
            return PoolRefreshResult(domain_count=0, job_count=active_count, already_running=True)

        domains = tuple(
            await session.scalars(
                select(Domain.domain)
                .where(Domain.last_checked_at.is_not(None))
                .order_by(Domain.domain.asc())
            )
        )
        if not domains:
            return PoolRefreshResult(domain_count=0, job_count=0)

        created_at = now or datetime.now(UTC)
        job_count = 0
        for batch in _chunks(domains, max(batch_size, 1)):
            job = await self.repository.create_scan_job(
                session=session,
                plan=ScanJobPlan(job_type=ScanJobType.POOL_REFRESH, domains=batch),
                chat_id=chat_id,
                requested_by=requested_by,
                now=created_at,
            )
            job.priority = 200
            job_count += 1
        return PoolRefreshResult(domain_count=len(domains), job_count=job_count)

    async def enqueue_btk_refresh(self, session: AsyncSession) -> int:
        result = await session.execute(
            update(Domain)
            .where(Domain.last_checked_at.is_not(None))
            .values(
                btk_status=None,
                btk_checked_at=None,
                btk_note=None,
                btk_error=None,
                updated_at=datetime.now(UTC),
            )
        )
        cursor_result = cast(CursorResult[object], result)
        return int(cursor_result.rowcount or 0)

    async def _active_domain_refresh_count(self, session: AsyncSession, chat_id: int) -> int:
        count = await session.scalar(
            select(func.count())
            .select_from(ScanJob)
            .where(
                ScanJob.chat_id == chat_id,
                ScanJob.job_type == ScanJobType.POOL_REFRESH.value,
                ScanJob.status.in_([ScanJobStatus.QUEUED.value, ScanJobStatus.RUNNING.value]),
            )
        )
        return int(count or 0)


def _chunks(values: tuple[str, ...], size: int) -> tuple[tuple[str, ...], ...]:
    return tuple(values[index : index + size] for index in range(0, len(values), size))

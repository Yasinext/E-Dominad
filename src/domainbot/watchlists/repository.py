from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from domainbot.db.models import ScanJob, Watchlist
from domainbot.domain.range_generator import generate_range_domains
from domainbot.jobs.planner import ScanJobPlan
from domainbot.jobs.repository import ScanJobRepository
from domainbot.jobs.types import ScanJobStatus, ScanJobType


@dataclass(frozen=True)
class WatchPlan:
    watch_type: str
    total_count: int
    frequency: str
    root: str | None = None
    range_start: int | None = None
    range_end: int | None = None
    range_width: int | None = None
    single_domain: str | None = None


class WatchlistRepository:
    async def create_watchlist(
        self,
        session: AsyncSession,
        plan: WatchPlan,
        chat_id: int,
        created_by: int,
        now: datetime | None = None,
    ) -> Watchlist:
        created_at = now or datetime.now(UTC)
        existing = await self._find_active(session, chat_id, plan)
        if existing is not None:
            return existing
        watchlist = Watchlist(
            chat_id=chat_id,
            created_by=created_by,
            watch_type=plan.watch_type,
            root=plan.root,
            range_start=plan.range_start,
            range_end=plan.range_end,
            range_width=plan.range_width,
            scan_cursor=plan.range_start,
            single_domain=plan.single_domain,
            frequency=plan.frequency,
            is_active=True,
            next_run_at=created_at,
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(watchlist)
        await session.flush()
        return watchlist

    async def deactivate_watchlist(
        self,
        session: AsyncSession,
        plan: WatchPlan,
        chat_id: int,
        now: datetime | None = None,
    ) -> bool:
        watchlist = await self._find_active(session, chat_id, plan)
        if watchlist is None:
            return False
        watchlist.is_active = False
        watchlist.updated_at = now or datetime.now(UTC)
        return True

    async def active_watchlists(self, session: AsyncSession, chat_id: int) -> list[Watchlist]:
        statement = (
            select(Watchlist)
            .where(Watchlist.chat_id == chat_id, Watchlist.is_active.is_(True))
            .order_by(Watchlist.created_at.asc())
        )
        return list((await session.scalars(statement)).all())

    async def claim_due_watchlists(
        self,
        session: AsyncSession,
        limit: int,
        now: datetime | None = None,
    ) -> list[Watchlist]:
        claimed_at = now or datetime.now(UTC)
        statement: Select[tuple[Watchlist]] = (
            select(Watchlist)
            .where(Watchlist.is_active.is_(True), Watchlist.next_run_at <= claimed_at)
            .order_by(Watchlist.next_run_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await session.scalars(statement)).all())

    async def create_due_scan_job(
        self,
        session: AsyncSession,
        watchlist: Watchlist,
        batch_size: int,
        now: datetime | None = None,
    ) -> ScanJob | None:
        run_at = now or datetime.now(UTC)
        plan = _batch_plan(watchlist, batch_size)
        existing_job = await self._active_scan_job(session, watchlist.chat_id, plan)
        if existing_job is not None:
            watchlist.next_run_at = run_at + timedelta(minutes=5)
            watchlist.updated_at = run_at
            return None

        job = await ScanJobRepository().create_scan_job(
            session=session,
            plan=plan,
            chat_id=watchlist.chat_id,
            requested_by=watchlist.created_by,
            now=run_at,
        )
        job.job_type = "watch"
        cursor = _next_cursor(watchlist, batch_size)
        watchlist.scan_cursor = cursor
        watchlist.last_run_at = run_at
        watchlist.next_run_at = _next_run_at(run_at, watchlist.frequency)
        watchlist.updated_at = run_at
        return job

    async def _find_active(
        self,
        session: AsyncSession,
        chat_id: int,
        plan: WatchPlan,
    ) -> Watchlist | None:
        statement = select(Watchlist).where(
            Watchlist.chat_id == chat_id,
            Watchlist.is_active.is_(True),
            Watchlist.watch_type == plan.watch_type,
            Watchlist.frequency == plan.frequency,
        )
        if plan.single_domain:
            statement = statement.where(Watchlist.single_domain == plan.single_domain)
        else:
            statement = statement.where(
                Watchlist.root == plan.root,
                Watchlist.range_start == plan.range_start,
                Watchlist.range_end == plan.range_end,
            )
        return cast(Watchlist | None, await session.scalar(statement.limit(1)))

    async def _active_scan_job(
        self,
        session: AsyncSession,
        chat_id: int,
        plan: ScanJobPlan,
    ) -> ScanJob | None:
        statement = select(ScanJob).where(
            ScanJob.chat_id == chat_id,
            ScanJob.status.in_((ScanJobStatus.QUEUED.value, ScanJobStatus.RUNNING.value)),
        )
        if plan.single_domain:
            statement = statement.where(ScanJob.single_domain == plan.single_domain)
        else:
            statement = statement.where(
                ScanJob.root == plan.root,
                ScanJob.range_start == plan.range_start,
                ScanJob.range_end == plan.range_end,
            )
        return cast(ScanJob | None, await session.scalar(statement.limit(1)))


def _batch_plan(watchlist: Watchlist, batch_size: int) -> ScanJobPlan:
    if watchlist.single_domain:
        return ScanJobPlan(
            job_type=ScanJobType.SINGLE,
            domains=(watchlist.single_domain,),
            single_domain=watchlist.single_domain,
        )
    if watchlist.root is None or watchlist.range_start is None or watchlist.range_end is None:
        raise ValueError("Range watchlist is missing range fields.")
    width = watchlist.range_width or len(str(watchlist.range_start))
    cursor = watchlist.scan_cursor or watchlist.range_start
    batch_end = min(cursor + batch_size - 1, watchlist.range_end)
    return ScanJobPlan(
        job_type=ScanJobType.RANGE,
        domains=tuple(generate_range_domains(watchlist.root, cursor, batch_end, width)),
        root=watchlist.root,
        range_start=cursor,
        range_end=batch_end,
        range_width=width,
    )


def _next_cursor(watchlist: Watchlist, batch_size: int) -> int | None:
    if watchlist.single_domain:
        return None
    if watchlist.range_start is None or watchlist.range_end is None:
        return None
    cursor = watchlist.scan_cursor or watchlist.range_start
    next_cursor = cursor + batch_size
    if next_cursor > watchlist.range_end:
        return watchlist.range_start
    return next_cursor


def _next_run_at(run_at: datetime, frequency: str) -> datetime:
    if frequency == "haftalik":
        return run_at + timedelta(days=7)
    return run_at + timedelta(days=1)

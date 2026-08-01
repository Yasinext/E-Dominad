from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from domainbot.db.models import ScanJob
from domainbot.domain.parser import ParsedCommand
from domainbot.jobs.planner import build_scan_job_plan
from domainbot.jobs.repository import ActiveJobSummary, ScanJobRepository


class ScanJobService:
    def __init__(self, repository: ScanJobRepository | None = None) -> None:
        self.repository = repository or ScanJobRepository()

    async def create_from_command(
        self,
        session: AsyncSession,
        parsed: ParsedCommand,
        chat_id: int,
        requested_by: int,
        now: datetime | None = None,
    ) -> ScanJob:
        plan = build_scan_job_plan(parsed)
        return await self.repository.create_scan_job(
            session=session,
            plan=plan,
            chat_id=chat_id,
            requested_by=requested_by,
            now=now,
        )

    async def active_job_summary(
        self,
        session: AsyncSession,
        chat_id: int,
    ) -> ActiveJobSummary | None:
        return await self.repository.active_job_summary(session, chat_id)

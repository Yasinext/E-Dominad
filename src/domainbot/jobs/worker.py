from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from domainbot.db.models import ScanJob
from domainbot.jobs.repository import PendingJobDomain, ScanJobRepository
from domainbot.rdap.result import RdapResult


class RdapChecker(Protocol):
    async def check_domain(self, domain: str) -> RdapResult: ...


@dataclass(frozen=True)
class WorkerSettings:
    worker_id: str
    lease_seconds: int = 300
    idle_sleep_seconds: float = 5.0

    @classmethod
    def default(cls, lease_seconds: int = 300, idle_sleep_seconds: float = 5.0) -> WorkerSettings:
        return cls(
            worker_id=f"{socket.gethostname()}:domainbot-worker",
            lease_seconds=lease_seconds,
            idle_sleep_seconds=idle_sleep_seconds,
        )


class ScanJobWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        rdap_checker: RdapChecker,
        repository: ScanJobRepository | None = None,
        settings: WorkerSettings | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.rdap_checker = rdap_checker
        self.repository = repository or ScanJobRepository()
        self.settings = settings or WorkerSettings.default()

    async def run_once(self) -> bool:
        async with self.session_factory() as session:
            async with session.begin():
                job = await self.repository.claim_next_job(
                    session,
                    worker_id=self.settings.worker_id,
                    lease_seconds=self.settings.lease_seconds,
                )
                if job is None:
                    return False
                job_id = job.id

        await self.process_job(job_id)
        return True

    async def run_forever(self) -> None:
        while True:
            did_work = await self.run_once()
            if not did_work:
                await asyncio.sleep(self.settings.idle_sleep_seconds)

    async def process_job(self, job_id: object) -> None:
        while True:
            async with self.session_factory() as session:
                async with session.begin():
                    job = await session.get(ScanJob, job_id)
                    if job is None:
                        return
                    pending = await self.repository.pending_domains(session, job.id)
                    if not pending:
                        await self.repository.finish_if_complete(session, job)
                        return
                    next_domain = pending[0]

            result = await self.rdap_checker.check_domain(next_domain.domain.domain)

            async with self.session_factory() as session:
                async with session.begin():
                    job = await session.get(ScanJob, job_id)
                    if job is None:
                        return
                    refreshed_pending = await self._refresh_pending(session, next_domain)
                    if refreshed_pending is None:
                        continue
                    await self.repository.record_result(session, job, refreshed_pending, result)
                    self.repository.renew_lease(
                        job,
                        worker_id=self.settings.worker_id,
                        lease_seconds=self.settings.lease_seconds,
                    )
                    await self.repository.finish_if_complete(session, job)

    async def _refresh_pending(
        self,
        session: AsyncSession,
        pending: PendingJobDomain,
    ) -> PendingJobDomain | None:
        refreshed = await self.repository.pending_domains(
            session,
            pending.scan_job_domain.scan_job_id,
        )
        for item in refreshed:
            if item.domain.id == pending.domain.id:
                return item
        return None

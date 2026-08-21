from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from domainbot.btk.repository import BtkRepository
from domainbot.btk.types import BtkResult


class BtkScanner(Protocol):
    async def scan(self, domains: tuple[str, ...]) -> tuple[BtkResult, ...]: ...


@dataclass(frozen=True)
class BtkWorkerSettings:
    worker_id: str
    batch_size: int = 25
    idle_sleep_seconds: float = 30.0
    batch_sleep_seconds: float = 5.0
    retry_interval_seconds: float = 21600.0

    @classmethod
    def default(
        cls,
        batch_size: int,
        idle_sleep_seconds: float,
        batch_sleep_seconds: float,
        retry_interval_seconds: float,
    ) -> BtkWorkerSettings:
        return cls(
            worker_id=f"{socket.gethostname()}:domainbot-btk-worker",
            batch_size=batch_size,
            idle_sleep_seconds=idle_sleep_seconds,
            batch_sleep_seconds=batch_sleep_seconds,
            retry_interval_seconds=retry_interval_seconds,
        )


class BtkWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        scanner: BtkScanner,
        repository: BtkRepository | None = None,
        settings: BtkWorkerSettings | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.scanner = scanner
        self.repository = repository or BtkRepository()
        self.settings = settings or BtkWorkerSettings.default(
            batch_size=25,
            idle_sleep_seconds=30.0,
            batch_sleep_seconds=5.0,
            retry_interval_seconds=21600.0,
        )

    async def run_once(self) -> bool:
        async with self.session_factory() as session:
            pending = await self.repository.pending_domains(
                session,
                self.settings.batch_size,
                timedelta(seconds=self.settings.retry_interval_seconds),
            )
            domains = tuple(domain.domain for domain in pending)
        if not domains:
            async with self.session_factory() as session:
                async with session.begin():
                    completed_count = await self.repository.complete_refresh_notifications_if_ready(
                        session
                    )
            if completed_count:
                return True
            return False

        results = await self.scanner.scan(domains)
        async with self.session_factory() as session:
            async with session.begin():
                await self.repository.record_results(session, results)
                await self.repository.complete_refresh_notifications_if_ready(session)
        await asyncio.sleep(self.settings.batch_sleep_seconds)
        return True

    async def run_forever(self) -> None:
        while True:
            did_work = await self.run_once()
            if not did_work:
                await asyncio.sleep(self.settings.idle_sleep_seconds)
